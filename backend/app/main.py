from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.config.database import async_engine, Base 
from app.auth import router as auth_router
from app.routers import projects, exports, blob, ratecards, project_prompts
from app.utils import azure_blob

# ---------- App Init ----------
app = FastAPI(
    title="AI-Powered Project Scoping Bot Backend",
    description="AI-Powered Project Scoping Bot Backend",
    version="1.0.0",
)
# ---------- Startup ----------
@app.on_event("startup")
async def on_startup():
    # Create DB tables
    print("Creating database tables...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created.")
    # Ensure Blob container exists
    await azure_blob.init_container()
    print("Azure Blob container ready.")

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Static Files ----------
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ---------- Routers ----------
app.include_router(auth_router)
app.include_router(projects.router)
app.include_router(exports.router)
app.include_router(blob.router)
app.include_router(ratecards.router)
app.include_router(project_prompts.router)

# ---------- Health Check ----------
@app.get("/health")
async def health_check():
    """
    Health check endpoint for Kubernetes probes.
    """
    return {"status": "ok"}

