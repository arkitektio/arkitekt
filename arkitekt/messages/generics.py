from typing import List, Optional
from pydantic import BaseModel

class Context(BaseModel):
    roles: List[str]
    scopes: List[str]
    user: Optional[str]
    app: Optional[str]

