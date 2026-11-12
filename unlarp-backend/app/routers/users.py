import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Follow, Persona, Post, SelfieReference, User
from ..schemas import (
    FeedOut,
    PersonaOut,
    ProfileOut,
    SelfieOut,
    UserOut,
    UserUpdateIn,
)
from ..services.posts import paginate

router = APIRouter(prefix="/users", tags=["users"])

ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _get_user_or_404(db: Session, username: str) -> User:
    user = db.scalar(select(User).where(User.username == username.lower()))
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


def _count(db: Session, query) -> int:
    return db.scalar(select(func.count()).select_from(query.subquery())) or 0


@router.get("/me", response_model=UserOut)
def read_me(me: User = Depends(get_current_user)):
    return me


@router.patch("/me", response_model=UserOut)
def update_me(
    body: UserUpdateIn,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for field, value in body.model_dump(exclude_unset=True).items():
        # display_name and bio are never null; only the reveal can be cleared.
        if value is None and field != "real_life_reveal":
            continue
        setattr(me, field, value)
    db.add(me)
    db.commit()
    return me


@router.post("/me/selfies", response_model=SelfieOut, status_code=status.HTTP_201_CREATED)
async def upload_selfie(
    file: UploadFile,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a reference photo of yourself for the image model.

    TODO before launch: add a live selfie check here so people can only
    upload their own face, never someone else's photos.
    """
    ext = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if not ext:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Upload a JPEG, PNG or WebP image"
        )
    data = await file.read(settings.max_selfie_bytes + 1)
    if len(data) > settings.max_selfie_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Image is too large")
    existing = _count(db, select(SelfieReference).where(SelfieReference.user_id == me.id))
    if existing >= settings.max_selfies_per_user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Selfie limit reached")

    # Selfies are private: stored outside the public /media/generated folder.
    folder = settings.media_dir / "selfies" / str(me.id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex}{ext}"
    path.write_bytes(data)

    selfie = SelfieReference(user_id=me.id, file_path=str(path))
    db.add(selfie)
    db.commit()
    return selfie


@router.get("/{username}", response_model=ProfileOut)
def read_profile(
    username: str,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(db, username)
    active = db.scalar(
        select(Persona).where(Persona.user_id == user.id, Persona.is_active.is_(True))
    )
    is_following = (
        db.scalar(
            select(Follow).where(
                Follow.follower_id == me.id, Follow.followed_id == user.id
            )
        )
        is not None
    )
    return ProfileOut(
        user=UserOut.model_validate(user),
        active_persona=PersonaOut.model_validate(active) if active else None,
        follower_count=_count(db, select(Follow).where(Follow.followed_id == user.id)),
        following_count=_count(db, select(Follow).where(Follow.follower_id == user.id)),
        post_count=_count(db, select(Post).where(Post.user_id == user.id)),
        is_following=is_following,
    )


@router.get("/{username}/posts", response_model=FeedOut)
def read_user_posts(
    username: str,
    before_id: int | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(db, username)
    return paginate(db, select(Post).where(Post.user_id == user.id), me.id, before_id, limit)


@router.post("/{username}/follow", status_code=status.HTTP_204_NO_CONTENT)
def follow(
    username: str,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(db, username)
    if user.id == me.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot follow yourself")
    exists = db.scalar(
        select(Follow).where(Follow.follower_id == me.id, Follow.followed_id == user.id)
    )
    if not exists:
        db.add(Follow(follower_id=me.id, followed_id=user.id))
        db.commit()


@router.delete("/{username}/follow", status_code=status.HTTP_204_NO_CONTENT)
def unfollow(
    username: str,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(db, username)
    row = db.scalar(
        select(Follow).where(Follow.follower_id == me.id, Follow.followed_id == user.id)
    )
    if row:
        db.delete(row)
        db.commit()
