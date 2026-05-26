from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.jwt import create_token
from app.auth.security import hash_password, verify_password
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/api/v1")


class AuthRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(request: AuthRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    return {"token": create_token(user.username), "user_id": user.username}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: AuthRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == request.username).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="user already exists")
    user = User(username=request.username, password_hash=hash_password(request.password))
    db.add(user)
    db.commit()
    return {
        "token": create_token(user.username),
        "user_id": user.username,
        "message": "user created successfully",
    }

