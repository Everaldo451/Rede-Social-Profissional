from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

# ID do MongoDB (ObjectId) em formato de string: 24 caracteres hexadecimais.
ObjectIdStr = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F]{24}$")]


class CreateNotificationRequest(BaseModel):
    destinatario_id: ObjectIdStr
    tipo: str = Field(min_length=1)
    titulo: str = Field(min_length=1)
    referencia_tipo: str | None = None
    referencia_id: ObjectIdStr | None = None


class UpdateNotificationRequest(BaseModel):
    lida: bool


class NotificationIdRequest(BaseModel):
    notification_id: ObjectIdStr


class NotificationUserRequest(BaseModel):
    user_id: ObjectIdStr


class NotificationPaginationRequest(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class NotificationFiltersRequest(BaseModel):
    destinatario_id: ObjectIdStr | None = None
    lida: bool | None = None
