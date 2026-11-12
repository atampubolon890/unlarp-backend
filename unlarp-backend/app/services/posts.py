"""Shared helpers for turning Post rows into API responses."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Comment, Like, Post
from ..schemas import FeedOut, PostOut


def serialize_posts(db: Session, posts: list[Post], viewer_id: int) -> list[PostOut]:
    if not posts:
        return []
    ids = [p.id for p in posts]
    like_counts = dict(
        db.execute(
            select(Like.post_id, func.count())
            .where(Like.post_id.in_(ids))
            .group_by(Like.post_id)
        ).all()
    )
    comment_counts = dict(
        db.execute(
            select(Comment.post_id, func.count())
            .where(Comment.post_id.in_(ids))
            .group_by(Comment.post_id)
        ).all()
    )
    liked = set(
        db.scalars(
            select(Like.post_id).where(Like.post_id.in_(ids), Like.user_id == viewer_id)
        )
    )
    return [
        PostOut(
            id=p.id,
            author_username=p.author.username,
            author_display_name=p.author.display_name,
            persona_name=p.persona.name if p.persona else None,
            persona_occupation=p.persona.occupation if p.persona else None,
            prompt=p.prompt,
            caption=p.caption,
            image_url=p.image_url,
            like_count=like_counts.get(p.id, 0),
            comment_count=comment_counts.get(p.id, 0),
            liked_by_me=p.id in liked,
            created_at=p.created_at,
        )
        for p in posts
    ]


def paginate(db: Session, query, viewer_id: int, before_id: int | None, limit: int) -> FeedOut:
    """Newest-first page of posts. `query` is a select(Post) with filters applied."""
    if before_id is not None:
        query = query.where(Post.id < before_id)
    rows = list(db.scalars(query.order_by(Post.id.desc()).limit(limit + 1)))
    has_more = len(rows) > limit
    rows = rows[:limit]
    return FeedOut(
        posts=serialize_posts(db, rows, viewer_id),
        next_before_id=rows[-1].id if has_more else None,
    )
