"""Run isolated Locust stages; warmup/login never enter steady-window statistics."""

import argparse
import csv
import hashlib
import html
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from mall_api_test.common.performance_steps import (
    assess_step,
    compare_steps,
    load_step_settings,
    summarize_entry,
)
from mall_api_test.common.performance_window import RequestWindow
from mall_api_test.config.settings import SETTINGS

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name("steps.yaml")


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def command(arguments: list[str], timeout: float = 20) -> str:
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=timeout, check=True)
    return result.stdout.strip()


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_stage(args, settings) -> dict:
    # Only worker processes import Locust, which patches networking before HTTP imports.
    import gevent
    from locust import constant
    from locust.env import Environment
    from locust.event import Events
    from locust.stats import RequestStats

    from performance.locustfile import MallPortalUser

    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    container_ids = command(
        [
            "docker",
            "ps",
            "-q",
            "--filter",
            "label=com.docker.compose.project=mall-commerce-api-test",
        ]
    ).splitlines()
    if not container_ids:
        raise RuntimeError("The dedicated Compose environment is not running")
    ready = set()
    ledger = RequestWindow()

    class StageUser(MallPortalUser):
        host = settings.portal_base_url
        wait_time = constant(settings.wait_seconds)

        def on_start(self):
            super().on_start()
            original_request = self.client.request

            def tracked_request(*args, **kwargs):
                context = dict(kwargs.pop("context", {}))
                context["step_window_token"] = ledger.start_request(time.monotonic())
                return original_request(*args, context=context, **kwargs)

            self.client.request = tracked_request
            ready.add(id(self))

    environment = Environment(user_classes=[StageUser], events=Events(), stop_timeout=15)
    runner = environment.create_local_runner()
    window_stats = RequestStats(use_response_times_cache=False)
    tail_stats = RequestStats(use_response_times_cache=False)
    window = {"start_wall": None, "deadline": None}
    history = []

    def record(request_type, name, response_time, response_length, exception=None, **kwargs):
        token = kwargs.get("context", {}).get("step_window_token")
        category = ledger.finish_request(token, time.monotonic())
        if category is None:
            return
        target = window_stats if category == "steady" else tail_stats
        target.log_request(request_type, name, response_time, response_length)
        if exception is not None:
            target.log_error(request_type, name, exception)

    environment.events.request.add_listener(record)

    def sample_history():
        while True:
            if window["start_wall"] is not None and time.monotonic() < window["deadline"]:
                history.append(
                    {
                        "elapsed_seconds": time.monotonic() - started_monotonic,
                        "requests": window_stats.total.num_requests,
                        "failures": window_stats.total.num_failures,
                        "users": runner.user_count,
                        "p95_ms_cumulative": window_stats.total.get_response_time_percentile(0.95),
                    }
                )
            gevent.sleep(1)

    sampler = gevent.spawn(sample_history)
    monitor = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "performance.resource_monitor",
            "--pid",
            str(os.getpid()),
            "--output",
            str(output),
            "--interval",
            str(settings.sample_interval_seconds),
        ],
        cwd=ROOT,
    )
    try:
        runner.start(args.user_count, spawn_rate=settings.spawn_rate)
        ready_deadline = time.monotonic() + settings.ready_timeout_seconds
        while len(ready) < args.user_count:
            if time.monotonic() >= ready_deadline or runner.exceptions:
                raise RuntimeError(f"Users failed to log in: {len(ready)}/{args.user_count}")
            gevent.sleep(0.1)
        gevent.sleep(settings.warmup_seconds)
        ready_users = runner.user_count
        started_monotonic = time.monotonic()
        ledger.begin(started_monotonic, settings.measure_seconds)
        window["start_wall"] = time.time()
        window["deadline"] = started_monotonic + settings.measure_seconds
        write_json(
            output / "window.json",
            {
                "start_monotonic": started_monotonic,
                "deadline": window["deadline"],
            },
        )
        gevent.sleep(settings.measure_seconds)
        ended_wall = window["start_wall"] + settings.measure_seconds
        runner.stop()
    finally:
        sampler.kill(block=True)
        (output / "monitor-stop").touch()
        try:
            monitor.wait(timeout=settings.sample_interval_seconds + 25)
        except subprocess.TimeoutExpired:
            monitor.terminate()
            monitor.wait(timeout=10)
        if runner.user_count:
            runner.stop()

    samples = json.loads((output / "resources.json").read_text(encoding="utf-8"))
    resource_errors = json.loads((output / "resource-errors.json").read_text(encoding="utf-8"))

    endpoints = [
        summarize_entry(item, settings.measure_seconds)
        for _, item in sorted(window_stats.entries.items())
    ]
    result = {
        "profile": args.profile,
        "repeat": args.repeat,
        "users": args.user_count,
        "ready_users": ready_users,
        "wait_seconds": settings.wait_seconds,
        "start_utc": datetime.fromtimestamp(window["start_wall"], UTC).isoformat(),
        "end_utc": datetime.fromtimestamp(ended_wall, UTC).isoformat(),
        "measured_seconds": settings.measure_seconds,
        "warmup_seconds": settings.warmup_seconds,
        "total": summarize_entry(window_stats.total, settings.measure_seconds),
        "endpoints": endpoints,
        "tail_requests": tail_stats.total.num_requests,
        "tail_failures": tail_stats.total.num_failures,
        "started_requests": ledger.started_requests,
        "incomplete_requests": len(ledger.pending),
        "user_exceptions": len(runner.exceptions),
        "resource_samples": len(samples),
        "resource_errors": resource_errors,
        "generator_cpu_median_percent": statistics.median(
            [sample["generator_cpu_percent"] for sample in samples]
        )
        if samples
        else 0,
        "failures": [error.serialize() for error in window_stats.errors.values()],
    }
    result["stop_reasons"] = assess_step(result, settings)
    if result["tail_failures"]:
        result["stop_reasons"].append("tail_request_failure")
    write_json(output / "summary.json", result)
    write_json(output / "resources.json", samples)
    write_csv(output / "endpoints.csv", [result["total"], *endpoints])
    write_csv(output / "history.csv", history)
    write_stage_html(output / "report.html", result)
    runner.quit()
    return result


