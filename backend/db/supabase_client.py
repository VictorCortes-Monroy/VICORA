# /db/supabase_client.py
import os
from supabase import create_client, Client

def get_client() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
