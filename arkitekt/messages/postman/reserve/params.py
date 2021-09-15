


from typing import List, Optional

from pydantic.main import BaseModel


class ReserveParams(BaseModel):
    providers: Optional[List[str]]
    templates: Optional[List[str]]
    auto_unprovide: Optional[bool] = True
    auto_provide: Optional[bool] = True