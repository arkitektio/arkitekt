
from typing import List, Optional
from pydantic import BaseModel


class ProvideParams(BaseModel):
    providers: Optional[List[str]]
    auto_unprovide: Optional[bool] = True
    auto_provide: Optional[bool] = True
