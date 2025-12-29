from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from datetime import datetime
from models.asset_model import AssetResponse
from core.database import assets_collection
from utils.s3_utils import upload_to_s3, delete_from_s3
from core.database import check_db_connection
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["Assets"])


# Upload Asset
@router.post("/upload/", response_model=AssetResponse)
async def upload_asset(
    file: UploadFile = File(...),
    thumbnail: UploadFile = File(None),
    name: str = Form("Untitled Asset")
):
    check_db_connection()
    logger.info(f"Starting upload for file: {file.filename}")

    try:
        # Upload model file
        file_id, model_key, model_url = upload_to_s3(
            file, "assets/models", "model/gltf-binary"
        )

        # Upload thumbnail if present
        thumbnail_url, thumb_key = None, None
        if thumbnail:
            _, thumb_key, thumbnail_url = upload_to_s3(
                thumbnail, "assets/previews", "image/jpeg"
            )

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

        # Insert into DB
        assets_collection.insert_one(metadata)

        # Remove Mongo _id before response
        metadata.pop("_id", None)
        metadata["message"] = "Upload successful ✅"

        logger.info(f"Upload successful for file_id: {file_id}")
        return metadata

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# List All Assets
@router.get("/")
def list_assets():
    check_db_connection()
    try:
        assets = list(assets_collection.find({}, {"_id": 0}))
        logger.info(f"Retrieved {len(assets)} assets")
        return {"total": len(assets), "assets": assets}
    except Exception as e:
        logger.error(f"Failed to list assets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Get Asset by ID
@router.get("/{file_id}")
def get_asset(file_id: str):
    check_db_connection()
    try:
        asset = assets_collection.find_one({"file_id": file_id}, {"_id": 0})
        if not asset:
            logger.warning(f"Asset not found: {file_id}")
            raise HTTPException(status_code=404, detail="Asset not found")
        return asset
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving asset {file_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Delete Asset (from S3 + DB)
@router.delete("/{file_id}")
def delete_asset(file_id: str):
    check_db_connection()
    try:
        asset = assets_collection.find_one({"file_id": file_id})
        if not asset:
            logger.warning(f"Asset not found for deletion: {file_id}")
            raise HTTPException(status_code=404, detail="Asset not found")

        # Delete model file
        delete_from_s3(asset["model_key"])

        # Delete thumbnail if exists
        if asset.get("thumbnail_key"):
            delete_from_s3(asset["thumbnail_key"])

        assets_collection.delete_one({"file_id": file_id})
        logger.info(f"Asset deleted successfully: {file_id}")
        return {"message": "Asset deleted successfully ✅"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting asset {file_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
