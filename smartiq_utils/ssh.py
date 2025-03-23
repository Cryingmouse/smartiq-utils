import logging
import threading
from contextlib import contextmanager
from typing import Dict
from typing import Optional

import paramiko  # type: ignore[import-untyped]

LOG = logging.getLogger()

GET_CLIENT_LOCK = threading.Lock()


class SSHClient:
    def __init__(
        self,
        host: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 10,
        max_channels: int = 5,
    ):
        self.host = host
        self.username = username
        self.password = password
        self.timeout = timeout

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # follow /etc/ssh/sshd_config, must be less than `MaxSessions`.
        self._semaphore = threading.Semaphore(value=max_channels)

    def connect(self):
        try:
            if self.username and self.password:
                self.client.connect(
                    hostname=self.host, username=self.username, password=self.password, timeout=self.timeout
                )
            else:
                self.client.connect(hostname=self.host, timeout=self.timeout)
            LOG.info(f"Connected to {self.host} with updated credentials.")
        except Exception as e:
            LOG.error(f"Failed to connect to {self.host}, error: {e}")
            raise e

    @contextmanager
    def get_channel(self, timeout: int = 180):
        transport = self.client.get_transport()
        if transport is None or not transport.is_active():
            raise ValueError("SSH connection transport not active")

        self._semaphore.acquire(timeout=timeout)

        channel = transport.open_session(timeout=timeout)

        try:
            yield channel
        finally:
            channel.close()
            self._semaphore.release()


class SSHConnectionManager:
    """Manage multiple SSH connections to ensure that each node has only one SSHClient instance"""

    connections: Dict[str, SSHClient] = {}

    @classmethod
    def get_client(
        cls, host: str, username: Optional[str] = None, password: Optional[str] = None, timeout: int = 10
    ) -> Optional[SSHClient]:
        """Get an SSHClient instance"""
        with GET_CLIENT_LOCK:
            if host not in cls.connections:
                client = SSHClient(host=host, username=username, password=password, timeout=timeout)
                try:
                    client.connect()
                    cls.connections[host] = client
                    LOG.info(f"Connected to {host} with updated credentials.")
                except Exception as e:
                    LOG.error(f"Failed to connect to {host}, error: {e}")
                    raise e

            return cls.connections.get(host)
