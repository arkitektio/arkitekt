from pydantic import BaseModel, Field
from typing import List, Optional


class Manifest(BaseModel):
    version: str
    identifier: str
    scopes: List[str]
    logo: Optional[str]
    """ Scopes that this app should request from the user """

    class Config:
        extra = "forbid"


class User(BaseModel):
    id: str = Field(alias="sub")
    username: str = Field(alias="preferred_username")
    email: str = Field(alias="email")
    """ The user's preferred username """
