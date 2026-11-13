# Valida credenciais, identificadores de sessão e referências para revogação.
from pydantic import BaseModel, EmailStr, Field


# Exige um e-mail válido e uma senha não vazia.
class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


# Exige um identificador de usuário não vazio.
class UserIdRequest(BaseModel):
    user_id: str = Field(min_length=1)


# Exige o identificador da sessão que autoriza a operação.
class SessionIdRequest(BaseModel):
    session_id: str = Field(min_length=1)


# Acrescenta a referência hexadecimal SHA-256 da sessão a encerrar.
class RevokeSessionRequest(SessionIdRequest):
    reference: str = Field(pattern=r"^[0-9a-f]{64}$")
