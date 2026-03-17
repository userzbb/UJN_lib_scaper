# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import sys

# Try to import pycryptodome for AES decryption
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
    """
    try:
        key = key_str.encode("utf-8")
        iv = iv_str.encode("utf-8")
        encrypted_bytes = base64.b64decode(encrypted_b64)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_bytes = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        print(f"Decryption error: {e}")
        return None


def calculate_hmac(secret_key, message):
    signature = hmac.new(
        bytes(secret_key, "utf-8"),
        msg=bytes(message, "utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return signature


def verify_hmac():
    print("正在验证潜在 HMAC 密钥...")

    # Data from a previous successful request capture
    # These values must match a real request to verify the signature
    captured_hmac = "3a0dd81a951b6f9171dd4856da9dc75448df5a7056b00bf8a6a473b8546c5cc0"
    req_date = "1773713088031"
    req_id = "b718255d-98a1-4119-8b9b-4e8bc32f2e2c"
    method = "GET"

    # Message format: seat::<UUID>::<Timestamp>::<Method>
    message = f"seat::{req_id}::{req_date}::{method}"
    print(f"[*] 构建消息 (Message): {message}")
    print(f"[*] 目标签名 (Target):  {captured_hmac}")
    print("-" * 50)

    # 1. The raw extracted secret from Vue.prototype.$NUMCODE
    raw_secret_b64 = "UmrX+lxhFE5neclEsBPing=="
    print(f"1. 尝试原始 Base64 密钥: {raw_secret_b64}")

    sig1 = calculate_hmac(raw_secret_b64, message)
    print(f"   计算结果: {sig1}")
    if sig1 == captured_hmac:
        print("   ✅ 成功匹配！密钥就是原始字符串！")
        return
    else:
        print("   ❌ 不匹配")

    print("-" * 50)

    # 2. Try to decrypt it (it looks like AES ciphertext)
    # Keys identified from JS analysis
    aes_key = "server_date_time"
    aes_iv = "client_date_time"

    print(f"2. 尝试 AES 解密密钥: {raw_secret_b64}")
    print(f"   AES Key: {aes_key}")
    print(f"   AES IV:  {aes_iv}")

    decrypted_secret = decrypt_aes(raw_secret_b64, aes_key, aes_iv)

    if decrypted_secret:
        print(f"   🔓 解密得到: {decrypted_secret}")
        sig2 = calculate_hmac(decrypted_secret, message)
        print(f"   计算结果: {sig2}")

        if sig2 == captured_hmac:
            print("\n   ✅✅✅ 成功匹配！HMAC 密钥已找到！")
            print(f"   真实密钥 (Real Secret): {decrypted_secret}")
        else:
            print("   ❌ 不匹配")
    else:
        print("   ❌ 解密失败")


if __name__ == "__main__":
    verify_hmac()
