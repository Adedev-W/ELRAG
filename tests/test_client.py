from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from client import (
    TokenStore,
    _base_url_from_redirect_uri,
    _token_payload,
    load_config,
)


class ClientConfigTest(unittest.TestCase):
    def test_base_url_is_derived_from_ngrok_redirect_uri(self) -> None:
        self.assertEqual(
            "https://example.ngrok-free.app",
            _base_url_from_redirect_uri(
                "https://example.ngrok-free.app/auth/callback"
            ),
        )

    def test_base_url_preserves_api_prefix(self) -> None:
        self.assertEqual(
            "https://example.ngrok-free.app/api",
            _base_url_from_redirect_uri(
                "https://example.ngrok-free.app/api/auth/callback"
            ),
        )

    def test_config_prefers_explicit_api_base_url(self) -> None:
        with patch.dict(
            os.environ,
            {
                "API_BASE_URL": "https://api.example.com/",
                "GOOGLE_REDIRECT_URI": "https://other.example.com/auth/callback",
            },
        ), patch("client.load_dotenv"):
            config = load_config()

        self.assertEqual("https://api.example.com", config.base_url)


class TokenStoreTest(unittest.TestCase):
    def test_save_and_load_uses_private_file_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".api_token.json"
            store = TokenStore(path)
            payload = {"access_token": "token", "token_type": "bearer"}

            store.save(payload)

            self.assertEqual(payload, store.load())
            self.assertEqual(stat.S_IRUSR | stat.S_IWUSR, stat.S_IMODE(path.stat().st_mode))
            self.assertEqual(payload, json.loads(path.read_text(encoding="utf-8")))

    def test_token_input_accepts_callback_json_or_bearer_value(self) -> None:
        self.assertEqual(
            {"access_token": "token", "token_type": "bearer"},
            _token_payload("Bearer token"),
        )
        self.assertEqual(
            {"access_token": "token", "user": {"email": "user@example.com"}},
            _token_payload('{"access_token":"token","user":{"email":"user@example.com"}}'),
        )


if __name__ == "__main__":
    unittest.main()
