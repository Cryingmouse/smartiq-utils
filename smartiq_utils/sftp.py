import logging
from typing import Optional
from typing import Union

from smartiq_utils.parser import AbstractParser
from smartiq_utils.ssh import SSHConnectionManager

LOG = logging.getLogger()


def sftp_read_file(
    host,
    remote_file,
    config_parser: Optional[AbstractParser] = None,
    timeout: int = 10,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Union[AbstractParser, str]:
    """Retrieves configuration information from a remote file

    Args:
        host: The IP address of the remote host
        remote_file: The path to the remote file
        config_parser (AbstractParser, optional): The configuration parser object
        timeout (int, optional): The timeout period, in seconds
        username (str, optional): The username to ssh login with. Defaults to "storadmin"
        password (str, optional): The password to ssh login with.

    Returns:
        The parsed configuration information (if config_parser is not empty), or the content of the file

    """
    ssh_client = SSHConnectionManager.get_client(host, username, password, timeout)
    if not ssh_client:
        raise RuntimeError(f"Failed to connect to remote {host}")

    with ssh_client.client.open_sftp() as sftp:
        with sftp.file(remote_file, "r", -1) as file:
            if config_parser:
                config_parser.read(file.read().decode("utf-8"))
                result = config_parser
            else:
                content = file.read().decode("utf-8")
                result = content

    return result


def sftp_write_file(
    host,
    remote_file,
    file_content: Optional[str] = None,
    config_parser: Optional[AbstractParser] = None,
    timeout: int = 10,
    username: Optional[str] = None,
    password: Optional[str] = None,
):
    """Writes local content to a remote file

    Args:
        host: The IP address of the remote host
        remote_file: Remote file path
        file_content (str, optional): The content string of the file
        config_parser (AbstractParser, optional): A parse instance of config
        timeout (int, optional): timeout
        username (str, optional): The username to ssh login with. Defaults to "storadmin"
        password (str, optional): The password to ssh login with.

    Raises:
        RuntimeError: At least one file_content and config_parser,
            otherwise throw an exception

    """
    ssh_client = SSHConnectionManager.get_client(host, username, password, timeout)
    if not ssh_client:
        raise RuntimeError(f"Failed to connect to remote {host}")

    with ssh_client.client.open_sftp() as sftp:
        with sftp.file(remote_file, "w+", -1) as file:
            if file_content:
                file.write(file_content)
            elif config_parser:
                config_parser.write(file)
            else:
                raise RuntimeError()


def sftp_download_file(
    host: str,
    remote_path: str,
    local_path: str,
    timeout: int = 10,
    username: Optional[str] = None,
    password: Optional[str] = None,
):
    """Download single file from remote, folders are not supported

    Args:
        host (str): The IP address of the remote host
        remote_path (str): Remote path, for example:/home/sdn/tmp.txt
        local_path (str): Local path, for example: D:/text.txt
        timeout (int, optional): The timeout period, in seconds
        username (str, optional): The username to ssh login with.
        password (str, optional): The password to ssh login with.

    Raises:
        FileNotFoundError: if the sever_path file is not found.
        RuntimeError: An error occurs while downloading the file.
    """
    ssh_client = SSHConnectionManager.get_client(host, username, password, timeout)
    if not ssh_client:
        raise RuntimeError(f"Failed to connect to remote {host}")

    with ssh_client.client.open_sftp() as sftp:
        try:
            sftp.stat(remote_path)  # 检查文件是否存在
            sftp.get(remote_path, local_path)
        except FileNotFoundError as e:
            raise e
        except Exception as e:
            raise RuntimeError(f"Failed to download file from remote {remote_path} to {local_path}, error: {e}") from e
