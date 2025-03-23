import base64
import unittest

from smartiq_utils.crypto import AESCrypto
from smartiq_utils.crypto import passwd_decode
from smartiq_utils.crypto import passwd_encode
from smartiq_utils.crypto import SECRET_KEY


class TestAESCrypto(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_strings = [
            "hello world",
            "你好，世界！",
            "!@#$%^&*()",
            "",
            "a" * 15,  # 测试非对齐数据
            "a" * 16,  # 测试对齐数据
            "a" * 17,  # 测试跨块数据
        ]

    def test_encrypt_decrypt_consistency(self):
        """测试加密解密一致性"""
        for data in self.test_strings:
            with self.subTest(data=data):
                encrypted = AESCrypto.encrypt(data)
                decrypted = AESCrypto.decrypt(encrypted)
                self.assertEqual(data, decrypted)

    def test_passwd_encode_decode(self):
        """测试Base64编解码流程"""
        for data in self.test_strings:
            with self.subTest(data=data):
                encoded = passwd_encode(data)
                decoded = passwd_decode(encoded)
                self.assertEqual(data, decoded)

    def test_key_iv_configuration(self):
        """测试密钥和IV配置"""
        self.assertEqual(len(AESCrypto.AES_CBC_KEY), 32, "密钥长度应为32字节")
        self.assertEqual(len(AESCrypto.AES_CBC_IV), 16, "IV长度应为16字节")
        self.assertEqual(AESCrypto.AES_CBC_KEY, SECRET_KEY[:32].encode(), "密钥生成错误")
        self.assertEqual(AESCrypto.AES_CBC_IV, SECRET_KEY[:16].encode(), "IV生成错误")

    def test_invalid_base64_input(self):
        """测试无效Base64输入"""
        with self.assertRaises(base64.binascii.Error):
            passwd_decode("invalid_base64~~")

    def test_corrupted_ciphertext(self):
        """测试损坏的密文"""
        original = "important message"
        encrypted = passwd_encode(original)

        # 损坏Base64字符串
        corrupted = encrypted[:-2] + "=="  # 无效修改
        with self.assertRaises(Exception):
            passwd_decode(corrupted)

        # 直接损坏二进制数据
        encrypted_bytes = base64.b64decode(encrypted)
        corrupted_bytes = encrypted_bytes[:-5] + b"xxxxx"  # 随机修改
        corrupted = base64.b64encode(corrupted_bytes).decode()
        with self.assertRaises(ValueError):
            passwd_decode(corrupted)

    def test_padding_logic(self):
        """测试PKCS7填充逻辑"""
        test_cases = [
            (b"", 16),  # 空数据填充
            (b"a" * 15, 1),  # 需要1字节填充
            (b"a" * 16, 16),  # 完整块填充
            (b"a" * 17, 15),  # 需要15字节填充
        ]

        for data, pad_size in test_cases:
            with self.subTest(data=data):
                padded = AESCrypto.pkcs7_padding(data)
                self.assertEqual(len(padded) % 16, 0, "填充后长度应为16的倍数")

                unpadded = AESCrypto.pkcs7_unpadding(padded)
                self.assertEqual(unpadded, data, "解填充后数据不一致")

                # 验证填充字节值是否正确
                if data:
                    self.assertEqual(padded[-1], pad_size, "填充字节值不正确")

    def test_invalid_padding(self):
        """测试无效填充数据"""
        # 正确填充示例
        valid = AESCrypto.pkcs7_padding(b"test")
        # 修改最后一个字节为无效值
        invalid = valid[:-1] + bytes([valid[-1] + 1])
        with self.assertRaises(ValueError):
            AESCrypto.pkcs7_unpadding(invalid)

    def test_cbc_mode_requirements(self):
        """测试CBC模式要求"""
        # 测试非16字节倍数数据加密（应自动填充）
        data = "abc"
        encrypted = AESCrypto.encrypt(data)
        self.assertEqual(len(encrypted) % 16, 0, "CBC加密输出应为16字节倍数")

        # 测试解密时传入非法长度数据
        with self.assertRaises(ValueError):
            AESCrypto.decrypt(b"short_data")

    def test_encoding_handling(self):
        """测试不同类型输入处理"""
        # bytes类型输入
        encrypted_bytes = AESCrypto.encrypt(b"byte data")
        decrypted_bytes = AESCrypto.decrypt(encrypted_bytes)
        self.assertEqual(decrypted_bytes, "byte data")

        # 非ASCII字符处理
        data = "中文测试"
        encrypted = AESCrypto.encrypt(data)
        decrypted = AESCrypto.decrypt(encrypted)
        self.assertEqual(decrypted, data)
