from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Import CORSMiddleware
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="3D Editor Asset Manager",
    version="1.0.0",
    description="FastAPI backend for managing 3D assets and previews stored in AWS S3 + MongoDB",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include Routers with Error Handling
try:
    from routes import assets
    app.include_router(assets.router)
    logger.info("Assets router included successfully.")
except Exception as e:
    logger.error(f"Failed to include assets router: {e}")

try:
    from routes import health
    app.include_router(health.router)
    logger.info("Health router included successfully.")
except Exception as e:
    logger.error(f"Failed to include health router: {e}")

@app.get("/")
def home():
    return {"message": "3D Editor FastAPI Backend 🚀"}

logger.info("Application startup complete. Ready to serve requests.")

# Run: uvicorn backend.main:app --reload
