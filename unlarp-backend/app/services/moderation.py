"""Prompt checks that run before any image is generated.

This keyword list is a placeholder so the pipeline has a moderation step from
day one. Before launch, replace `check_prompt` with a real moderation model or
API, and also scan the generated image itself.
"""

BLOCKED_TERMS = {
    "nude",
    "naked",
    "nsfw",
    "porn",
    "sexual",
    "gore",
    "child",
    "minor",
}


def check_prompt(prompt: str) -> str | None:
    """Return a reason the prompt is not allowed, or None if it is fine."""
    words = {w.strip(".,!?;:'\"()").lower() for w in prompt.split()}
    hit = words & BLOCKED_TERMS
    if hit:
        return "This prompt breaks the content rules."
    return None
