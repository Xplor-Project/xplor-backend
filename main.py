from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import boto3
import os
from dotenv import load_dotenv
from uuid import uuid4
from datetime import datetime
from pymongo import MongoClient
import certifi
import os

# Load environment variables
load_dotenv()

# AWS configuration
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")

# MongoDB configuration
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

# Initialize AWS S3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

# Initialize MongoDB
# ✅ Use certifi to trust MongoDB’s SSL certificates
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client[MONGO_DB_NAME]
assets_collection = db["assets"]

# Initialize FastAPI app
app = FastAPI(title="3D Asset Manager", version="1.1")


@app.get("/")
def home():
    return {"message": "3D Editor Backend + MongoDB connected 🚀"}


# ✅ Upload GLB file and save metadata
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        # ✅ Check file type
        if not file.filename.endswith(".glb"):
            raise HTTPException(status_code=400, detail="Only .glb files are allowed")

        # ✅ Generate unique file key
        file_id = str(uuid4())
        file_key = f"assets/{file_id}_{file.filename}"

        # ✅ Upload to S3
        s3.upload_fileobj(
            file.file,
            S3_BUCKET,
            file_key,
            ExtraArgs={"ContentType": "model/gltf-binary"}
        )

        # ✅ Construct public URL
        file_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{file_key}"

        # ✅ Prepare metadata
        metadata = {
            "file_id": file_id,
            "file_name": file.filename,
            "s3_key": file_key,
            "file_url": file_url,
            "uploaded_at": datetime.utcnow(),
            "tags": [],
            "uploaded_by": "Ananya"
        }

        # ✅ Insert into MongoDB
        result = assets_collection.insert_one(metadata)

        # ✅ Convert ObjectId to string
        metadata["_id"] = str(result.inserted_id)

        # ✅ Convert datetime to ISO string (JSON-safe)
        metadata["uploaded_at"] = metadata["uploaded_at"].isoformat()

        # ✅ Return clean JSON response
        return JSONResponse(
            status_code=200,
            content={
                "message": "Upload successful ✅",
                "file_url": file_url,
                "metadata": metadata
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ✅ List all assets from MongoDB
@app.get("/assets/")
def list_assets():
    try:
        assets = list(assets_collection.find({}, {"_id": 0}))  # hide MongoDB internal _id
        return {"assets": assets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ Get a specific asset's details by ID
@app.get("/assets/{file_id}")
def get_asset(file_id: str):
    asset = assets_collection.find_one({"file_id": file_id}, {"_id": 0})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


# ✅ Delete an asset (S3 + Mongo)
@app.delete("/assets/{file_id}")
def delete_asset(file_id: str):
    asset = assets_collection.find_one({"file_id": file_id})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    try:
        # Delete from S3
        s3.delete_object(Bucket=S3_BUCKET, Key=asset["s3_key"])
        # Delete from MongoDB
        assets_collection.delete_one({"file_id": file_id})
        return {"message": "Asset deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
