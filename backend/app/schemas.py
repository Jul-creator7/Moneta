from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr


class Credentials(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(min_length=1, max_length=128)


class Registration(Credentials):
    username: str = Field(pattern=r"^[a-zA-Z0-9_]{3,32}$")
    password: SecretStr = Field(min_length=8, max_length=128)


class PublicUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
