from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class BanCreate(BaseModel):
    reason: Optional[str] = None
    until: Optional[datetime] = None