def write_stage_html(path: Path, result: dict) -> None:
    rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row.values()) + "</tr>"
        for row in [result["total"], *result["endpoints"]]
    )
    headers = "".join(f"<th>{name}</th>" for name in result["total"])
    path.write_text(
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        "<title>Locust 阶段实测</title><style>body{font:16px sans-serif;margin:2rem}"
        "td,th{padding:.5rem;border:1px solid #ccc}table{border-collapse:collapse}</style>"
        "<h1>Locust 阶段实测</h1><p>仅统计稳态窗口内开始且完成的请求；"
        "预热和登录不计入。跨窗口完成的请求单独记录，不混入分位数。</p>"
        f"<pre>{html.escape(json.dumps(result, ensure_ascii=False, indent=2))}</pre>"
        f"<table><tr>{headers}</tr>{rows}</table></html>",
        encoding="utf-8",
    )


def environment_metadata(settings) -> dict:
    import psutil

    source = os.getenv("MALL_SOURCE_DIR", str(ROOT / ".sut" / "mall"))
    sut_commit = command(["git", "-C", source, "rev-parse", "HEAD"])
    if sut_commit != SETTINGS.sut_commit:
        raise RuntimeError("The SUT commit does not match the pinned version")
    docker = json.loads(command(["docker", "info", "--format", "{{json .}}"], timeout=30))
    return {
        "created_utc": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "os": platform.platform(),
        "logical_cpus": psutil.cpu_count(),
        "host_memory_gb": round(psutil.virtual_memory().total / 1024**3, 2),
        "docker_version": docker["ServerVersion"],
        "docker_cpus": docker["NCPU"],
        "docker_memory_gb": round(docker["MemTotal"] / 1024**3, 2),
        "sut_commit": sut_commit,
        "test_commit": command(["git", "rev-parse", "HEAD"]),
        "portal_base_url": settings.portal_base_url,
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "performance/step_load.py",
                "performance/resource_monitor.py",
                "performance/locustfile.py",
                "performance/steps.yaml",
                "src/mall_api_test/common/performance_steps.py",
                "src/mall_api_test/common/performance_window.py",
                "src/mall_api_test/repositories/performance_repository.py",
            )
        },
        "running_containers": command(
            ["docker", "ps", "--format", "{{.Names}} {{.Image}}"]
        ).splitlines(),
        "workload": "single dedicated member, fixed product/search, task weights 3:2:1",
        "statistics": "completions within steady window; starts before warmup end excluded",
    }


