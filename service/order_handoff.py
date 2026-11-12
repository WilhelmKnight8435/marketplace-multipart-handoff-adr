from service.domain_models import BuyerUpdate, OrderRecord, SellerAssetRecord


class OrderHandoffService:
    def complete_seller_asset_upload(
        self,
        order: OrderRecord,
        asset: SellerAssetRecord,
    ) -> tuple[OrderRecord, BuyerUpdate]:
        if order.status != "awaiting_seller_media":
            return order, BuyerUpdate(
                order_id=order.order_id,
                message=f"Seller uploaded {asset.filename}.",
            )

        message = f"Seller uploaded {asset.filename}. Order is moving to handoff."
        updated_order = OrderRecord(
            order_id=order.order_id,
            status="ready_for_handoff",
            buyer_updates=[*order.buyer_updates, message],
        )
        return updated_order, BuyerUpdate(order_id=order.order_id, message=message)
