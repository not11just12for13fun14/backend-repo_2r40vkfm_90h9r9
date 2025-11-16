import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Nadit API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Nadit Backend Ready"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from Nadit backend API"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except ImportError:
        response["database"] = "❌ Database module not found"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# Feedback endpoint
class FeedbackIn(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    message: str
    source: Optional[str] = "website"


@app.post("/api/feedback")
def submit_feedback(payload: FeedbackIn):
    # Store in database
    try:
        from database import create_document
        from schemas import Feedback as FeedbackSchema
        doc = FeedbackSchema(**payload.model_dump())
        inserted_id = create_document("feedback", doc)
    except Exception as e:
        # If DB not available, still accept but mark as not persisted
        inserted_id = None

    # Optional email notification via SMTP if environment is configured
    sent_email = False
    try:
        import smtplib
        from email.mime.text import MIMEText

        host = os.getenv("MAIL_HOST")
        port = int(os.getenv("MAIL_PORT", "0") or 0)
        user = os.getenv("MAIL_USER")
        password = os.getenv("MAIL_PASSWORD")
        to_email = os.getenv("FEEDBACK_TO", "info@nadit.com")

        if host and port and user and password:
            subject = "Nuovo feedback dal sito Nadit"
            body = f"Nome: {payload.name or '-'}\nEmail: {payload.email or '-'}\nOrigine: {payload.source or 'website'}\n\nMessaggio:\n{payload.message}"
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = user
            msg["To"] = to_email

            with smtplib.SMTP_SSL(host, port) as server:
                server.login(user, password)
                server.sendmail(user, [to_email], msg.as_string())
            sent_email = True
    except Exception:
        sent_email = False

    return {
        "status": "ok",
        "saved": inserted_id is not None,
        "id": inserted_id,
        "emailed": sent_email,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
