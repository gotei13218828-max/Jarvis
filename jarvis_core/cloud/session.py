from .auth import login, signup, refresh_session, logout
from .secure_storage import (
    save_session,
    load_session,
    delete_session,
)


class SessionManager:
    def __init__(self):
        self.session = None

    @property
    def is_authenticated(self):
        return bool(
            isinstance(self.session, dict)
            and self.session.get("access_token")
            and isinstance(self.session.get("user"), dict)
            and self.session["user"].get("id")
        )

    @property
    def user_id(self):
        if not self.is_authenticated:
            return None
        return self.session["user"]["id"]

    def create_account(self, email, password):
        return signup(email, password)

    def _validate_session(self, result):
        if not isinstance(result, dict):
            raise ValueError("Invalid authentication response.")

        if not result.get("access_token"):
            raise ValueError("Authentication response has no access token.")

        if not result.get("refresh_token"):
            raise ValueError("Authentication response has no refresh token.")

        if not isinstance(result.get("user"), dict):
            raise ValueError("Authentication response has no user.")

        if not result["user"].get("id"):
            raise ValueError("Authentication response has no user ID.")

        return result

    def sign_in(self, email, password):
        result = self._validate_session(login(email, password))

        # Save encrypted credentials before activating the session.
        save_session(result)

        self.session = result
        return result

    def restore_session(self, saved_session=None):
        if saved_session is None:
            saved_session = load_session()

        if not saved_session:
            self.session = None
            return False

        if not isinstance(saved_session, dict):
            self.session = None
            raise ValueError("Stored session is invalid.")

        refresh_token = saved_session.get("refresh_token")

        if not refresh_token:
            self.session = None
            return False

        # Preserve stored credentials if a network error occurs.
        result = self._validate_session(
            refresh_session(refresh_token)
        )

        # Persist rotated credentials before activating them.
        save_session(result)

        self.session = result
        return True

    def get_access_token(self):
        if not self.is_authenticated:
            return None
        return self.session["access_token"]

    def sign_out(self):
        token = self.get_access_token()
        logout_error = None
        storage_error = None

        try:
            if token:
                logout(token)
        except Exception as error:
            logout_error = error

        # Always clear the in-memory session.
        self.session = None

        try:
            delete_session()
        except Exception as error:
            storage_error = error

        if logout_error:
            raise logout_error

        if storage_error:
            raise storage_error

    def clear_session(self):
        # Clears memory only; persistent credentials remain untouched.
        self.session = None


session_manager = SessionManager()
