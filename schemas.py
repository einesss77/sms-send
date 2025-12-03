from pydantic import BaseModel

class SMSCreate(BaseModel):
    to: str
    message: str
