import json
import urllib.request
import urllib.error

from .config import SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY


class SupabaseAuthError(Exception):
    pass


def _request(endpoint, payload, access_token=None):
    url = SUPABASE_URL.rstrip("/") + endpoint

    headers = {
        "apikey": SUPABASE_PUBLISHABLE_KEY,
        "Authorization": "Bearer " + (
            access_token or SUPABASE_PUBLISHABLE_KEY
        ),
        "Content-Type": "application/json",
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = response.read().decode("utf-8")

        if not result:
            return {}

        result = json.loads(result)

        if not isinstance(result, dict):
            raise SupabaseAuthError(
                "Supabase returned an unexpected response."
            )

        return result

    except urllib.error.HTTPError as error:
        try:
            details = json.loads(error.read().decode("utf-8"))
            message = (
                details.get("msg")
                or details.get("message")
                or details.get("error_description")
                or details.get("error")
            )
        except Exception:
            message = None

        raise SupabaseAuthError(
            message or "Supabase authentication failed."
        ) from None

    except urllib.error.URLError:
        raise SupabaseAuthError(
            "Unable to connect to Supabase. Check your internet connection."
        ) from None

    except TimeoutError:
        raise SupabaseAuthError(
            "Supabase request timed out. Please try again."
        ) from None

    except (json.JSONDecodeError, UnicodeDecodeError):
        raise SupabaseAuthError(
            "Supabase returned an invalid response."
        ) from None


def _validate_credentials(email, password):
    if not isinstance(email, str) or not email.strip():
        raise SupabaseAuthError("A valid email address is required.")

    if not isinstance(password, str) or not password:
        raise SupabaseAuthError("Password is required.")

    email = email.strip()

    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise SupabaseAuthError("Please enter a valid email address.")

    return email, password


def signup(email, password):
    email, password = _validate_credentials(email, password)

    return _request(
        "/auth/v1/signup",
        {
            "email": email,
            "password": password,
        },
    )


def login(email, password):
    email, password = _validate_credentials(email, password)

    return _request(
        "/auth/v1/token?grant_type=password",
        {
            "email": email,
            "password": password,
        },
    )


def refresh_session(refresh_token):
    if not isinstance(refresh_token, str) or not refresh_token:
        raise SupabaseAuthError("Refresh token is required.")

    return _request(
        "/auth/v1/token?grant_type=refresh_token",
        {
            "refresh_token": refresh_token,
        },
    )


def logout(access_token):
    if not isinstance(access_token, str) or not access_token:
        raise SupabaseAuthError("Access token is required.")

    return _request(
        "/auth/v1/logout",
        {},
        access_token=access_token,
    )
