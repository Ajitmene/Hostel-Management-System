from pydantic import BaseModel, ConfigDict, EmailStr, Field

from api.schemas.common import ORMModel


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)

    model_config = ConfigDict(json_schema_extra={"examples": [{"email": "admin@example.com", "password": "your-password"}]})


class UserOut(ORMModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: str
    permissions: list[str]
    employee_id: str | None = None


class SessionOut(BaseModel):
    user: UserOut
    csrf_token: str | None = None
    expires_in: int | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=10, max_length=256)
