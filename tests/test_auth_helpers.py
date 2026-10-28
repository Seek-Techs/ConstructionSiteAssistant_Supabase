from unittest.mock import MagicMock

import auth_helpers
from supabase_auth.errors import AuthInvalidJwtError, AuthRetryableError

def test_register_user_calls_supabase_signup():
    client = MagicMock()

    auth_helpers.register_user(client, "  test@example.com  ", "ExamplePassword123!")

    client.auth.sign_up.assert_called_once_with(
        {
            "email": "test@example.com",
            "password": "ExamplePassword123!",
        }
    )


def test_sign_in_user_calls_supabase_password_login():
    client = MagicMock()

    auth_helpers.sign_in_user(client, "  test@example.com  ", "ExamplePassword123!")

    client.auth.sign_in_with_password.assert_called_once_with(
        {
            "email": "test@example.com",
            "password": "ExamplePassword123!",
        }
    )


def test_password_reset_uses_trimmed_email():
    client = MagicMock()

    auth_helpers.request_password_reset(client, "  test@example.com  ")

    client.auth.reset_password_for_email.assert_called_once_with("test@example.com")


def test_sign_out_calls_supabase_sign_out():
    client = MagicMock()

    auth_helpers.sign_out_user(client)

    client.auth.sign_out.assert_called_once_with()

def test_get_validated_user_returns_user_when_supabase_validates_session():
    client = MagicMock()
    expected_user = MagicMock()
    client.auth.get_user.return_value.user = expected_user

    actual_user = auth_helpers.get_validated_user(client)

    assert actual_user is expected_user
    client.auth.get_user.assert_called_once_with()


def test_get_validated_user_returns_none_when_jwt_is_invalid():
    client = MagicMock()
    client.auth.get_user.side_effect = AuthInvalidJwtError(
        "Invalid JWT"
    )

    actual_user = auth_helpers.get_validated_user(client)

    assert actual_user is None
    client.auth.get_user.assert_called_once_with()


def test_get_validated_user_does_not_hide_retryable_auth_errors():
    client = MagicMock()
    client.auth.get_user.side_effect = AuthRetryableError(
        "Temporary authentication failure",
        503,
    )

    try:
        auth_helpers.get_validated_user(client)
    except AuthRetryableError:
        pass
    else:
        raise AssertionError(
            "A retryable authentication error should propagate"
        )

    client.auth.get_user.assert_called_once_with()
