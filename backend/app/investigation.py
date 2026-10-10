from typing import Any

import httpx

from .collectors.github import collect_github_account
from .detectors import detect_github_findings


def investigate_github(
	target_url: str,
	*,
	transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
	result = collect_github_account(target_url, transport=transport)
	for repository_index, repository in enumerate(result["repositories"], start=1):
		repository["evidence_id"] = f"ev_{repository_index:03d}"
	result["findings"] = detect_github_findings(result["repositories"])
	return result
