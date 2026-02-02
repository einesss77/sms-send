from sqlalchemy import Column, String, Integer, DateTime, func
from database import Base
import uuid

class SMS(Base):
    __tablename__ = "sms"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    to = Column(String, nullable=False)
    message = Column(String, nullable=False)

    # Statuts: PENDING | SENT | FAILED
    status = Column(String, nullable=False, default="PENDING")

    attempt_count = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    fail_reason = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
