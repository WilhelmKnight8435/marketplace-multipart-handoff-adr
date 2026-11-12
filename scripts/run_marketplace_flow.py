from pprint import pprint
from pathlib import Path
import sys

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from service.domain_models import CompleteSellerAssetUploadRequest, SellerAssetUploadRequest
from service.marketplace_media_api import complete_upload, start_upload


def main() -> None:
    started = start_upload(
        SellerAssetUploadRequest(
            order_id="ord_1001",
            asset_id="asset_demo_video",
            filename="demo.mp4",
            content_type="video/mp4",
            parts=3,
        )
    )
    print("Started multipart upload:")
    pprint(started.model_dump())

    parts = []
    for ticket in started.part_tickets:
        response = httpx.put(ticket.url, content=b"0" * (5 * 1024 * 1024), timeout=60.0)
        response.raise_for_status()
        parts.append({"part_number": ticket.part_number, "etag": response.headers["ETag"]})

    completed = complete_upload(
        CompleteSellerAssetUploadRequest(
            order_id="ord_1001",
            asset_id="asset_demo_video",
            upload_id=started.upload_id,
            parts=parts,
        )
    )
    print("\nCompleted order handoff:")
    pprint(completed)


if __name__ == "__main__":
    main()
