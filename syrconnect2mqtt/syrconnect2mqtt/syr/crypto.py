from Crypto.Cipher import AES
import base64


KEY = bytes.fromhex("d805a5c409dc354b6ccf03a2c29a5825851cf31979abf526ede72570c52cf954")
IV = bytes.fromhex("408a42beb8a1cefad990098584ed51a5")


class SYRCrypto:
    @staticmethod
    def decrypt_base64(payload: str) -> str:
        encrypted = base64.b64decode(payload)
        cipher = AES.new(KEY, AES.MODE_CBC, IV)
        decrypted = cipher.decrypt(encrypted)
        return decrypted.decode("utf-8", errors="ignore").rstrip("\x00")

    @staticmethod
    def encrypt_to_base64(plaintext: str) -> str:
        data = plaintext.encode("utf-8")
        pad_len = (16 - (len(data) % 16)) % 16
        data += b"\x00" * pad_len
        cipher = AES.new(KEY, AES.MODE_CBC, IV)
        encrypted = cipher.encrypt(data)
        return base64.b64encode(encrypted).decode("utf-8")
