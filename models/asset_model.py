# backend/models/asset_model.py
from pydantic import BaseModel, HttpUrl, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class AssetBase(BaseModel):
    """Shared attributes for assets (used for both DB and response)"""
    file_id: str = Field(..., description="Unique ID for the asset (UUID)")
    name: Optional[str] = Field(default="Untitled Asset", description="Name of the 3D asset")
    file_name: str = Field(..., description="Original filename of the uploaded model")
    model_url: HttpUrl = Field(..., description="Public or presigned URL of the .glb file")
    model_key: str = Field(..., description="S3 key path for the model file")
    thumbnail_url: Optional[HttpUrl] = Field(default=None, description="Optional preview image URL")
    thumbnail_key: Optional[str] = Field(default=None, description="S3 key path for the thumbnail image")
    uploaded_by: Optional[str] = Field(default="Unknown", description="Uploader name")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")
    tags: List[str] = Field(default_factory=list, description="Tags for search/filtering")

    model_config = ConfigDict(from_attributes=True)


class AssetCreate(BaseModel):
    """For creating a new asset (input validation)"""
    name: Optional[str] = Field(default="Untitled Asset")
    tags: Optional[List[str]] = Field(default_factory=list)


class AssetResponse(AssetBase):
    """Response model returned by the API"""
    message: Optional[str] = Field(default="Upload successful ✅")
