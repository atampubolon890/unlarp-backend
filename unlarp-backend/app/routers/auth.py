from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import SignupIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupIn, db: Session = Depends(get_db)):
    username = body.username.lower()
    email = body.email.lower()
    taken = db.scalar(
        select(User).where(or_(User.username == username, User.email == email))
    )
    if taken:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username or email already in use")
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(body.password),
        display_name=body.display_name or body.username,
    )
    db.add(user)
    db.commit()
    return TokenOut(
        access_token=create_access_token(user.id), user=UserOut.model_validate(user)
    )


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Log in with a username (or email) and password, sent as form fields."""
    ident = form.username.lower()
    user = db.scalar(
        select(User).where(or_(User.username == ident, User.email == ident))
    )
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong username or password")
    return TokenOut(
        access_token=create_access_token(user.id), user=UserOut.model_validate(user)
    )
