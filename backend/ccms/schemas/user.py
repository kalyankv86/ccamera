from datetime import datetime

from pydantic import BaseModel, EmailStr

from ccms.models.enums import Role


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    password: str
    role: Role
    vendor_id: int | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    password: str | None = None
    role: Role | None = None
    vendor_id: int | None = None
    active: bool | None = None


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str | None
    role: Role
    vendor_id: int | None
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
