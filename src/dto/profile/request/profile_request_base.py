from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from common.validation import clean_int

MongoId = Annotated[str, Field(pattern=r"^[a-fA-F0-9]{24}$")]


class ProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaginationRequest(ProfileRequest):
    offset: int = 0
    limit: int = 20
    filters: dict[str, Any] | None = None

    @field_validator("offset", mode="before")
    @classmethod
    def validate_offset(cls, value):
        return clean_int(value, "offset", minimum=0, maximum=2_147_483_647, required=True)

    @field_validator("limit", mode="before")
    @classmethod
    def validate_limit(cls, value):
        return clean_int(value, "limit", minimum=1, maximum=100, required=True)


class FiltersRequest(ProfileRequest):
    filters: dict[str, Any] | None = None
