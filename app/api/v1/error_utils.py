from typing import Any

from fastapi import HTTPException


def raise_api_error(
    status_code: int,
    code: str,
    message: str,
    meta: dict[str, Any] | None = None,
) -> None:
    detail: dict[str, Any] = {"code": code, "message": message}
    if meta:
        detail["meta"] = meta
    raise HTTPException(status_code=status_code, detail=detail)
