from pydantic import BaseModel, Field, field_validator
from dto.shared.email import normalize_email

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    headline: str = ""
    @field_validator("name")
    @classmethod
    def _name(cls,value):
        value=value.strip()
        if not 2<=len(value)<=80: raise ValueError("O nome deve ter entre 2 e 80 caracteres.")
        return value
    @field_validator("email")
    @classmethod
    def _email(cls,value): return normalize_email(value)
    @field_validator("password")
    @classmethod
    def _password(cls,value):
        if len(value)<8: raise ValueError("A senha deve ter pelo menos 8 caracteres.")
        if len(value.encode("utf-8"))>72: raise ValueError("A senha deve ter no máximo 72 bytes.")
        return value
    @field_validator("headline")
    @classmethod
    def _headline(cls,value):
        value=value.strip()
        if len(value)>100: raise ValueError("O cargo/headline deve ter no máximo 100 caracteres.")
        return value

class UpdateProfileRequest(BaseModel):
    name: str = Field(min_length=2,max_length=80)
    headline: str = Field(default="",max_length=100)
    bio: str = Field(default="",max_length=1000)
    location: str = Field(default="",max_length=100)
    @field_validator("name","headline","bio","location")
    @classmethod
    def clean(cls,value): return value.strip()
