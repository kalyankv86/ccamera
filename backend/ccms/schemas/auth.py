from pydantic import BaseModel, EmailStr

from ccms.models.enums import Role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: Role
    vendor_id: int | None = None

    model_config = {"from_attributes": True}
