import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_DEFAULT_MODEL = "openai/gpt-oss-20b"
GROQ_TIMEOUT = 30.0
MAX_ANALYSIS_RETRIES = 3


def _build_rule_based_analysis(
	github_data: dict[str, Any],
	website_data: dict[str, Any] | None,
	warning_message: str | None = None,
) -> dict[str, Any]:
	account_name = (github_data.get("account") or {}).get("name") or (github_data.get("account") or {}).get("login") or "Target company"
	findings = github_data.get("findings") or []
	backing_commits = github_data.get("backing_commits") or []
	repo_count = len(github_data.get("repositories") or [])

	website_title = (website_data or {}).get("title") or ""
	website_desc = (website_data or {}).get("description") or ""
	website_text = (website_data or {}).get("text") or ""

	stated_focus = website_desc or website_title or "Official website claims were unavailable or not provided."
	engineering_reality = (
		f"{account_name} has {repo_count} public repositories with {len(backing_commits)} active commits "
		f"and {len(findings)} detected engineering signals over the past 45 days."
	)

	say_do_gaps = []
	website_combined = f"{website_title} {website_desc} {website_text}".lower()

	for f in findings:
		title = f.get("title", "")
		desc = f.get("description", "")
		repo = f.get("committed_repo", "")
		# Check if the signal is mentioned on the website
		key_words = [w for w in title.lower().split() if len(w) > 4]
		mentioned = any(w in website_combined for w in key_words) if key_words and website_combined.strip() else False

		say_do_gaps.append(
			{
				"claim": f"Website narrative around {title}" if mentioned else f"Unannounced engineering in {repo}",
				"reality": desc,
				"verdict": "partly_supported" if mentioned else "unannounced_move",
			}
		)

	if not say_do_gaps:
		say_do_gaps.append(
			{
				"claim": "Official product footprint",
				"reality": "Public code matches standard maintenance activity without significant anomalies.",
				"verdict": "supported",
			}
		)

	warnings = []
	if warning_message:
		warnings.append({"scope": "analysis", "message": warning_message})

	return {
		"analysis_source": "rule_based",
		"stated_focus": stated_focus,
		"engineering_reality": engineering_reality,
		"say_do_gaps": say_do_gaps,
		"strategic_verdict": f"Observational synthesis: {len(findings)} signals detected across {repo_count} public repositories.",
		"warnings": warnings,
	}


