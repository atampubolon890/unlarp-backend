from datetime import datetime, time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Comment, Like, Persona, Post, SelfieReference, User, utcnow
from ..schemas import CommentIn, CommentOut, PostIn, PostOut
from ..services.image_gen import ImageGenerator, get_image_generator
from ..services.moderation import check_prompt
from ..services.posts import serialize_posts

router = APIRouter(tags=["posts"])


def _get_post_or_404(db: Session, post_id: int) -> Post:
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")
    return post


def _comment_out(c: Comment) -> CommentOut:
    return CommentOut(
        id=c.id, author_username=c.author.username, body=c.body, created_at=c.created_at
    )


@router.post("/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    body: PostIn,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    generator: ImageGenerator = Depends(get_image_generator),
):
    """Generate an AI photo of the user from a prompt and post it."""
    reason = check_prompt(body.prompt) or check_prompt(body.caption)
    if reason:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)

    selfies = list(
        db.scalars(select(SelfieReference).where(SelfieReference.user_id == me.id))
    )
    if not selfies:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Upload a selfie before generating photos"
        )

    midnight = datetime.combine(utcnow().date(), time.min)
    used_today = db.scalar(
        select(func.count())
        .select_from(Post)
        .where(Post.user_id == me.id, Post.created_at >= midnight)
    )
    if used_today >= settings.daily_generation_limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Daily limit of {settings.daily_generation_limit} generations reached",
        )

    if body.persona_id is not None:
        persona = db.get(Persona, body.persona_id)
        if not persona or persona.user_id != me.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Persona not found")
    else:
        persona = db.scalar(
            select(Persona).where(Persona.user_id == me.id, Persona.is_active.is_(True))
        )

    image_url = generator.generate(
        prompt=body.prompt,
        persona=persona,
        selfie_paths=[Path(s.file_path) for s in selfies],
    )
    post = Post(
        user_id=me.id,
        persona_id=persona.id if persona else None,
        prompt=body.prompt,
        caption=body.caption,
        image_url=image_url,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return serialize_posts(db, [post], me.id)[0]


@router.get("/posts/{post_id}", response_model=PostOut)
def read_post(
    post_id: int,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return serialize_posts(db, [_get_post_or_404(db, post_id)], me.id)[0]


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = _get_post_or_404(db, post_id)
    if post.user_id != me.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your post")
    db.delete(post)
    db.commit()


@router.post("/posts/{post_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def like_post(
    post_id: int,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = _get_post_or_404(db, post_id)
    exists = db.scalar(
        select(Like).where(Like.user_id == me.id, Like.post_id == post.id)
    )
    if not exists:
        db.add(Like(user_id=me.id, post_id=post.id))
        db.commit()


@router.delete("/posts/{post_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def unlike_post(
    post_id: int,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.scalar(select(Like).where(Like.user_id == me.id, Like.post_id == post_id))
    if row:
        db.delete(row)
        db.commit()


@router.get("/posts/{post_id}/comments", response_model=list[CommentOut])
def list_comments(
    post_id: int,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_post_or_404(db, post_id)
    rows = db.scalars(
        select(Comment).where(Comment.post_id == post_id).order_by(Comment.id)
    )
    return [_comment_out(c) for c in rows]


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(
    post_id: int,
    body: CommentIn,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = _get_post_or_404(db, post_id)
    comment = Comment(user_id=me.id, post_id=post.id, body=body.body)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _comment_out(comment)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: int,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comment not found")
    post = db.get(Post, comment.post_id)
    # The commenter or the post's owner can remove a comment.
    if me.id not in (comment.user_id, post.user_id if post else None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
    db.delete(comment)
    db.commit()
