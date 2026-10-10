from fastapi import FastAPI

app = FastAPI(
	title="PHOENIX API",
	description="Infrastructure and investigation API for PHOENIX.",
)


@app.get("/health")
def health_check() -> dict[str, str]:
	return {"status": "ok"}
