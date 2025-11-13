from fastapi import FastAPI
from routes import assets, health
from fastapi.middleware.cors import CORSMiddleware # Import CORSMiddleware

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

# Include Routers
app.include_router(assets.router)
app.include_router(health.router)

@app.get("/")
def home():
    return {"message": "3D Editor FastAPI Backend 🚀"}

# Run: uvicorn backend.main:app --reload
