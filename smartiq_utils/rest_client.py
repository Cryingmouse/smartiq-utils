from typing import Any
from typing import Dict
from typing import Literal
from typing import Optional
from urllib.parse import urljoin

import requests


class ConnectionConfig:
    """连接配置管理类，负责URL构造和参数验证"""

    def __init__(
        self,
        http: Literal["http", "https"],
        host: str,
        port: int,
        base_path: str = "/api/v1",
        login_path: Optional[str] = "/login",
        verify_ssl: bool = True,
    ):
        self.http = http
        self.host = host
        self.port = port
        self.base_path = base_path.strip("/")
        self.login_path = login_path.lstrip("/") if login_path else None
        self.verify_ssl = verify_ssl
        self._validate()
        self._base_url = self._build_base_url()

    def _validate(self) -> None:
        """参数验证"""
        if self.http not in ("http", "https"):
            raise ValueError("协议必须为 http 或 https")

        if not 1 <= self.port <= 65535:
            raise ValueError("端口号必须介于1-65535")

    def _build_base_url(self) -> str:
        """构建基础URL"""
        port_suffix = f":{self.port}" if self.port is not None else ""
        base = f"{self.http}://{self.host}{port_suffix}"

        return f"{base}/{self.base_path}" if self.base_path else base

    @property
    def login_url(self) -> Optional[str]:
        """获取完整登录URL"""
        if self.login_path:
            return urljoin(f"{self._base_url}/", self.login_path)

        return None


class SmartRestClient:
    """
    智能REST客户端，支持以下模式：
    1. 无密码模式：仅使用Cookie
    2. 密码模式：支持登录API和Basic认证
    """

    def __init__(self, config: ConnectionConfig, username: Optional[str] = None, password: Optional[str] = None):
        self.config = config
        self.username = username
        self.password = password

        # 会话状态
        self.cookies: Dict[str, str] = {}
        self._retry_count = 0
        self.max_retries = 2

        # 凭证验证
        self._validate_credentials()

    def _validate_credentials(self) -> None:
        """验证凭证配置有效性"""
        has_creds = self.username is not None or self.password is not None
        if has_creds and not (self.username and self.password):
            raise ValueError("用户名和密码必须同时提供")

        if self.config.login_path and not has_creds:
            raise ValueError("登录接口需要用户名和密码")

    @property
    def has_credentials(self) -> bool:
        """是否包含有效凭证"""
        return self.username is not None and self.password is not None

    def _send_request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        """发送请求的核心方法"""
        url = self._build_url(path)

        try:
            response = requests.request(
                method=method, url=url, cookies=self.cookies, verify=self.config.verify_ssl, **kwargs
            )
        except requests.RequestException as e:
            raise ConnectionError(f"请求失败: {str(e)}") from e

        self._update_cookies(response)

        if response.status_code == 401:
            return self._handle_unauthorized(response, method, path, **kwargs)

        self._retry_count = 0
        return response

    def _handle_unauthorized(
        self, response: requests.Response, method: str, path: str, **kwargs: Any
    ) -> requests.Response:
        """处理401未授权错误"""
        if self._retry_count >= self.max_retries:
            response.raise_for_status()

        self._retry_count += 1

        # 有凭证时的恢复流程
        if self.has_credentials:
            success = False

            # 优先尝试登录接口
            if self.config.login_url:
                success = self._attempt_login_api()
                if success:
                    return self._retry_request(method, path, **kwargs)
            else:
                self._attempt_basic_auth()

        response.raise_for_status()

    def _attempt_login_api(self) -> bool:
        """尝试通过登录接口认证"""
        try:
            response = requests.post(
                self.config.login_url,  # type: ignore
                json={"username": self.username, "password": self.password},
                verify=self.config.verify_ssl,
            )
            if response.ok:
                self.cookies.update(response.cookies.get_dict())
                return True
        except Exception as e:
            print(f"登录接口调用失败: {str(e)}")
        return False

    def _attempt_basic_auth(self) -> bool:
        """尝试Basic认证"""
        try:
            response = requests.get(
                self.config._base_url, auth=(self.username, self.password), verify=self.config.verify_ssl
            )
            if response.ok:
                self.cookies.update(response.cookies.get_dict())
                return True
        except Exception as e:
            print(f"Basic认证失败: {str(e)}")
        return False

    def _build_url(self, path: str) -> str:
        """构建完整请求URL"""
        return urljoin(f"{self.config._base_url}/", path.lstrip("/"))

    def _update_cookies(self, response: requests.Response) -> None:
        """更新Cookie存储"""
        self.cookies.update(response.cookies.get_dict())

    def _retry_request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        """重试原始请求"""
        return self._send_request(method, path, **kwargs)

    # 公共API方法
    def get(self, path: str, **kwargs) -> requests.Response:
        return self._send_request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self._send_request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self._send_request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self._send_request("DELETE", path, **kwargs)


# 使用示例
if __name__ == "__main__":
    # 场景1：无密码模式（仅使用Cookie）
    public_config = ConnectionConfig(http="https", host="public.api.com", port=443, base_path="v1")
    public_client = SmartRestClient(public_config)

    # 场景2：密码模式（同时支持登录接口和Basic认证）
    private_config = ConnectionConfig(
        http="https", host="private.api.com", port=443, base_path="secure", login_path="auth/login"
    )
    private_client = SmartRestClient(config=private_config, username="admin", password="secret")

    # 场景3：仅Basic认证模式
    basic_config = ConnectionConfig(http="https", host="basic.api.com", port=443, base_path="api")
    basic_client = SmartRestClient(config=basic_config, username="user", password="pass")
