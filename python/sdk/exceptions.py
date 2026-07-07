from __future__ import annotations

from typing import Any

from httpx import Response


class SDKResponseError(RuntimeError):
    def __init__(self, response: Response) -> None:
        self.status_code = response.status_code
        self.body = self._safe_json(response)
        super().__init__(f"HTTP {response.status_code}")

    @staticmethod
    def _safe_json(response: Response) -> Any:
        try:
            return response.json()
        except Exception:
            return response.text
