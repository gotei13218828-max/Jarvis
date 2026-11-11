import base64
import json

from pathlib import Path

from .secure_storage import (
    _android_classes,
    _java_bytes,
    _python_bytes,
    _get_storage_path,
)


TEST_ALIAS = "jarvis_keystore_diagnostic_key"
TEST_FILENAME = "jarvis_keystore_diagnostic.enc"


def run_keystore_diagnostic():
    test_path = None
    store = None

    try:
        classes = _android_classes()
        autoclass = classes["autoclass"]

        KeyStore = autoclass("java.security.KeyStore")
        store = KeyStore.getInstance("AndroidKeyStore")
        store.load(None)

        # Remove only an earlier diagnostic key.
        if store.containsAlias(TEST_ALIAS):
            store.deleteEntry(TEST_ALIAS)

        KeyProperties = autoclass(
            "android.security.keystore.KeyProperties"
        )
        Builder = autoclass(
            "android.security.keystore.KeyGenParameterSpec$Builder"
        )
        KeyGenerator = autoclass("javax.crypto.KeyGenerator")
        Cipher = autoclass("javax.crypto.Cipher")
        GCMParameterSpec = autoclass(
            "javax.crypto.spec.GCMParameterSpec"
        )

        purposes = (
            KeyProperties.PURPOSE_ENCRYPT
            | KeyProperties.PURPOSE_DECRYPT
        )

        StringArray = classes["jarray"]("java.lang.String")
        builder = Builder(TEST_ALIAS, purposes)
        builder.setBlockModes(StringArray(["GCM"]))
        builder.setEncryptionPaddings(StringArray(["NoPadding"]))
        builder.setKeySize(256)
        builder.setRandomizedEncryptionRequired(True)

        generator = KeyGenerator.getInstance(
            "AES", "AndroidKeyStore"
        )
        generator.init(builder.build())
        key = generator.generateKey()

        original = json.dumps({
            "test": "Jarvis Keystore",
            "value": "encryption_verified",
        }).encode("utf-8")

        encryptor = Cipher.getInstance("AES/GCM/NoPadding")
        encryptor.init(Cipher.ENCRYPT_MODE, key)

        ciphertext = _python_bytes(
            encryptor.doFinal(_java_bytes(original))
        )
        iv = _python_bytes(encryptor.getIV())

        if len(iv) != 12:
            raise RuntimeError("Unexpected AES-GCM IV length.")

        # Use a dedicated diagnostic file.
        test_path = _get_storage_path().with_name(TEST_FILENAME)

        record = {
            "iv": base64.b64encode(iv).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }

        test_path.write_text(json.dumps(record), encoding="utf-8")

        stored = json.loads(test_path.read_text(encoding="utf-8"))

        decryptor = Cipher.getInstance("AES/GCM/NoPadding")
        decryptor.init(
            Cipher.DECRYPT_MODE,
            key,
            GCMParameterSpec(
                128,
                _java_bytes(base64.b64decode(stored["iv"])),
            ),
        )

        recovered = _python_bytes(
            decryptor.doFinal(
                _java_bytes(base64.b64decode(stored["ciphertext"]))
            )
        )

        if recovered != original:
            raise RuntimeError("Decrypted data does not match.")

        return "ANDROID KEYSTORE: ENCRYPTION AND DECRYPTION PASSED"

    except Exception as error:
        return (
            "ANDROID KEYSTORE DIAGNOSTIC FAILED: "
            + type(error).__name__
            + ": "
            + str(error)
        )

    finally:
        if test_path is not None:
            try:
                if test_path.exists():
                    test_path.unlink()
            except Exception:
                pass

        if store is not None:
            try:
                if store.containsAlias(TEST_ALIAS):
                    store.deleteEntry(TEST_ALIAS)
            except Exception:
                pass
