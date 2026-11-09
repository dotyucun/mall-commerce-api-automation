"""Collect blocking Docker/OS/database probes outside Locust's event loop."""

import argparse
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import psutil
from pymysql import MySQLError

from mall_api_test.common.db import MallDb
from mall_api_test.config.settings import SETTINGS
from mall_api_test.repositories.performance_repository import PerformanceRepository


def collect(pid: int, output: Path, interval: float) -> None:
    process = psutil.Process(pid)
    samples = []
    errors = []
    database = None
    try:
        container_ids = subprocess.check_output(
            [
                "docker",
                "ps",
                "-q",
                "--filter",
                "label=com.docker.compose.project=mall-commerce-api-test",
            ],
            text=True,
            timeout=20,
        ).splitlines()
        if not container_ids:
            raise RuntimeError("No dedicated containers")
        while not (output / "monitor-stop").exists():
            marker = output / "window.json"
            if marker.exists():
                try:
                    window = json.loads(marker.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    time.sleep(0.05)
                    continue
                break
            time.sleep(0.1)
        else:
            return
        database = MallDb(SETTINGS.database)
        repository = PerformanceRepository(database)
        process.cpu_percent()
        while time.monotonic() < window["deadline"]:
            payload = subprocess.check_output(
                ["docker", "stats", "--no-stream", "--format", "{{json .}}", *container_ids],
                text=True,
                timeout=20,
            )
            containers = [json.loads(line) for line in payload.splitlines() if line]
            if len(containers) != len(container_ids):
                raise RuntimeError("Incomplete container samples")
            if time.monotonic() >= window["deadline"]:
                break
            samples.append(
                {
                    "utc": datetime.now(UTC).isoformat(),
                    "elapsed_seconds": time.monotonic() - window["start_monotonic"],
                    "generator_cpu_percent": process.cpu_percent(),
                    "generator_rss_mb": process.memory_info().rss / 1024**2,
                    "host_memory_percent": psutil.virtual_memory().percent,
                    "containers": containers,
                    "database": repository.snapshot(),
                }
            )
            if (output / "monitor-stop").exists():
                break
            time.sleep(min(interval, max(0, window["deadline"] - time.monotonic())))
    except (
        OSError,
        ValueError,
        RuntimeError,
        MySQLError,
        psutil.Error,
        subprocess.SubprocessError,
    ) as error:
        errors.append(type(error).__name__)
    finally:
        if database is not None:
            database.connection.close()
        (output / "resources.json").write_text(
            json.dumps(samples, indent=2) + "\n", encoding="utf-8"
        )
        (output / "resource-errors.json").write_text(json.dumps(errors), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--interval", type=float, required=True)
    arguments = parser.parse_args()
    collect(arguments.pid, arguments.output, arguments.interval)
