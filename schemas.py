from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SMSCreate(BaseModel):
    to: str
    message: str

class SMSSchema(BaseModel):
    id: str
    to: str
    message: str
    status: str
    attempt_count: int
    created_at: datetime
    last_attempt_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    fail_reason: Optional[str] = None

    class Config:
        from_attributes = True
