from service.domain_models import OrderRecord, SellerAssetRecord
from service.order_handoff import OrderHandoffService


def test_uploaded_seller_asset_moves_order_to_handoff_and_adds_buyer_update() -> None:
    service = OrderHandoffService()
    order = OrderRecord(
        order_id="ord_1001",
        status="awaiting_seller_media",
        buyer_updates=[],
    )
    asset = SellerAssetRecord(
        order_id="ord_1001",
        asset_id="asset_demo_video",
        filename="demo.mp4",
        object_key="orders/ord_1001/seller-assets/asset_demo_video/demo.mp4",
        content_type="video/mp4",
        status="uploaded",
        upload_id="upload_123",
    )

    updated_order, buyer_update = service.complete_seller_asset_upload(order, asset)

    assert updated_order.status == "ready_for_handoff"
    assert updated_order.buyer_updates == [
        "Seller uploaded demo.mp4. Order is moving to handoff."
    ]
    assert buyer_update.message == "Seller uploaded demo.mp4. Order is moving to handoff."
