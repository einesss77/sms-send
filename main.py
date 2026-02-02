from fastapi import FastAPI, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import SessionLocal, engine
from models import SMS, Base
from schemas import SMSCreate
import os
from datetime import datetime

API_KEY = os.getenv("API_KEY")
print("API_KEY loaded?", API_KEY is not None)
print("API_KEY length:", 0 if API_KEY is None else len(API_KEY))


Base.metadata.create_all(bind=engine)


app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def authorize(x_api_key: str = Header(...)):
    print("RECEIVED:", x_api_key)
    print("EXPECTED:", API_KEY)
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.post("/sms", dependencies=[Depends(authorize)])
def create_sms(sms: SMSCreate, db: Session = Depends(get_db)):
    db_sms = SMS(to=sms.to, message=sms.message, status="PENDING")
    db.add(db_sms)
    db.commit()
    db.refresh(db_sms)
    return {"id": db_sms.id, "status": "queued"}

# ✅ Historique (interface web + mobile vont taper ça)
@app.get("/sms")
def list_sms(
        status: str | None = Query(default=None),          # PENDING / SENT / FAILED
        to: str | None = Query(default=None),
        limit: int = Query(default=200, ge=1, le=2000),
        db: Session = Depends(get_db)
):
    q = db.query(SMS)
    if status:
        q = q.filter(SMS.status == status)
    if to:
        q = q.filter(SMS.to == to)

    return q.order_by(desc(SMS.created_at)).limit(limit).all()

# ✅ Pending pour l'app (inchangé conceptuellement)
@app.get("/sms/pending")
def get_pending_sms(db: Session = Depends(get_db)):
    return db.query(SMS).filter(SMS.status == "PENDING").all()

# ✅ Marquer comme envoyé (compat existant)
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

# ✅ Marquer comme failed (utile quand l'app échoue)
@app.patch("/sms/{sms_id}/mark-failed")
def mark_sms_failed(sms_id: str, reason: str = Query(default="send_error"), db: Session = Depends(get_db)):
    sms = db.query(SMS).filter(SMS.id == sms_id).first()
    if not sms:
        raise HTTPException(status_code=404, detail="SMS not found")

    sms.status = "FAILED"
    sms.fail_reason = reason
    sms.last_attempt_at = datetime.utcnow()
    sms.attempt_count = (sms.attempt_count or 0) + 1
    db.commit()
    return {"status": "ok"}

# ✅ Retry manuel (web + mobile)
@app.post("/sms/{sms_id}/retry")
def retry_sms(sms_id: str, db: Session = Depends(get_db)):
    sms = db.query(SMS).filter(SMS.id == sms_id).first()
    if not sms:
        raise HTTPException(status_code=404, detail="SMS not found")

    sms.status = "PENDING"
    sms.fail_reason = None
    db.commit()
    return {"status": "queued"}

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app.mount("/web", StaticFiles(directory="web"), name="web")

@app.get("/dashboard")
def dashboard():
    return FileResponse("web/index.html")
