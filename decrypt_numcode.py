# -*- coding: utf-8 -*-
import base64
import sys

# Try to import pycryptodome
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
except ImportError:
    print("Error: 'pycryptodome' is required.")
    print("Please install it using: pip install pycryptodome")
    sys.exit(1)


def decrypt_aes(encrypted_b64, key_str, iv_str):
    """
    Decrypt AES-128-CBC encrypted string.
    Key and IV are UTF-8 strings.
    """
    try:
        # In the JS (AOJh module), keys are parsed as UTF-8
        key = key_str.encode("utf-8")
        iv = iv_str.encode("utf-8")

        encrypted_bytes = base64.b64decode(encrypted_b64)

        cipher = AES.new(key, AES.MODE_CBC, iv)
        # JS uses Pkcs7 padding
        decrypted_bytes = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        print(f"Decryption error: {e}")
        return None


def main():
    # The specific base64 string provided
    # Note: User extracted this from app.js (suspected to be $NUMCODE)
    target_ciphertext = "yF23mqlZqjx9siSFna8uRA=="

    # Keys identified from JS analysis (AOJh module)
    # Key default: "server_date_time"
    # IV default:  "client_date_time"
    key = "server_date_time"
    iv = "client_date_time"

    print(f"[*] Ciphertext: {target_ciphertext}")
    print(f"[*] Key: {key}")
    print(f"[*] IV:  {iv}")

    decrypted_value = decrypt_aes(target_ciphertext, key, iv)

    if decrypted_value:
        print(f"\n✅ Decrypted Result: {decrypted_value}")

        # Validation logic based on context
        if decrypted_value == "080518":
            print("\n⚠️  NOTE: The result '080518' matches the test password.")
            print(
                "    This confirms the encryption keys are correct, but the ciphertext"
            )
            print(
                "    provided appears to be the encrypted password, not the HMAC secret."
            )
            print("    Please look for the real '$NUMCODE' value in the JS files.")
    else:
        print("\n❌ Decryption Failed")


if __name__ == "__main__":
    main()
