from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import config
from app.config.database import engine, Base
from app import models
from app.auth import router as auth_router
from app.routers import projects, exports, blob

# ---------- DB Init ----------
print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Database tables created.")

# ---------- App Init ----------
app = FastAPI(
    title=config.APP_NAME,
    description="AI-Powered Project Scoping Bot Backend",
    version="1.0.0",
)

# ---------- CORS ----------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Routers
app.include_router(auth_router)
app.include_router(projects.router)
app.include_router(exports.router)
app.include_router(blob.router)

# Health Check 
@app.get("/")
def root():
    return {
        "message": f"{config.APP_NAME} is running",
        "environment": config.APP_ENV,
    }
