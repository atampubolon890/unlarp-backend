from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Persona, Post, User
from ..schemas import PersonaIn, PersonaOut, PersonaUpdateIn

router = APIRouter(prefix="/personas", tags=["personas"])


def _get_mine_or_404(db: Session, persona_id: int, me: User) -> Persona:
    persona = db.get(Persona, persona_id)
    if not persona or persona.user_id != me.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Persona not found")
    return persona


@router.get("", response_model=list[PersonaOut])
def list_my_personas(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(
        db.scalars(select(Persona).where(Persona.user_id == me.id).order_by(Persona.id))
    )


@router.post("", response_model=PersonaOut, status_code=status.HTTP_201_CREATED)
def create_persona(
    body: PersonaIn,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    has_any = db.scalar(select(Persona.id).where(Persona.user_id == me.id).limit(1))
    # The first persona becomes the active one automatically.
    persona = Persona(user_id=me.id, is_active=has_any is None, **body.model_dump())
    db.add(persona)
    db.commit()
    return persona


@router.patch("/{persona_id}", response_model=PersonaOut)
def update_persona(
    persona_id: int,
    body: PersonaUpdateIn,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = _get_mine_or_404(db, persona_id, me)
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(persona, field, value)
    db.commit()
    return persona


@router.post("/{persona_id}/activate", response_model=PersonaOut)
def activate_persona(
    persona_id: int,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Switch which life you are currently posting as."""
    persona = _get_mine_or_404(db, persona_id, me)
    db.execute(update(Persona).where(Persona.user_id == me.id).values(is_active=False))
    persona.is_active = True
    db.commit()
    db.refresh(persona)
    return persona


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(
    persona_id: int,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = _get_mine_or_404(db, persona_id, me)
    # Keep the posts; they just lose their persona label.
    db.execute(update(Post).where(Post.persona_id == persona.id).values(persona_id=None))
    db.delete(persona)
    db.commit()
