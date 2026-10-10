from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .investigation import investigate_github

app = FastAPI(
	title="PHOENIX API",
	description="Infrastructure and investigation API for PHOENIX.",
)


@app.get("/health")
def health_check() -> dict[str, str]:
	return {"status": "ok"}


class InvestigationRequest(BaseModel):
	target_url: str


@app.post("/api/investigations")
def create_investigation(request: InvestigationRequest) -> dict:
	try:
		return investigate_github(request.target_url)
	except ValueError as error:
		raise HTTPException(status_code=422, detail=str(error)) from error
