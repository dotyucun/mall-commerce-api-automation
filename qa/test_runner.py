import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHELLS = [path for name in ("pwsh", "powershell") if (path := shutil.which(name))]


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize(
    "action,failed_tool",
    [("test", "python"), ("slow", "python"), ("report", "allure"), ("performance", "locust")],
)
def test_native_command_failure_is_not_reported_as_success(tmp_path, action, failed_tool, shell):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(ROOT / "scripts/mall-test.ps1", scripts)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    if os.name == "nt":
        (bin_dir / f"{failed_tool}.cmd").write_text("@exit /b 17\n", encoding="ascii")
    else:
        stub = bin_dir / failed_tool
        stub.write_text("#!/bin/sh\nexit 17\n", encoding="ascii")
        stub.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]
    for name in (
        "MALL_ADMIN_PASSWORD",
        "MALL_TEST_USER_A_PASSWORD",
        "MALL_TEST_USER_B_PASSWORD",
        "MALL_MYSQL_PASSWORD",
        "MALL_RABBITMQ_PASSWORD",
    ):
        env[name] = "runner-test-placeholder"
    result = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(scripts / "mall-test.ps1"),
            action,
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0, result.stdout + result.stderr
