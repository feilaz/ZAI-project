from fastapi import FastAPI

app = FastAPI(title="ZAI API")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
