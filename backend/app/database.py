import logging
from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger("uvicorn")

def get_supabase() -> Client:
    """
    Returns an initialized Supabase Client.
    Will log warning if credentials are missing.
    """
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_KEY
    
    if not url or not key:
        logger.warning(
            "Supabase credentials (SUPABASE_URL, SUPABASE_KEY) are missing in environment configuration. "
            "Database/Auth calls will fail."
        )
    return create_client(url, key)
