import base64
import re
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
        key = key_str.encode("utf-8")
        iv = iv_str.encode("utf-8")
        encrypted = base64.b64decode(encrypted_b64)

        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)
        return decrypted.decode("utf-8")
    except Exception as e:
        print(f"Decryption error: {e}")
        return None


def main():
    js_file = "app.js"

    print(f"[*] Reading {js_file}...")
    try:
        with open(js_file, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"[-] File '{js_file}' not found.")
        print(
            "    Please run: curl -o app.js https://seat.ujn.edu.cn/libseat/static/js/app.91deae66c4be3b22b18d.js"
        )
        return

    print("[*] Searching for $NUMCODE inside module '/5sW'...")

    # Pattern to capture value of $NUMCODE inside the exports object
    # Matches: $NUMCODE:"<value>"
    regex_pattern = r'\$NUMCODE\s*:\s*["\']([^"\']+)["\']'

    # Since the file is minified, we look around "/5sW" if it exists.
    module_start = content.find('"/5sW":')
    if module_start != -1:
        print("[+] Found module '/5sW'")
        # Search in the vicinity of this module
        chunk = content[module_start : module_start + 500]
        match = re.search(regex_pattern, chunk)
    else:
        print("[-] Module '/5sW' not found, searching globally...")
        match = re.search(regex_pattern, content)

    if match:
        encrypted_value = match.group(1)
        print(f"[+] Found encrypted value: {encrypted_value}")

        # Keys identified from JS analysis
        # decrypt function uses:
        # Key: "server_date_time"
        # IV: "client_date_time"

        key = "server_date_time"
        iv = "client_date_time"

        print(f"[*] Decrypting using Key='{key}', IV='{iv}'...")
        decrypted_secret = decrypt_aes(encrypted_value, key, iv)

        if decrypted_secret:
            print(f"\n✅ Decrypted HMAC Secret: {decrypted_secret}")

            # Save to file
            with open("hmac_secret.txt", "w") as f:
                f.write(decrypted_secret)
            print("[*] Saved secret to 'hmac_secret.txt'")
        else:
            print("[-] Decryption failed.")
    else:
        print("[-] Could not find $NUMCODE in app.js")
        print(
            "    The variable might be in another JS file or the minification pattern is different."
        )


if __name__ == "__main__":
    main()
