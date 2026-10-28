"""Authentication helpers for Construction Site Assistant."""

import streamlit as st
from supabase import Client, create_client
from supabase_auth.errors import AuthInvalidJwtError

def create_supabase_client() -> Client:
    """Create a Supabase client using the project's Streamlit secrets."""
    url = st.secrets["SUPABASE_URL"]
    publishable_key = st.secrets["SUPABASE_PUBLISHABLE_KEY"]

    return create_client(url, publishable_key)


def register_user(client: Client, email: str, password: str):
    """Register a user with Supabase Auth."""
    return client.auth.sign_up(
        {
            "email": email.strip(),
            "password": password,
        }
    )


def sign_in_user(client: Client, email: str, password: str):
    """Sign in with email and password."""
    return client.auth.sign_in_with_password(
        {
            "email": email.strip(),
            "password": password,
        }
    )


def request_password_reset(client: Client, email: str):
    """Request a password-reset email."""
    return client.auth.reset_password_for_email(email.strip())


def sign_out_user(client: Client):
    """Sign out the current authenticated session."""
    return client.auth.sign_out()


def get_validated_user(client: Client):
    """Return the user only if Supabase validates the current session."""
    try:
        response = client.auth.get_user()
        return response.user
    except AuthInvalidJwtError:
        return None
