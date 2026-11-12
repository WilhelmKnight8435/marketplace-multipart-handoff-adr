from typing import Literal
from pydantic import BaseModel, Field


OrderStatus = Literal["awaiting_seller_media", "ready_for_handoff"]
AssetStatus = Literal["pending_upload", "uploaded"]


class SellerAssetUploadRequest(BaseModel):
    order_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    parts: int = Field(ge=1, le=1000)


class UploadPartTicket(BaseModel):
    part_number: int
    url: str
    method: Literal["PUT"] = "PUT"


class SellerAssetUploadSession(BaseModel):
    order_id: str
    asset_id: str
    upload_id: str
    bucket: str
    object_key: str
    part_tickets: list[UploadPartTicket]


class CompletedUploadPart(BaseModel):
    part_number: int = Field(ge=1, le=1000)
    etag: str = Field(min_length=1)


class CompleteSellerAssetUploadRequest(BaseModel):
    order_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    upload_id: str = Field(min_length=1)
    parts: list[CompletedUploadPart] = Field(min_length=1)


class BuyerUpdate(BaseModel):
    order_id: str
    message: str


class OrderRecord(BaseModel):
    order_id: str
    status: OrderStatus
    buyer_updates: list[str]


class SellerAssetRecord(BaseModel):
    order_id: str
    asset_id: str
    filename: str
    object_key: str
    content_type: str
    status: AssetStatus
    upload_id: str
