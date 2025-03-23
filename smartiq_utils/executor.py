import logging
import subprocess
from typing import Any
from typing import Optional

import tenacity
from paramiko import SSHException  # type: ignore[import-untyped]
from tenacity import retry_if_exception_type
from tenacity import retry_if_result

from smartiq_utils.decorator import measure_exec_time
from smartiq_utils.ssh import SSHConnectionManager

LOG = logging.getLogger()


class SystemCallError(Exception):
    """Exception raised when a system call fails with a non-zero exit code."""

    def __init__(self, exit_code: int, stdout: str, stderr: str):
        super().__init__(f"Command failed with exit code {exit_code}")
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


class SystemCallTimeoutError(Exception):
    """Exception raised when a system call times out."""

    def __init__(self, stdout: str):
        super().__init__("Command timed out")
        self.stdout = stdout


@measure_exec_time
def execute_local_command(
    command: str,
    raise_exception: bool = True,
    output_only: bool = True,
    timeout: int = 10,
    log_level: int = logging.INFO,
    command_for_logging: Optional[str] = None,
) -> Any:
    """Execute a local command and capture merged stdout/stderr output.

    Args:
        command: The shell command to execute
        raise_exception: Raise error on non-zero exit code or timeout
        output_only: Return only merged output when True, else (exit_code, output)
        timeout: Maximum execution time in seconds (None for no timeout)
        log_level: Temporary log level during execution
        command_for_logging: Optional sanitized command string for logging

    Returns:
        Merged output or tuple with exit code and output

    Raises:
        SystemCallError: On non-zero exit code when raise_exception=True
        SystemCallTimeoutError: On timeout when raise_exception=True
        ValueError: If command is empty or timeout is invalid
    """
    # Parameter validation
    if not command.strip():
        raise ValueError("Command cannot be empty")

    if timeout is not None and timeout <= 0:
        raise ValueError("Timeout must be a positive integer or None")

    original_log_level = LOG.getEffectiveLevel()
    if log_level < original_log_level:
        LOG.setLevel(log_level)

    try:
        logged_command = command_for_logging or command
        LOG.debug(f"Executing command: '{logged_command}' (timeout={timeout})")

        try:
            completed = subprocess.run(
                command,
                shell=True,
                timeout=timeout,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=True,
            )
            exit_code = completed.returncode
            data = completed.stdout
            LOG.debug(f"Command succeeded [code={exit_code}]: {data}")

        except subprocess.CalledProcessError as ex:
            exit_code = ex.returncode
            data = ex.stdout
            error = ex.stderr
            LOG.debug(f"Command failed [code={exit_code}]: stdout={data}, stderr={error}")
            if raise_exception:
                raise SystemCallError(exit_code, data, error) from ex

        except subprocess.TimeoutExpired as ex:
            exit_code = -999  # Special value indicating timeout
            data = str(ex.stdout) or ""
            LOG.debug(f"Command timeout: {data}")
            if raise_exception:
                raise SystemCallTimeoutError(data) from ex

        # Clean trailing newline while preserving empty strings
        if data:
            data = data.rstrip("\n")

        return data if output_only else (exit_code, data)

    finally:
        LOG.setLevel(original_log_level)


