import json
from typing import Any, Dict

from fastapi import HTTPException

MAX_JSON_BYTES = 16 * 1024


def validate_json_object(obj: Any, label: str) -> None:
    if not isinstance(obj, dict):
        raise HTTPException(status_code=422, detail=f"{label} must be JSON object")
    payload_bytes = len(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    if payload_bytes > MAX_JSON_BYTES:
        raise HTTPException(status_code=413, detail=f"{label} too large")
