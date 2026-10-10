from typing import Any

import httpx

from .collectors.github import collect_github_account


def investigate_github(
	target_url: str,
	*,
	transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
	return collect_github_account(target_url, transport=transport)
