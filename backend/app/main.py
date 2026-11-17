import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import chat, documents, graph, upload
from app.services.neo4j_client import neo4j_driver


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure storage dirs & verify/initialize Neo4j driver if configured
    settings.ensure_storage_dirs()
    if settings.neo4j_uri and not os.environ.get("PYTEST_CURRENT_TEST"):
        try:
            neo4j_driver.initialize()
        except Exception as e:
            print(f"Warning: Failed to initialize Neo4j driver on startup: {e}")
    yield
    # Shutdown: Close Neo4j driver
    neo4j_driver.close()


app = FastAPI(
    title="Intelligence Forge API",
    description="Multimodal Research Knowledge Retrieval System",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the Next.js dev server to call the API during development.
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
app.include_router(graph.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    return {
        "message": "Intelligence Forge API is running!",
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}