def run_campaign(args, settings) -> int:
    SETTINGS.require_credentials()
    metadata = environment_metadata(settings)
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "environment.json", metadata)
    write_json(args.output / "settings.json", asdict(settings))
    results = []
    for repeat in range(1, settings.repeats + 1):
        previous = None
        for users in settings.users:
            stage_dir = args.output / f"repeat-{repeat}-users-{users}"
            arguments = [
                sys.executable,
                "-m",
                "performance.step_load",
                "--worker",
                "--profile",
                args.profile,
                "--config",
                str(args.config),
                "--user-count",
                str(users),
                "--repeat",
                str(repeat),
                "--output",
                str(stage_dir),
            ]
            print(f"Starting repeat={repeat} users={users}", flush=True)
            with (args.output / f"repeat-{repeat}-users-{users}.log").open(
                "w", encoding="utf-8"
            ) as log:
                worker = subprocess.run(
                    arguments,
                    cwd=ROOT,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=settings.ready_timeout_seconds
                    + settings.warmup_seconds
                    + settings.measure_seconds
                    + 90,
                )
            if worker.returncode != 0:
                raise RuntimeError(f"Stage failed; inspect {stage_dir.name}.log")
            result = json.loads((stage_dir / "summary.json").read_text(encoding="utf-8"))
            result["comparison"] = compare_steps(previous, result) if previous else "first_level"
            results.append(result)
            write_json(args.output / "campaign.json", results)
            from performance.report import render

            render(args.output)
            write_csv(
                args.output / "campaign.csv",
                [
                    {
                        "repeat": item["repeat"],
                        "users": item["users"],
                        "measured_seconds": item["measured_seconds"],
                        **item["total"],
                        "generator_cpu_median_percent": item["generator_cpu_median_percent"],
                        "stop_reasons": ";".join(item["stop_reasons"]),
                        "comparison": item["comparison"],
                    }
                    for item in results
                ],
            )
            print(
                json.dumps(
                    {
                        "users": users,
                        "rps": round(result["total"]["rps"], 2),
                        "p95_ms": result["total"]["p95_ms"],
                        "stop_reasons": result["stop_reasons"],
                        "comparison": result["comparison"],
                    }
                ),
                flush=True,
            )
            if result["stop_reasons"]:
                return 2
            previous = result
            time.sleep(settings.cooldown_seconds)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--profile", choices=["smoke", "explore", "confirm"], default="explore")
    parser.add_argument("--users", type=int, nargs="+")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--user-count", type=int, default=10, help=argparse.SUPPRESS)
    parser.add_argument("--repeat", type=int, default=1, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.output is None:
        args.output = (
            ROOT / "reports" / "locust" / "steps" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        )
    args.output = args.output.resolve()
    settings = load_step_settings(args.config, args.profile, args.users)
    if args.worker:
        from gevent import monkey

        # Cooperative I/O is sufficient: each virtual user owns its HTTP session.
        # Native logging locks avoid Windows/Python 3.12 finalization failures.
        monkey.patch_all(thread=False)
        os.environ["LOCUST_SKIP_MONKEY_PATCH"] = "1"
        run_stage(args, settings)
        return 0
    return run_campaign(args, settings)


if __name__ == "__main__":
    raise SystemExit(main())
