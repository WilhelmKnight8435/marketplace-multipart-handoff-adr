from service.domain_models import OrderRecord, SellerAssetRecord


class MarketplaceStore:
    def __init__(self) -> None:
        self.orders: dict[str, OrderRecord] = {
            "ord_1001": OrderRecord(
                order_id="ord_1001",
                status="awaiting_seller_media",
                buyer_updates=[],
            )
        }
        self.assets: dict[tuple[str, str], SellerAssetRecord] = {}

    def get_order(self, order_id: str) -> OrderRecord:
        return self.orders[order_id]

    def save_order(self, order: OrderRecord) -> None:
        self.orders[order.order_id] = order

    def save_asset(self, asset: SellerAssetRecord) -> None:
        self.assets[(asset.order_id, asset.asset_id)] = asset

    def get_asset(self, order_id: str, asset_id: str) -> SellerAssetRecord:
        return self.assets[(order_id, asset_id)]
