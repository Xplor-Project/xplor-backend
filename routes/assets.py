from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from datetime import datetime
from models.asset_model import AssetResponse
from core.database import assets_collection
from utils.s3_utils import upload_to_s3, delete_from_s3

router = APIRouter(prefix="/assets", tags=["Assets"])

# ✅ Upload Asset
@router.post("/upload/", response_model=AssetResponse)
async def upload_asset(
    file: UploadFile = File(...),
    thumbnail: UploadFile = File(None),
    name: str = Form("Untitled Asset")
):
    # ✅ upload logic same as before
    file_id, model_key, model_url = upload_to_s3(file, "assets/models", "model/gltf-binary")
    thumbnail_url, thumb_key = None, None
    if thumbnail:
        _, thumb_key, thumbnail_url = upload_to_s3(thumbnail, "assets/previews", "image/jpeg")

    metadata = {
        "file_id": file_id,
        "file_name": file.filename,
        "model_url": model_url,
        "model_key": model_key,
        "thumbnail_url": thumbnail_url,
        "thumbnail_key": thumb_key,
        "uploaded_at": datetime.utcnow(),
        "uploaded_by": "Ananya",
        "name": name,
        "tags": []
    }

    metadata["message"] = "Upload successful ✅"
    return metadata


# ✅ List All Assets
@router.get("/")
def list_assets():
    try:
        assets = list(assets_collection.find({}, {"_id": 0}))
        return {"total": len(assets), "assets": assets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ Get Asset by ID
@router.get("/{file_id}")
def get_asset(file_id: str):
    asset = assets_collection.find_one({"file_id": file_id}, {"_id": 0})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


# ✅ Delete Asset (from S3 + DB)
@router.delete("/{file_id}")
def delete_asset(file_id: str):
    asset = assets_collection.find_one({"file_id": file_id})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    try:
        # Delete model file
        delete_from_s3(asset["model_url"].split(".amazonaws.com/")[1])

        # Delete preview if exists
        if asset.get("thumbnail_url"):
            delete_from_s3(asset["thumbnail_url"].split(".amazonaws.com/")[1])

        assets_collection.delete_one({"file_id": file_id})
        return {"message": "Asset deleted successfully ✅"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
