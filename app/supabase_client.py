import os
from supabase import create_client, Client

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            os.environ['SUPABASE_URL'],
            os.environ['SUPABASE_SERVICE_ROLE_KEY'],
        )
    return _client


def fetch_one(query):
    """Return the first row of a built (not-yet-executed) query, or None.

    Safer than PostgREST's .maybe_single(), which returns HTTP 406 on zero rows
    and raises in some supabase-py versions — that turns an ordinary "no match"
    (e.g. a brand-new user or a stale shop_id) into a 500.
    """
    rows = query.limit(1).execute().data
    return rows[0] if rows else None
