# Unlarp backend

Starter API for Unlarp: accounts, personas, AI-generated posts, a feed, likes,
comments and follows. Built with FastAPI, SQLAlchemy and SQLite.

## Run it

```bash
cd unlarp-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive docs where you can try every
endpoint. Click **Authorize** and log in to call the protected ones.

Run the tests with `pytest`.

## Settings

Set through environment variables; see `.env.example`. Set a real
`UNLARP_SECRET_KEY` before deploying anywhere.

## Endpoints

| Area | Endpoint | What it does |
|---|---|---|
| Auth | `POST /auth/signup` | Create an account, returns a token |
| | `POST /auth/login` | Log in (form fields `username`, `password`) |
| Users | `GET /users/me`, `PATCH /users/me` | Read or edit your account, including the optional real-life reveal |
| | `POST /users/me/selfies` | Upload a reference photo of yourself |
| | `GET /users/{username}` | Profile with follower, following and post counts |
| | `GET /users/{username}/posts` | That user's posts |
| | `POST` / `DELETE /users/{username}/follow` | Follow or unfollow |
| Personas | `GET /personas`, `POST /personas` | List or create your personas |
| | `PATCH` / `DELETE /personas/{id}` | Edit or delete one |
| | `POST /personas/{id}/activate` | Switch which persona you post as |
| Posts | `POST /posts` | Generate a photo from a prompt and post it |
| | `GET` / `DELETE /posts/{id}` | Read or delete a post |
| | `POST` / `DELETE /posts/{id}/like` | Like or unlike |
| | `GET` / `POST /posts/{id}/comments` | Read or add comments |
| | `DELETE /comments/{id}` | Delete a comment (commenter or post owner) |
| Feed | `GET /feed` | Posts from people you follow, plus your own |
| | `GET /feed/explore` | Newest posts from everyone |

Feeds are paginated: pass the `next_before_id` from one response as
`?before_id=` to get the next page.

## What is stubbed

These parts are placeholders, marked in the code, and need real
implementations before launch:

- **Image generation** (`app/services/image_gen.py`). It currently writes a
  labeled placeholder image. Add a class with the same `generate` method that
  calls a real image model with the user's selfies, and return it from
  `get_image_generator`.
- **Moderation** (`app/services/moderation.py`). A short keyword list. Replace
  it with a moderation model, and scan generated images too.
- **Selfie verification** (`app/routers/users.py`). Uploads are accepted
  without checking that the face belongs to the uploader. Add a live selfie
  check.

## Already in place

- Passwords hashed with bcrypt; login tokens are JWTs.
- A daily generation limit per user (`UNLARP_DAILY_GENERATION_LIMIT`).
- Every post is flagged `is_ai_generated`, and the placeholder images carry a
  watermark.
- Selfies are stored privately and never served over the web.

## Next steps

1. Connect a real image model.
2. Move from SQLite to Postgres and add Alembic migrations.
3. Store images in object storage (S3 or similar) instead of local disk.
4. Run generation as a background job so `POST /posts` returns immediately.
5. Add reporting and blocking, an age gate, and email verification.
6. Add the bigger features: storylines, collab posts, remixing, weekly prompts.
