from typing import Any
from pydantic import BaseModel


class BaseResponse(BaseModel):
    status: bool
    data: Any = None
    message: str | None = None
