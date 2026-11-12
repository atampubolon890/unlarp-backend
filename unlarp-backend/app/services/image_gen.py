"""Image generation.

`PlaceholderGenerator` makes a labeled stand-in image so the whole app works
without paying for a model. To go live, write a class with the same `generate`
method that calls your image model (passing the user's selfies as likeness
references) and return it from `get_image_generator`.
"""
import html
import textwrap
import uuid
from pathlib import Path
from typing import Protocol

from ..config import settings
from ..models import Persona

WATERMARK = "AI-GENERATED · UNLARP"


class ImageGenerator(Protocol):
    def generate(
        self, *, prompt: str, persona: Persona | None, selfie_paths: list[Path]
    ) -> str:
        """Create an image and return its public URL path (e.g. /media/...)."""
        ...


class PlaceholderGenerator:
    def generate(
        self, *, prompt: str, persona: Persona | None, selfie_paths: list[Path]
    ) -> str:
        out_dir = settings.media_dir / "generated"
        out_dir.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4().hex}.svg"

        lines = textwrap.wrap(prompt, width=38)[:6]
        text = "".join(
            f'<text x="540" y="{470 + i * 56}" text-anchor="middle" '
            f'font-size="40" fill="#fff">{html.escape(line)}</text>'
            for i, line in enumerate(lines)
        )
        role = html.escape(persona.occupation) if persona else "No persona"
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1080" '
            'font-family="sans-serif">'
            '<rect width="1080" height="1080" fill="#1b1b2f"/>'
            f'<text x="540" y="360" text-anchor="middle" font-size="64" '
            f'font-weight="bold" fill="#e94560">{role}</text>'
            f"{text}"
            f'<text x="1040" y="1040" text-anchor="end" font-size="28" '
            f'fill="#ffffff" opacity="0.7">{WATERMARK}</text>'
            "</svg>"
        )
        (out_dir / name).write_text(svg, encoding="utf-8")
        return f"/media/generated/{name}"


def get_image_generator() -> ImageGenerator:
    return PlaceholderGenerator()
