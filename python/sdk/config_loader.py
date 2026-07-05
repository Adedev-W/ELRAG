from __future__ import annotations

import json
from pathlib import Path


def load_sdk_conf(conf_path: str | Path) -> dict[str, str]:
    path = Path(conf_path)
    config: dict[str, str] = {}
    if not path.exists():
        return config

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        config[key.strip()] = value.strip().strip('"').strip("'")
    return config


def load_auth_file(auth_path: str | Path) -> dict[str, str]:
    path = Path(auth_path)
    if not path.exists():
        raise FileNotFoundError(f"Auth file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Auth file must contain a JSON object")

    client_id = payload.get("client_id")
    if not isinstance(client_id, str) or not client_id.strip():
        raise ValueError("Auth file must contain non-empty 'client_id'")

    return {"client_id": client_id.strip()}