def analyze_company(
	github_data: dict[str, Any],
	website_data: dict[str, Any] | None = None,
	*,
	transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
	"""
	Produces the final company analysis by passing website text + GitHub signals
	into a second Groq LLM call. Compares what the company claims to build vs. what it is shipping.
	Falls back gracefully to a deterministic rule-based analysis on failure.
	"""
	load_dotenv(PROJECT_ROOT / ".env")
	api_key = os.getenv("GROQ_API_KEY")
	if not api_key:
		return _build_rule_based_analysis(
			github_data, website_data, "GROQ_API_KEY is missing; rule-based analysis used."
		)

	model = os.getenv("GROQ_MODEL") or GROQ_DEFAULT_MODEL

	# Prepare bounded context
	company_name = (
		(website_data or {}).get("title")
		or (github_data.get("account") or {}).get("name")
		or (github_data.get("account") or {}).get("login")
		or "Company"
	)

	# Compact company website content
	compact_website = {
		"title": (website_data or {}).get("title"),
		"description": (website_data or {}).get("description"),
		"headings": (website_data or {}).get("headings", [])[:6],
		"sample_text": ((website_data or {}).get("text") or "")[:1200],
	}

	# Only the merged findings from GitHub signal detection
	merged_findings = [
		{
			"title": f.get("title"),
			"committed_repo": f.get("committed_repo"),
			"description": f.get("description"),
		}
		for f in (github_data.get("findings") or [])
		if isinstance(f, dict) and f.get("title")
	]

	input_payload = {
		"company_name": company_name,
		"website_content": compact_website,
		"merged_findings": merged_findings,
	}

	request_body = {
		"model": model,
		"temperature": 0.2,
		"response_format": {"type": "json_object"},
		"messages": [
			{
				"role": "system",
				"content": (
					"You are an expert technical intelligence and competitive analysis analyst. "
					"You are given a technology company's compact official website content (what it claims publicly) "
					"and its merged GitHub engineering findings (what its code and commits concretely show).\n\n"
					"Guidelines for objective, evidence-based intelligence:\n"
					"1. Strict Evidence Grounding: Base all observations strictly on the provided website content and observable GitHub findings.\n"
					"2. Do NOT Present Speculative Conclusions as Facts: Clearly distinguish verified public evidence from preliminary indicators. "
					"Never assert unconfirmed corporate strategy, internal management motives, or unverified roadmaps as established facts. "
					"Use measured, objective language (e.g. 'Public repositories demonstrate active development of...', 'Commit patterns indicate engineering focus on...', rather than asserting unconfirmed internal corporate strategy as a proven fact).\n"
					"3. Detect Say-Do Gaps and Unannounced Moves:\n"
					"- Stated Focus: Objective summary of the company's official positioning and product claims.\n"
					"- Engineering Reality: Objective summary of what public repositories and findings concretely show.\n"
					"- Say-Do Gaps: Compare claims and observable code. Use one of these exact verdicts:\n"
					"  ['supported', 'partly_supported', 'no_public_corroboration', 'contradictory_evidence', 'unannounced_move'].\n"
					"- Strategic Verdict: A balanced, evidence-backed synthesis of observable directions without speculative conjecture.\n\n"
					"Return ONLY valid JSON with this exact format:\n"
					"{\n"
					'  "stated_focus": "Clear summary of public website positioning",\n'
					'  "engineering_reality": "Clear summary of actual code and findings",\n'
					'  "say_do_gaps": [\n'
					"    {\n"
					'      "claim": "Specific website claim or observed unannounced initiative",\n'
					'      "reality": "What public code and findings concretely show",\n'
					'      "verdict": "supported" | "partly_supported" | "no_public_corroboration" | "contradictory_evidence" | "unannounced_move"\n'
					"    }\n"
					"  ],\n"
					'  "strategic_verdict": "Objective, evidence-backed strategic summary without speculation"\n'
					"}"
				),
			},
			{
				"role": "user",
				"content": json.dumps(input_payload, ensure_ascii=False),
			},
		],
	}

	for attempt in range(MAX_ANALYSIS_RETRIES):
		try:
			with httpx.Client(timeout=GROQ_TIMEOUT, transport=transport) as client:
				response = client.post(
					GROQ_API_URL,
					headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
					json=request_body,
				)
				if response.status_code == 429 and attempt < MAX_ANALYSIS_RETRIES - 1:
					retry_after = 2.0
					if "retry-after" in response.headers:
						try:
							retry_after = float(response.headers["retry-after"])
						except (ValueError, TypeError):
							pass
					time.sleep(min(max(retry_after, 1.5), 5.0))
					continue

				response.raise_for_status()
				content = response.json()["choices"][0]["message"]["content"]
				parsed = json.loads(content)

				stated_focus = parsed.get("stated_focus") or ""
				engineering_reality = parsed.get("engineering_reality") or ""
				say_do_gaps = parsed.get("say_do_gaps") or []
				strategic_verdict = parsed.get("strategic_verdict") or ""

				if not isinstance(say_do_gaps, list):
					say_do_gaps = []

				clean_gaps = []
				for g in say_do_gaps:
					if isinstance(g, dict) and g.get("claim"):
						clean_gaps.append(
							{
								"claim": str(g.get("claim", "")).strip(),
								"reality": str(g.get("reality", "")).strip(),
								"verdict": str(g.get("verdict", "partly_supported")).strip(),
							}
						)

				return {
					"analysis_source": "groq",
					"stated_focus": str(stated_focus).strip(),
					"engineering_reality": str(engineering_reality).strip(),
					"say_do_gaps": clean_gaps,
					"strategic_verdict": str(strategic_verdict).strip(),
					"warnings": [],
				}

		except httpx.HTTPStatusError as error:
			if error.response.status_code == 429 and attempt < MAX_ANALYSIS_RETRIES - 1:
				time.sleep(2.0)
				continue
			if error.response.status_code == 413:
				warning = "Groq token limit exceeded (HTTP 413); rule-based analysis used."
			else:
				warning = f"Groq returned HTTP {error.response.status_code}; rule-based analysis used."
			return _build_rule_based_analysis(github_data, website_data, warning)
		except httpx.HTTPError:
			return _build_rule_based_analysis(
				github_data, website_data, "Groq request failed due to network error; rule-based analysis used."
			)
		except (ValueError, KeyError, IndexError, TypeError):
			return _build_rule_based_analysis(
				github_data, website_data, "Groq analysis response was invalid; rule-based analysis used."
			)

	return _build_rule_based_analysis(
		github_data, website_data, "Groq rate limit exceeded (HTTP 429); rule-based analysis used."
	)
