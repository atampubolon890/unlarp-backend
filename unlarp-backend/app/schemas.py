"""Request and response shapes."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth / users ----
class SignupIn(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_.]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=60)


class UserOut(ORMModel):
    id: int
    username: str
    display_name: str
    bio: str
    real_life_reveal: str | None
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserUpdateIn(BaseModel):
    display_name: str | None = Field(default=None, max_length=60)
    bio: str | None = Field(default=None, max_length=300)
    real_life_reveal: str | None = Field(default=None, max_length=120)


class PersonaOut(ORMModel):
    id: int
    name: str
    occupation: str
    backstory: str
    is_active: bool
    created_at: datetime


class ProfileOut(BaseModel):
    user: UserOut
    active_persona: PersonaOut | None
    follower_count: int
    following_count: int
    post_count: int
    is_following: bool


class SelfieOut(ORMModel):
    id: int
    created_at: datetime


# ---- personas ----
class PersonaIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    occupation: str = Field(min_length=1, max_length=80)
    backstory: str = Field(default="", max_length=2000)


class PersonaUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    occupation: str | None = Field(default=None, min_length=1, max_length=80)
    backstory: str | None = Field(default=None, max_length=2000)


# ---- posts ----
class PostIn(BaseModel):
    prompt: str = Field(min_length=3, max_length=1000)
    caption: str = Field(default="", max_length=500)
    # Defaults to the user's active persona.
    persona_id: int | None = None


class PostOut(BaseModel):
    id: int
    author_username: str
    author_display_name: str
    persona_name: str | None
    persona_occupation: str | None
    prompt: str
    caption: str
    image_url: str
    is_ai_generated: bool = True
    like_count: int
    comment_count: int
    liked_by_me: bool
    created_at: datetime


class FeedOut(BaseModel):
    posts: list[PostOut]
    # Pass as ?before_id= to get the next page; null when there are no more.
    next_before_id: int | None


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=500)


class CommentOut(BaseModel):
    id: int
    author_username: str
    body: str
    created_at: datetime
