"""Generate ignored development secrets once without printing them."""

from pathlib import Path
import secrets


def main():
    root = Path(__file__).resolve().parents[2]
    target = root / ".env"
    if target.exists():
        raise SystemExit(".env already exists; preserved without changes.")
    value = (root / ".env.example").read_text()
    password = secrets.token_urlsafe(24)
    for old, new in {
        "replace-local-password": password,
        "replace-with-at-least-32-random-characters": secrets.token_urlsafe(48),
        "replace-with-local-learner-password": secrets.token_urlsafe(18),
        "replace-with-local-mentor-password": secrets.token_urlsafe(18),
    }.items():
        value = value.replace(old, new)
    target.write_text(value)
    print("Created ignored .env. Read demo credentials privately from that file.")


if __name__ == "__main__":
    main()
