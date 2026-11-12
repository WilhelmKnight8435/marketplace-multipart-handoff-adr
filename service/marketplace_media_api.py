from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from service.domain_models import (
    CompleteSellerAssetUploadRequest,
    SellerAssetRecord,
    SellerAssetUploadRequest,
    SellerAssetUploadSession,
    UploadPartTicket,
)
from service.infrai_client import InfraiError, infrai
from service.marketplace_store import MarketplaceStore
from service.order_handoff import OrderHandoffService


BUCKET_NAME = "marketplace-media-demo"
store = MarketplaceStore()
handoff = OrderHandoffService()


def ensure_bucket() -> None:
    infrai.storage.bucket.create({"name": BUCKET_NAME})


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_bucket()
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/seller-assets/start-upload", response_model=SellerAssetUploadSession)
def start_upload(payload: SellerAssetUploadRequest) -> SellerAssetUploadSession:
    ensure_bucket()
    object_key = f"orders/{payload.order_id}/seller-assets/{payload.asset_id}/{payload.filename}"

    try:
        created = infrai.storage.multipart.create(
            BUCKET_NAME,
            {
                "key": object_key,
                "content_type": payload.content_type,
                "idempotency_key": f"{payload.order_id}:{payload.asset_id}:create",
            },
        )
        upload_data = created["data"]
        upload_id = upload_data["upload_id"]

        part_tickets: list[UploadPartTicket] = []
        for part_number in range(1, payload.parts + 1):
            presigned = infrai.storage.multipart.presign_part(
                upload_id,
                part_number,
                {
                    "upload_id": upload_id,
                    "part_number": part_number,
                    "idempotency_key": f"{payload.order_id}:{payload.asset_id}:part:{part_number}",
                },
            )
            part_tickets.append(
                UploadPartTicket(
                    part_number=part_number,
                    url=presigned["data"]["url"],
                )
            )

        store.save_asset(
            SellerAssetRecord(
                order_id=payload.order_id,
                asset_id=payload.asset_id,
                filename=payload.filename,
                object_key=object_key,
                content_type=payload.content_type,
                status="pending_upload",
                upload_id=upload_id,
            )
        )

        return SellerAssetUploadSession(
            order_id=payload.order_id,
            asset_id=payload.asset_id,
            upload_id=upload_id,
            bucket=BUCKET_NAME,
            object_key=object_key,
            part_tickets=part_tickets,
        )
    except InfraiError as exc:
        raise HTTPException(status_code=400, detail=exc.error) from exc


@app.post("/seller-assets/complete-upload")
def complete_upload(payload: CompleteSellerAssetUploadRequest) -> dict:
    asset = store.get_asset(payload.order_id, payload.asset_id)
    order = store.get_order(payload.order_id)

    try:
        infrai.storage.multipart.complete(
            payload.upload_id,
            {
                "parts": [part.model_dump() for part in payload.parts],
                "idempotency_key": f"{payload.order_id}:{payload.asset_id}:complete",
            },
        )
    except InfraiError as exc:
        raise HTTPException(status_code=400, detail=exc.error) from exc

    uploaded_asset = SellerAssetRecord(
        order_id=asset.order_id,
        asset_id=asset.asset_id,
        filename=asset.filename,
        object_key=asset.object_key,
        content_type=asset.content_type,
        status="uploaded",
        upload_id=asset.upload_id,
    )
    store.save_asset(uploaded_asset)

    updated_order, buyer_update = handoff.complete_seller_asset_upload(order, uploaded_asset)
    store.save_order(updated_order)

    return {
        "order_id": updated_order.order_id,
        "status": updated_order.status,
        "buyer_update": buyer_update.message,
        "asset": {
            "asset_id": uploaded_asset.asset_id,
            "filename": uploaded_asset.filename,
            "object_key": uploaded_asset.object_key,
            "status": uploaded_asset.status,
        },
    }
