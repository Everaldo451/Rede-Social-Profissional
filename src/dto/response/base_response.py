from typing import Any
from pydantic import BaseModel


class BaseResponse(BaseModel):
    data: dict[str, Any]
    status: int
