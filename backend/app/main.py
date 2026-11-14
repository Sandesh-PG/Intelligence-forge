from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.upload import router as upload_router

app = FastAPI(
    title="Intelligence Forge API",
    description="Multimodal Research Knowledge Retrieval System",
    version="1.0.0",
)

# Allow the Next.js dev server to call the API during development.
# Restrict origins in production when the deployment target is known.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)


@app.get("/")
async def root():
    return {
        "message": "Intelligence Forge API is running!",
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}
