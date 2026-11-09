"""Cross-check saved summaries against raw stage counters and resource evidence."""

import argparse
import csv
import hashlib
import json
import math
import statistics
from datetime import datetime
from pathlib import Path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit(folder: Path, source_root: Path | None = None) -> dict:
    campaign = read_json(folder / "campaign.json")
    if not campaign:
        raise ValueError("Empty campaign")
    metadata = read_json(folder / "environment.json")
    if source_root is not None:
        for name, expected in metadata["source_sha256"].items():
            actual = hashlib.sha256((source_root / name).read_bytes()).hexdigest()
            if actual != expected:
                raise ValueError(f"Source fingerprint changed: {name}")
    total_requests = 0
    for item in campaign:
        stage = folder / f"repeat-{item['repeat']}-users-{item['users']}"
        saved = read_json(stage / "summary.json")
        if saved != {key: value for key, value in item.items() if key != "comparison"}:
            raise ValueError("Campaign and stage summaries disagree")
        seconds = (
            datetime.fromisoformat(item["end_utc"]) - datetime.fromisoformat(item["start_utc"])
        ).total_seconds()
        if seconds <= 0 or not math.isclose(seconds, item["measured_seconds"]):
            raise ValueError("Invalid measurement window")
        total = item["total"]
        if "started_requests" in item and item["started_requests"] != (
            total["requests"] + item["tail_requests"] + item["incomplete_requests"]
        ):
            raise ValueError("Started/completed request accounting mismatch")
        for field in ("requests", "failures"):
            if total[field] != sum(entry[field] for entry in item["endpoints"]):
                raise ValueError(f"Endpoint {field} do not add up")
        if not math.isclose(total["rps"], total["requests"] / seconds):
            raise ValueError("RPS denominator mismatch")
        if not math.isclose(
            total["success_rps"], (total["requests"] - total["failures"]) / seconds
        ):
            raise ValueError("Successful RPS mismatch")
        resources = read_json(stage / "resources.json")
        if len(resources) != item["resource_samples"]:
            raise ValueError("Resource sample count mismatch")
        if resources:
            cpu = statistics.median(sample["generator_cpu_percent"] for sample in resources)
            if not math.isclose(cpu, item["generator_cpu_median_percent"]):
                raise ValueError("Generator CPU summary mismatch")
        with (stage / "endpoints.csv").open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        if int(rows[0]["requests"]) != total["requests"]:
            raise ValueError("CSV and JSON disagree")
        if not (stage / "report.html").is_file():
            raise ValueError("Stage HTML report missing")
        total_requests += total["requests"]
    return {
        "stages": len(campaign),
        "requests": total_requests,
        "stopped_stages": sum(bool(item["stop_reasons"]) for item in campaign),
        "source_checked": source_root is not None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--source-root", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(audit(arguments.folder, arguments.source_root), indent=2))
