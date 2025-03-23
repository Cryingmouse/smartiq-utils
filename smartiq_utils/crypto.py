import base64
from typing import Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers import modes

SECRET_KEY = "*pbm%^sk$wkh38uxv!cj^j-hmg)=xctmcmkw6ezm2yp2tx88h6"  # 加密使用的 SALT，DONT CHANGE


class AESCrypto:
    AES_CBC_KEY = SECRET_KEY[:32].encode()
    AES_CBC_IV = SECRET_KEY[:16].encode()

    @classmethod
    def encrypt(cls, data: str, mode: str = "cbc"):
        func = getattr(cls, f"{mode}_encrypt")
        return func(data)

    @classmethod
    def decrypt(cls, data: bytes, mode: str = "cbc"):
        func = getattr(cls, f"{mode}_decrypt")
        return func(data)

    @staticmethod
    def pkcs7_unpadding(padded_data: bytes):
        """解密字符串去掉 pkcs7 标准"""
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        data = unpadder.update(padded_data)

        return data + unpadder.finalize()

    @staticmethod
    def pkcs7_padding(data: Union[bytes, str]):
        """使用 pkcs7 标准化要加密的字符串"""
        if not isinstance(data, bytes):
            data = data.encode()

        padder = padding.PKCS7(algorithms.AES.block_size).padder()

        return padder.update(data) + padder.finalize()

    @classmethod
    def cbc_encrypt(cls, data: Union[bytes, str]):
        if not isinstance(data, bytes):
            data = data.encode()

        cipher = Cipher(algorithms.AES(cls.AES_CBC_KEY), modes.CBC(cls.AES_CBC_IV), backend=default_backend())
        encryptor = cipher.encryptor()

        padded_data = encryptor.update(cls.pkcs7_padding(data))

        return padded_data

    @classmethod
    def cbc_decrypt(cls, data: Union[bytes, str]):
        if not isinstance(data, bytes):
            data = data.encode()

        cipher = Cipher(algorithms.AES(cls.AES_CBC_KEY), modes.CBC(cls.AES_CBC_IV), backend=default_backend())
        decryptor = cipher.decryptor()

        uppaded_data = cls.pkcs7_unpadding(decryptor.update(data))

        return uppaded_data.decode()


def passwd_encode(value: str):
    """加密字符串"""
    v = AESCrypto.encrypt(value)
    return base64.b64encode(v).decode()


def passwd_decode(encrypted_value: str):
    """解密字符串"""
    v = base64.b64decode(encrypted_value.encode())
    return AESCrypto.decrypt(v)
