from sqlalchemy import Column, String, Boolean, DateTime, func
from database import Base
import uuid

class SMS(Base):
    __tablename__ = "sms"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    to = Column(String, nullable=False)
    message = Column(String, nullable=False)
    sent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
