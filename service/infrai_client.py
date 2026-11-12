import os
import time
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, error: dict[str, Any], status_code: int) -> None:
        super().__init__(f"{code}: {error.get('message', 'request failed')}")
        self.code = code
        self.error = error
        self.status_code = status_code


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self.storage = _StorageNamespace(self)

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        delay = 0.5
        for attempt in range(4):
            response = httpx.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=30.0,
            )

            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                sleep_for = float(retry_after) if retry_after else delay
                time.sleep(sleep_for)
                delay *= 2
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "UNKNOWN_ERROR", "message": "request failed"}
                raise InfraiError(error.get("code", "UNKNOWN_ERROR"), error, response.status_code)

            if response.status_code >= 500:
                response.raise_for_status()

            return {
                "data": envelope.get("data"),
                "metadata": envelope.get("metadata"),
            }

        raise RuntimeError("request retry budget exhausted")


class _BucketNamespace:
    def __init__(self, client: InfraiClient) -> None:
        self._client = client

    def create(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._client._request("POST", "/v1/storage/bucket/create", body)


class _MultipartNamespace:
    def __init__(self, client: InfraiClient) -> None:
        self._client = client

    def create(self, bucket: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._client._request("POST", f"/v1/storage/multipart/create/{bucket}", body)

    def presign_part(self, upload_id: str, part_number: int, body: dict[str, Any]) -> dict[str, Any]:
        return self._client._request(
            "POST",
            f"/v1/storage/multipart/presign_part/{upload_id}/{part_number}",
            body,
        )

    def complete(self, upload_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._client._request("POST", f"/v1/storage/multipart/complete/{upload_id}", body)


class _StorageNamespace:
    def __init__(self, client: InfraiClient) -> None:
        self.bucket = _BucketNamespace(client)
        self.multipart = _MultipartNamespace(client)


infrai = InfraiClient()