def execute_local_command_with_retry(
    command: str,
    raise_exception: bool = True,
    output_only: bool = True,
    timeout: int = 10,
    log_level: int = logging.INFO,
    command_for_logging: Optional[str] = None,
    wait_time: int = 1,
    retries: int = 3,
    retry=tenacity.retry_if_exception_type,
    retry_param=(SystemCallError, SystemCallTimeoutError),
) -> Any:
    """Execute a local command with retry logic.

    This function attempts to execute the given command multiple times if specific exceptions occur.
    It uses the `tenacity` library to implement the retry mechanism.

    Args:
        command (str): The shell command to execute.
        raise_exception (bool, optional): Raise an error on non-zero exit code or timeout. Defaults to True.
        output_only (bool, optional): Return only the merged output when True, else return a tuple of
            (exit_code, output). Defaults to True.
        timeout (int, optional): Maximum execution time in seconds. Defaults to 10.
        log_level (int, optional): Temporary log level during execution. Defaults to logging.INFO.
        command_for_logging (str, optional): Optional sanitized command string for logging. Defaults to None.
        wait_time (int): The time to wait between retry attempts in seconds. Defaults to 1.
        retries (int): The number of retry attempts. Defaults to 3.
        retry (retry_base, optional): The retry condition function. Defaults to tenacity.retry_if_exception_type.
        retry_param (tuple, optional): The exception types that trigger a retry.
            Defaults to (SystemCallError, SystemCallTimeoutError).

    Returns:
        Union[Optional[str], Tuple[int, str]]: Merged output or a tuple with exit code and output.

    Raises:
        tenacity.RetryError: If all retry attempts fail.
    """

    @tenacity.retry(
        wait=tenacity.wait_fixed(wait_time),
        stop=tenacity.stop_after_attempt(retries),
        retry=retry(retry_param),
        before_sleep=tenacity.before_sleep_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def wrapped_execute_local_command() -> Any:
        return execute_local_command(
            command=command,
            raise_exception=raise_exception,
            output_only=output_only,
            timeout=timeout,
            log_level=log_level,
            command_for_logging=command_for_logging,
        )

    return wrapped_execute_local_command()


def execute_remote_command_with_retry(
    host: str,
    cmd: str,
    timeout: int = 180,
    username: Optional[str] = None,
    password: Optional[str] = None,
    log_level: int = logging.DEBUG,
    retries: int = 3,
    wait_time: int = 1,
):
    """Execute the command via Paramiko SSH client.

    Args:
        host (str): The host to execute the command.
        cmd (str): The command to be executed.
        timeout (int, optional): Timeout for ssh client.
        username (str, optional): The username to ssh login with.
        password (str, optional): The password to ssh login with.
        retries (int, optional): Retry times
        wait_time (int, optional): Wait time between retry, unit sec
        log_level (int, optional): Logging level. Defaults to logging.DEBUG.

    Returns:
        a 3-tuple (exit_code, output, error)

    Raises:
        RetryError:
        SSHException:

    """

    @tenacity.retry(
        wait=tenacity.wait_fixed(wait_time),
        reraise=True,
        stop=tenacity.stop_after_attempt(retries),
        retry=retry_if_result(lambda v: v[0] != 0) | retry_if_exception_type(SSHException),
        before_sleep=tenacity.before_sleep_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def _wrapped_execute_remote_cmd(
        w_host: str,
        w_cmd: str,
        w_timeout: int = 180,
        w_username: Optional[str] = None,
        w_password: Optional[str] = None,
        w_log_level: int = logging.DEBUG,
    ):
        return execute_remote_command(
            host=w_host,
            cmd=w_cmd,
            output_only=False,
            timeout=w_timeout,
            username=w_username,
            password=w_password,
            raise_exception=False,
            log_level=w_log_level,
        )

    return _wrapped_execute_remote_cmd(
        w_host=host, w_cmd=cmd, w_timeout=timeout, w_username=username, w_password=password, w_log_level=log_level
    )


def execute_remote_command(
    host: str,
    cmd: str,
    output_only: bool = False,
    timeout: int = 180,
    username: Optional[str] = None,
    password: Optional[str] = None,
    raise_exception: bool = False,
    log_level: int = logging.DEBUG,
):
    """Execute the command via Paramiko SSH client

    Args:
        host (str): The host to execute the command.
        cmd (str): The command to be executed
        output_only (bool, optional): It will return output only.
        timeout (int, optional): Timeout for ssh client
        username (str, optional): The username to ssh login with.
        password (str, optional): The password to ssh login with.
        raise_exception (bool, optional): Whether to raise exceptions immediately or collect them.
        log_level (int, optional): Logging level. Defaults to logging.DEBUG.

    Returns:
        a 3-tuple (exit_code, output, error)

    Raises:
        SSHException: If there is an error in the SSH connection.
        NoValidConnectionsError: If no valid connections can be made to the host.
        SystemCallTimeoutError:If the command returns a non-zero exit code and raise_exception is set to True.
    """
    original_log_level = LOG.getEffectiveLevel()
    if log_level < original_log_level:
        LOG.setLevel(log_level)

    try:
        ssh_client = SSHConnectionManager.get_client(host, username, password, timeout)
        if not ssh_client:
            raise RuntimeError(f"Failed to connect to remote {host}")

        LOG.debug(f"Running the command '{cmd}' on {host}")
        with ssh_client.get_channel(timeout=timeout) as channel:
            channel.exec_command(f"timeout -s 15 {timeout} {cmd}")

            with channel.makefile("r") as stdout_file, channel.makefile_stderr("r") as stderr_file:
                out = stdout_file.read().decode().strip()
                err = stderr_file.read().decode()

            exit_code = channel.recv_exit_status()

        LOG.debug(f"The execution result of '{cmd}' on {host}: " f"exit_code={exit_code}, stdout={out}, stderr={err}")
        if exit_code != 0 and raise_exception:
            raise SystemCallError(exit_code, out, err)

        return out if output_only else (exit_code, out, err)
    finally:
        LOG.setLevel(original_log_level)
