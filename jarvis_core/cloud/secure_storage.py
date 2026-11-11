import base64
import json
import os
from pathlib import Path


KEY_ALIAS = "jarvis_supabase_session_key"
STORAGE_FILENAME = "supabase_session.enc"


class SecureStorageError(Exception):
    pass


class SecureStorageUnavailable(SecureStorageError):
    pass


def _android_classes():
    try:
        from jnius import autoclass, jarray
    except ImportError as error:
        raise SecureStorageUnavailable(
            "Android Keystore is unavailable in this environment."
        ) from error

    return {"autoclass": autoclass, "jarray": jarray}


def _get_storage_path():
    try:
        from kivy.app import App

        app = App.get_running_app()
        if app is None:
            raise SecureStorageUnavailable(
                "Jarvis Android application is not running."
            )

        directory = Path(app.user_data_dir)
        directory.mkdir(parents=True, exist_ok=True)
        return directory / STORAGE_FILENAME

    except SecureStorageError:
        raise
    except Exception as error:
        raise SecureStorageError(
            "Could not access private application storage."
        ) from error


def _get_keystore():
    classes = _android_classes()
    autoclass = classes["autoclass"]

    KeyStore = autoclass("java.security.KeyStore")
    store = KeyStore.getInstance("AndroidKeyStore")
    store.load(None)

    return store, classes


def _get_or_create_key():
    store, classes = _get_keystore()
    autoclass = classes["autoclass"]

    if store.containsAlias(KEY_ALIAS):
        return store.getKey(KEY_ALIAS, None)

    KeyProperties = autoclass(
        "android.security.keystore.KeyProperties"
    )
    Builder = autoclass(
        "android.security.keystore.KeyGenParameterSpec$Builder"
    )
    KeyGenerator = autoclass("javax.crypto.KeyGenerator")

    purposes = (
        KeyProperties.PURPOSE_ENCRYPT
        | KeyProperties.PURPOSE_DECRYPT
    )

    StringArray = classes["jarray"]("java.lang.String")
    builder = Builder(KEY_ALIAS, purposes)

    builder.setBlockModes(StringArray(["GCM"]))
    builder.setEncryptionPaddings(StringArray(["NoPadding"]))
    builder.setKeySize(256)
    builder.setRandomizedEncryptionRequired(True)

    generator = KeyGenerator.getInstance("AES", "AndroidKeyStore")
    generator.init(builder.build())

    return generator.generateKey()


def _java_bytes(data):
    ByteArray = _android_classes()["jarray"]("b")
    return ByteArray([
        value if value < 128 else value - 256
        for value in data
    ])


def _python_bytes(data):
    return bytes(int(value) & 0xFF for value in data)


def _validate_session(session):
    if not isinstance(session, dict):
        raise SecureStorageError("Invalid session data.")

    if not isinstance(session.get("access_token"), str):
        raise SecureStorageError("Access token is missing.")

    if not isinstance(session.get("refresh_token"), str):
        raise SecureStorageError("Refresh token is missing.")

    user = session.get("user")
    if not isinstance(user, dict) or not user.get("id"):
        raise SecureStorageError("Valid user information is missing.")


def save_session(session):
    _validate_session(session)

    try:
        autoclass = _android_classes()["autoclass"]
        Cipher = autoclass("javax.crypto.Cipher")

        payload = json.dumps(session).encode("utf-8")
        key = _get_or_create_key()

        cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key)

        encrypted = _python_bytes(
            cipher.doFinal(_java_bytes(payload))
        )
        iv = _python_bytes(cipher.getIV())

        if len(iv) != 12:
            raise SecureStorageError(
                "Unexpected AES-GCM initialization vector."
            )

        record = {
            "version": 1,
            "iv": base64.b64encode(iv).decode("ascii"),
            "ciphertext": base64.b64encode(
                encrypted
            ).decode("ascii"),
        }

        path = _get_storage_path()
        temporary = path.with_suffix(".tmp")

        temporary.write_text(
            json.dumps(record),
            encoding="utf-8",
        )
        os.replace(temporary, path)

    except SecureStorageError:
        raise
    except Exception as error:
        raise SecureStorageError(
            "Could not securely save the session."
        ) from error


def load_session():
    path = _get_storage_path()

    if not path.exists():
        return None

    try:
        record = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(record, dict):
            raise SecureStorageError("Invalid encrypted storage record.")

        if record.get("version") != 1:
            raise SecureStorageError(
                "Unsupported session storage version."
            )

        iv = base64.b64decode(record["iv"], validate=True)
        encrypted = base64.b64decode(
            record["ciphertext"],
            validate=True,
        )

        if len(iv) != 12 or not encrypted:
            raise SecureStorageError(
                "Invalid encrypted session data."
            )

        store, classes = _get_keystore()

        if not store.containsAlias(KEY_ALIAS):
            raise SecureStorageError(
                "Encryption key is missing. Session cannot be recovered."
            )

        autoclass = classes["autoclass"]
        Cipher = autoclass("javax.crypto.Cipher")
        GCMParameterSpec = autoclass(
            "javax.crypto.spec.GCMParameterSpec"
        )

        key = store.getKey(KEY_ALIAS, None)
        cipher = Cipher.getInstance("AES/GCM/NoPadding")

        cipher.init(
            Cipher.DECRYPT_MODE,
            key,
            GCMParameterSpec(128, _java_bytes(iv)),
        )

        decrypted = _python_bytes(
            cipher.doFinal(_java_bytes(encrypted))
        )

        session = json.loads(decrypted.decode("utf-8"))
        _validate_session(session)

        return session

    except SecureStorageError:
        raise
    except Exception as error:
        raise SecureStorageError(
            "Could not decrypt the stored session."
        ) from error


def delete_session():
    path = _get_storage_path()
    deletion_error = None

    try:
        if path.exists():
            path.unlink()
    except Exception as error:
        deletion_error = error

    try:
        store, _ = _get_keystore()

        if store.containsAlias(KEY_ALIAS):
            store.deleteEntry(KEY_ALIAS)

    except Exception as error:
        if deletion_error is None:
            deletion_error = error

    if deletion_error is not None:
        raise SecureStorageError(
            "Could not completely delete the stored session."
        ) from deletion_error
