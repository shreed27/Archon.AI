from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database.db import get_db
from ..database.models import User
from ..auth.jwt import create_access_token
from pydantic import BaseModel
import requests

router = APIRouter()


class GoogleAuthRequest(BaseModel):
    token: str


@router.post("/google")
async def google_auth(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    # In a real app, verify the token with Google
    # For now, we'll assume the token is a mock but contains the email
    # Or use google-auth library

    # Mock verification for demonstration
    # email = verify_google_token(request.token)
    email = "user@example.com"  # Default for now

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(data={"sub": user.email})
    return {"token": access_token}


@router.get("/me")
async def get_me(
    user_email: str = Depends(create_access_token),
):  # Needs proper dependency injection
    return {"email": user_email}
