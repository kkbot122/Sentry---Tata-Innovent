from fastapi import FastAPI

app = FastAPI(title="Bearing Fault Demo API")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
