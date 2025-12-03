from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import SMS, Base
from schemas import SMSCreate

API_KEY = "SECRET123"  # à sécuriser ensuite

Base.metadata.create_all(bind=engine)
app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def authorize(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.post("/sms", dependencies=[Depends(authorize)])
def create_sms(sms: SMSCreate, db: Session = Depends(get_db)):
    db_sms = SMS(to=sms.to, message=sms.message)
    db.add(db_sms)
    db.commit()
    db.refresh(db_sms)
    return {"id": db_sms.id, "status": "queued"}

@app.get("/sms/pending")
def get_pending_sms(db: Session = Depends(get_db)):
    return db.query(SMS).filter(SMS.sent == False).all()

@app.patch("/sms/{sms_id}/mark-sent")
def mark_sms_sent(sms_id: str, db: Session = Depends(get_db)):
    sms = db.query(SMS).filter(SMS.id == sms_id).first()
    if not sms:
        raise HTTPException(status_code=404, detail="SMS not found")
    sms.sent = True
    db.commit()
    return {"status": "ok"}
