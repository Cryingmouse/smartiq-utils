import logging
import subprocess
import unittest
from unittest.mock import patch

import tenacity

from smartiq_utils.executor import execute_local_command
from smartiq_utils.executor import execute_local_command_with_retry
from smartiq_utils.executor import SystemCallError
from smartiq_utils.executor import SystemCallTimeoutError

logging.basicConfig(level=logging.DEBUG)


class TestExecuteLocalCommand(unittest.TestCase):
    @patch("subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args="echo hello",
            returncode=0,
            stdout="hello\n",
        )
        result = execute_local_command("echo hello")
        self.assertEqual(result, "hello")
        mock_run.assert_called_once_with(
            "echo hello",
            shell=True,
            timeout=10,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_failure_raise_exception(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd="invalid command",
            output="error message",
        )
        with self.assertRaises(SystemCallError) as cm:
            execute_local_command("invalid command", raise_exception=True)
        self.assertEqual(cm.exception.exit_code, 1)
        self.assertEqual(cm.exception.output, "error message")

    @patch("subprocess.run")
    def test_timeout_raise_exception(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep 2", timeout=1, output="timeout occurred")
        with self.assertRaises(SystemCallTimeoutError) as cm:
            execute_local_command("sleep 2", timeout=1, raise_exception=True)
        self.assertEqual(cm.exception.output, "timeout occurred")

    def test_empty_command(self):
        with self.assertRaises(ValueError):
            execute_local_command("")

    def test_invalid_timeout(self):
        with self.assertRaises(ValueError):
            execute_local_command("echo hello", timeout=0)

    @patch("subprocess.run")
    def test_output_only_false(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args="echo hello",
            returncode=0,
            stdout="hello\n",
        )
        result = execute_local_command("echo hello", output_only=False)
        self.assertEqual(result, (0, "hello"))

    @patch("subprocess.run")
    def test_output_stripping(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args="echo hello",
            returncode=0,
            stdout="hello\n\n",
        )
        result = execute_local_command("echo hello")
        self.assertEqual(result, "hello")

    @patch("subprocess.run")
    def test_no_exception_with_raise_false(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd="invalid command",
            output="error",
        )
        result = execute_local_command("invalid command", raise_exception=False, output_only=False)
        self.assertEqual(result, (1, "error"))


class TestExecuteLocalCommandWithRetry(unittest.TestCase):
    @patch("smartiq_utils.executor.execute_local_command")
    def test_retry_success_after_failures(self, mock_execute):
        mock_execute.side_effect = [
            SystemCallError(1, "error1"),
            SystemCallError(1, "error2"),
            "success",
        ]
        result = execute_local_command_with_retry("command", retries=3)
        self.assertEqual(result, "success")
        self.assertEqual(mock_execute.call_count, 3)

    @patch("smartiq_utils.executor.execute_local_command")
    def test_retry_all_failures(self, mock_execute):
        mock_execute.side_effect = SystemCallError(1, "error")
        with self.assertRaises(tenacity.RetryError):
            execute_local_command_with_retry("command", retries=3)
        self.assertEqual(mock_execute.call_count, 3)

    @patch("smartiq_utils.executor.execute_local_command")
    def test_no_retry_on_other_exceptions(self, mock_execute):
        mock_execute.side_effect = ValueError("unexpected error")
        with self.assertRaises(ValueError):
            execute_local_command_with_retry("command", retries=3)
        mock_execute.assert_called_once()

    @patch("smartiq_utils.executor.execute_local_command")
    def test_retry_count(self, mock_execute):
        mock_execute.side_effect = SystemCallError(1, "error")
        try:
            execute_local_command_with_retry("command", retries=5)
        except tenacity.RetryError:
            pass
        self.assertEqual(mock_execute.call_count, 5)

    @patch("smartiq_utils.executor.execute_local_command")
    def test_retry_timeout_errors(self, mock_execute):
        mock_execute.side_effect = [
            SystemCallTimeoutError("timeout1"),
            SystemCallTimeoutError("timeout2"),
            "success",
        ]
        result = execute_local_command_with_retry("command", retries=3)
        self.assertEqual(result, "success")
        self.assertEqual(mock_execute.call_count, 3)
