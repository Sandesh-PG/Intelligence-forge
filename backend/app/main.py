
from fastapi import FastAPI

app = FastAPI(
    title="Intelligence Forge API",
    description="Multimodal Research Knowledge Retrieval System",
    version="1.0.0"
)


@app.get("/")
async def root():
    return {
        "message": "Intelligence Forge API is running!",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}
