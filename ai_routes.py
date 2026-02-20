from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
import database_models
from database import get_db
import uuid
import requests
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/ai", tags=["AI"])

limiter = Limiter(key_func=get_remote_address)


# ================================
# Schemas
# ================================

class RegisterRequest(BaseModel):
    email: str


class GenerateRequest(BaseModel):
    api_key: str
    message: str


class UpgradeRequest(BaseModel):
    email: str


# ================================
# Helpers
# ================================

def classify_message(message: str) -> str:
    msg = message.lower()

    if "not interested" in msg:
        return "Objection"
    if "follow" in msg:
        return "Follow-up"
    if "interested" in msg:
        return "Interested"
    if "?" in msg:
        return "Question"

    return "Cold Intro"


def build_prompt(message: str) -> str:
    return f"""
Reply in under 60 words.
Professional LinkedIn tone.
Be concise and conversion-focused.

Message:
{message}
"""


def call_groq(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama3-70b-8192",
        "max_tokens": 200,
        "messages": [
            {"role": "system", "content": "You are a LinkedIn reply expert."},
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=15
    )

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=response.text)

    data = response.json()
    return data["choices"][0]["message"]["content"]


def get_daily_limit(plan: str) -> int:
    return 30 if plan == "paid" else 3


# ================================
# Routes
# ================================

@router.post("/register")
def register_user(req: RegisterRequest, db: Session = Depends(get_db)):

    user = db.query(database_models.AIUser).filter(
        database_models.AIUser.email == req.email
    ).first()

    if not user:
        user = database_models.AIUser(
            email=req.email,
            api_key=uuid.uuid4().hex,
            usage_count=0,
            last_reset=str(date.today()),
            plan="free"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return {"api_key": user.api_key, "plan": user.plan}


@router.post("/generate")
@limiter.limit("20/minute")
def generate_reply(
    request: Request,
    req: GenerateRequest,
    db: Session = Depends(get_db)
):

    user = db.query(database_models.AIUser).filter(
        database_models.AIUser.api_key == req.api_key
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    today = str(date.today())

    if user.last_reset != today:
        user.usage_count = 0
        user.last_reset = today
        db.commit()

    limit = get_daily_limit(user.plan)

    if user.usage_count >= limit:
        raise HTTPException(status_code=403, detail="Daily limit reached")

    prompt = build_prompt(req.message)
    ai_reply = call_groq(prompt)

    user.usage_count += 1
    db.commit()

    return {
        "reply": ai_reply.strip(),
        "replies_left": limit - user.usage_count,
        "detected_type": classify_message(req.message)
    }


@router.post("/upgrade")
def upgrade_user(req: UpgradeRequest, db: Session = Depends(get_db)):

    user = db.query(database_models.AIUser).filter(
        database_models.AIUser.email == req.email
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.plan = "paid"
    db.commit()

    return {"message": "User upgraded to paid plan"}
