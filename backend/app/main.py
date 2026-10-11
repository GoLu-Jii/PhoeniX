from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .detectors import detect_signals, parse_github_commits
from .investigation import compact_investigation_result, investigate_company, investigate_github

app = FastAPI(
	title="PHOENIX API",
	description="Infrastructure, investigation, and company intelligence API for PHOENIX.",
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

latest_investigation_store: dict[str, Any] = {}


@app.get("/health")
def health_check() -> dict[str, str]:
	return {"status": "ok"}


class InvestigationRequest(BaseModel):
	target_url: str | None = None
	github_url: str | None = None
	website_url: str | None = None
	include_raw: bool = False
	debug: bool = False

	model_config = {
		"json_schema_extra": {
			"example": {
				"github_url": "https://github.com/octocat",
				"website_url": "https://example.com",
				"include_raw": False,
			}
		}
	}


class SignalsRequest(BaseModel):
	target_url: str | None = None
	parsed_commits: list[dict[str, Any]] | None = None

	model_config = {
		"json_schema_extra": {
			"example": {}
		}
	}


def _process_signals(
	target_url: str | None = None,
	parsed_commits: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
	if parsed_commits is not None:
		commits_to_use = parsed_commits
		status = "success"
		account = None
		summary = None
		base_warnings: list[dict[str, str]] = []
	elif target_url:
		try:
			result = investigate_github(target_url)
		except ValueError as error:
			raise HTTPException(status_code=422, detail=str(error)) from error
		latest_investigation_store.clear()
		latest_investigation_store.update(result)
		commits_to_use = result.get("parsed_commits", [])
		status = result.get("status", "success")
		account = result.get("account")
		summary = result.get("summary")
		base_warnings = result.get("warnings", [])
	elif latest_investigation_store:
		commits_to_use = latest_investigation_store.get("parsed_commits", [])
		status = latest_investigation_store.get("status", "success")
		account = latest_investigation_store.get("account")
		summary = latest_investigation_store.get("summary")
		base_warnings = latest_investigation_store.get("warnings", [])
	else:
		raise HTTPException(
			status_code=400,
			detail="No previous investigation found. Please run /api/investigations first, or supply target_url.",
		)

	signals = detect_signals(commits_to_use)
	if signals.get("detection_source") == "groq":
		return {
			"findings": signals.get("findings", []),
			"backing_commits": signals.get("backing_commits", []),
		}

	return {
		"status": status,
		"detection_source": "rule_based",
		"findings": signals.get("findings", []),
		"backing_commits": signals.get("backing_commits", []),
		"parsed_commits": commits_to_use,
		"repositories": signals.get("repositories", []),
		"warnings": [*base_warnings, *signals.get("warnings", [])],
	}


@app.post("/api/investigations")
def create_investigation(
	request: InvestigationRequest,
	include_raw: bool | None = None,
	debug: bool | None = None,
) -> dict:
	github_target = request.github_url or request.target_url
	if not github_target:
		raise HTTPException(status_code=422, detail="github_url or target_url is required.")

	is_raw = bool(
		(include_raw is True)
		or (debug is True)
		or request.include_raw
		or request.debug
	)
	try:
		# Retrieve complete uncompacted data so internal store keeps full commit history
		try:
			full_result = investigate_company(github_target, website_url=request.website_url, include_raw=True)
		except TypeError:
			full_result = investigate_company(github_target, website_url=request.website_url)

		latest_investigation_store.clear()
		latest_investigation_store.update(full_result)

		if is_raw:
			return full_result

		return compact_investigation_result(full_result)
	except ValueError as error:
		raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/analyze")
def create_analysis(
	request: InvestigationRequest,
	include_raw: bool | None = None,
	debug: bool | None = None,
) -> dict:
	"""Alias for complete investigation and analysis."""
	return create_investigation(request, include_raw=include_raw, debug=debug)


@app.get("/api/signals")
def get_signals() -> dict:
	return _process_signals()


@app.post("/api/signals")
def create_signals(request: SignalsRequest | None = None) -> dict:
	target_url = request.target_url if request else None
	parsed_commits = request.parsed_commits if request else None
	return _process_signals(target_url=target_url, parsed_commits=parsed_commits)
