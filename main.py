import os
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import SessionLocal, engine
from models import SMS, Base
from schemas import SMSCreate

# =========================
# APP
# =========================
app = FastAPI()

# =========================
# CONFIG
# =========================
API_KEY = os.getenv("API_KEY")

# =========================
# DB INIT (controlled reset)
# - Set RESET_DB=1 on Render to drop+recreate tables one time
# - Then remove RESET_DB to keep data
# =========================
@app.on_event("startup")
def init_db():
    reset = os.getenv("RESET_DB") == "1"
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

# =========================
# DEPENDENCIES
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def authorize(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

# =========================
# HEALTH
# =========================
@app.get("/health")
def health():
    return {"ok": True}

# =========================
# CONFIG (for dashboard JS)
# =========================
@app.get("/config")
def get_config():
    return {
        "api_base_url": os.getenv("API_BASE_URL")
    }

# =========================
# SMS API
# =========================
@app.post("/sms", dependencies=[Depends(authorize)])
def create_sms(sms: SMSCreate, db: Session = Depends(get_db)):
    db_sms = SMS(to=sms.to, message=sms.message, status="PENDING")
    db.add(db_sms)
    db.commit()
    db.refresh(db_sms)
    return {"id": db_sms.id, "status": "queued"}

@app.get("/sms")
def list_sms(
        status: str | None = Query(default=None),  # PENDING / SENT / FAILED
        to: str | None = Query(default=None),
        limit: int = Query(default=200, ge=1, le=2000),
        db: Session = Depends(get_db),
):
    q = db.query(SMS)
    if status:
        q = q.filter(SMS.status == status)
    if to:
        q = q.filter(SMS.to == to)

    return q.order_by(desc(SMS.created_at)).limit(limit).all()

@app.get("/sms/pending")
def get_pending_sms(db: Session = Depends(get_db)):
    return db.query(SMS).filter(SMS.status == "PENDING").all()

@app.patch("/sms/{sms_id}/mark-sent")
def mark_sms_sent(sms_id: str, db: Session = Depends(get_db)):
    sms = db.query(SMS).filter(SMS.id == sms_id).first()
    if not sms:
        raise HTTPException(status_code=404, detail="SMS not found")

    sms.status = "SENT"
    sms.sent_at = datetime.utcnow()
    sms.fail_reason = None
    db.commit()
    return {"status": "ok"}

@app.patch("/sms/{sms_id}/mark-failed")
def mark_sms_failed(
        sms_id: str,
        reason: str = Query(default="send_error"),
        db: Session = Depends(get_db),
):
    sms = db.query(SMS).filter(SMS.id == sms_id).first()
    if not sms:
        raise HTTPException(status_code=404, detail="SMS not found")

    sms.status = "FAILED"
    sms.fail_reason = reason
    sms.last_attempt_at = datetime.utcnow()
    sms.attempt_count = (sms.attempt_count or 0) + 1
    db.commit()
    return {"status": "ok"}

@app.post("/sms/{sms_id}/retry")
def retry_sms(sms_id: str, db: Session = Depends(get_db)):
    sms = db.query(SMS).filter(SMS.id == sms_id).first()
    if not sms:
        raise HTTPException(status_code=404, detail="SMS not found")

    sms.status = "PENDING"
    sms.fail_reason = None
    db.commit()
    return {"status": "queued"}

# =========================
# DASHBOARD (served by FastAPI)
# =========================
app.mount("/web", StaticFiles(directory="web"), name="web")

@app.get("/dashboard")
def dashboard():
    return FileResponse("web/index.html")
