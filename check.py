import re
import subprocess
import sys
from pathlib import Path
from typing import List

import click
from rich.console import Console
from rich.style import Style

console = Console()
error_style = Style(color="red", bold=True)
warning_style = Style(color="yellow")
success_style = Style(color="green", bold=True)


@click.command()
@click.option("--skip-pytest", is_flag=True, help="Skip pytest tests")
@click.option("--skip-pylint", is_flag=True, help="Skip pylint checks")
@click.option("--skip-mypy", is_flag=True, help="Skip mypy checks")
def main(skip_pytest: bool, skip_pylint: bool, skip_mypy: bool):
    """Run code quality checks with configurable parameters"""
    exit_code = 0
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)

    # 执行顺序：pytest -> pylint -> mypy
    if not skip_pytest:
        exit_code |= run_pytest(report_dir)

    if not skip_pylint:
        exit_code |= run_pylint(report_dir)

    if not skip_mypy:
        exit_code |= run_mypy(report_dir)

    # 最终结果输出
    console.print("\n[bold]Check results summary:[/bold]")
    status_style = success_style if exit_code == 0 else error_style
    console.print(f"Final exit code: [bold]{exit_code}[/]", style=status_style)

    sys.exit(exit_code)


def run_pytest(report_dir: Path) -> int:
    """运行pytest测试"""
    console.print("\n[bold cyan]🚀 Running pytest...[/bold cyan]")

    base_cmd = ["poetry", "run", "pytest", "tests"]

    report_file = report_dir / "pytest_report.txt"
    full_cmd = base_cmd + ["--cov=smartiq_utils", "--cov-report=xml", "--cov-report=html"]

    console.print(f"Command: [yellow]{' '.join(full_cmd)}[/]")
    return execute_command(full_cmd, report_file)


def run_pylint(report_dir: Path) -> int:
    """运行pylint检查"""
    console.print("\n[bold cyan]🔍 Running pylint...[/bold cyan]")

    report_file = report_dir / "pylint_report.txt"
    base_cmd = ["poetry", "run", "pylint", "smartiq_utils"]

    full_cmd = base_cmd + ["--output-format=text"]

    console.print(f"Command: [yellow]{' '.join(full_cmd)}[/]")
    return execute_command(full_cmd, report_file)


def run_mypy(report_dir: Path) -> int:
    """运行mypy类型检查"""
    console.print("\n[bold cyan]🧠 Running mypy...[/bold cyan]")

    report_file = report_dir / "mypy_report.txt"
    base_cmd = ["poetry", "run", "mypy", "smartiq_utils"]

    full_cmd = base_cmd + ["--show-error-codes"]

    console.print(f"Command: [yellow]{' '.join(full_cmd)}[/]")
    return execute_command(full_cmd, report_file)


def execute_command(cmd: List[str], report_file: Path) -> int:
    """执行命令并处理输出"""
    try:
        with report_file.open("w") as f:
            process = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)

        # 输出简要结果
        with report_file.open() as f:
            lines = f.readlines()

            mypy_error_count = 0

            # This is for pylint
            pattern = r"^[^:]+:\d+:\d+:\s[A-Z]\d+:\s.*"
            pylint_error_count = sum(1 for line in lines if re.match(pattern, line))
            if pylint_error_count == 0:
                # This is for mypy
                mypy_error_count = sum(1 for line in lines if "error" in line.lower())

            error_count = pylint_error_count + mypy_error_count
            warning_count = sum(1 for line in lines if "warning" in line.lower())

        console.print(
            f"Results: [red]{error_count} errors[/], [yellow]{warning_count} warnings[/] in {len(lines)} lines"
        )
        console.print(f"Full report: [blue]{report_file}[/]")

        return process.returncode
    except Exception as e:
        console.print(f"Command failed: {str(e)}", style=error_style)
        return 1


if __name__ == "__main__":
    main()
