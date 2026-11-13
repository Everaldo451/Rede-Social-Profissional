# Modelos de validação para criação, consulta, paginação e leitura de notificações.
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

# ID do MongoDB (ObjectId) em formato de string: 24 caracteres hexadecimais.
ObjectIdStr = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F]{24}$")]


# Define destinatário, tipo, título e referência opcional da nova notificação.
class CreateNotificationRequest(BaseModel):
    destinatario_id: ObjectIdStr
    tipo: str = Field(min_length=1)
    titulo: str = Field(min_length=1)
    referencia_tipo: str | None = None
    referencia_id: ObjectIdStr | None = None


# Permite alterar o estado de leitura da notificação.
class UpdateNotificationRequest(BaseModel):
    lida: bool


# Valida o identificador da notificação consultada ou alterada.
class NotificationIdRequest(BaseModel):
    notification_id: ObjectIdStr


# Valida o identificador do usuário destinatário.
class NotificationUserRequest(BaseModel):
    user_id: ObjectIdStr


# Impede posição negativa e limita cada consulta a cem notificações.
class NotificationPaginationRequest(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


# Permite selecionar as notificações pelo destinatário e pelo estado de leitura.
class NotificationFiltersRequest(BaseModel):
    destinatario_id: ObjectIdStr | None = None
    lida: bool | None = None
