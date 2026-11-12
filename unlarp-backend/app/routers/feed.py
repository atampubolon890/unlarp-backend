from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Follow, Post, User
from ..schemas import FeedOut
from ..services.posts import paginate

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("", response_model=FeedOut)
def home_feed(
    before_id: int | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Newest posts from people you follow, plus your own."""
    following = select(Follow.followed_id).where(Follow.follower_id == me.id)
    query = select(Post).where(or_(Post.user_id == me.id, Post.user_id.in_(following)))
    return paginate(db, query, me.id, before_id, limit)


@router.get("/explore", response_model=FeedOut)
def explore_feed(
    before_id: int | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Newest posts from everyone. Swap in ranking here later."""
    return paginate(db, select(Post), me.id, before_id, limit)
