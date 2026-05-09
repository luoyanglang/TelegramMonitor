"""
Bot authorization helpers.
"""

from decouple import config


def parse_authorized_user_ids(
    authorized_user_ids: object = "",
    fallback_user_id: object = "",
) -> set[int]:
    """Parse comma-separated admin IDs, falling back to the legacy single ID."""
    ids: set[int] = set()

    for raw_id in str(authorized_user_ids or "").split(","):
        raw_id = raw_id.strip()
        if raw_id:
            ids.add(int(raw_id))

    if not ids and fallback_user_id not in (None, ""):
        ids.add(int(fallback_user_id))

    if not ids:
        raise ValueError("AUTHORIZED_USER_IDS or AUTHORIZED_USER_ID is required")

    return ids


def load_authorized_user_ids() -> set[int]:
    """Load authorized admin IDs from environment configuration."""
    return parse_authorized_user_ids(
        config("AUTHORIZED_USER_IDS", default=""),
        config("AUTHORIZED_USER_ID", default=""),
    )
