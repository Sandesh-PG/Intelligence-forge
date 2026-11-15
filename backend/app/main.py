from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import documents, upload

# Ensure storage directories exist at application startup
settings.ensure_storage_dirs()

app = FastAPI(
    title="Intelligence Forge API",
    description="Multimodal Research Knowledge Retrieval System",
    version="1.0.0",
)

# Allow the Next.js dev server to call the API during development.
# Restrict origins in production when the deployment target is known.
origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(documents.router)


@app.get("/")
async def root():
    return {
        "message": "Intelligence Forge API is running!",
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}
