"""Render measured stage summaries without averaging percentiles."""

import argparse
import html
import json
from pathlib import Path


def chart(results: list[dict], field: str, title: str, unit: str) -> str:
    width, height = 840, 360
    left, right, top, bottom = 75, 30, 45, 65
    xs = sorted({item["users"] for item in results})
    maximum = max((item["total"][field] or 0 for item in results), default=1) * 1.15 or 1

    def x(value):
        return left + (value - min(xs)) / max(max(xs) - min(xs), 1) * (width - left - right)

    def y(value):
        return height - bottom - value / maximum * (height - top - bottom)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="sans-serif" font-size="13" fill="#243142">',
        f'<text x="{left}" y="25" font-size="18">{html.escape(title)}</text>',
    ]
    if any(item.get("stop_reasons") for item in results):
        parts.append(
            '<text x="360" y="25" fill="#b02020">红点：触发停止条件，不作为容量结论</text>'
        )
    for index in range(6):
        value = maximum * index / 5
        parts += [
            f'<path d="M{left},{y(value):.2f} H{width - right}" stroke="#dde3eb"/>',
            f'<text x="{left - 8}" y="{y(value) + 4:.2f}" text-anchor="end">{value:.1f}</text>',
        ]
    for users in xs:
        parts.append(
            f'<text x="{x(users):.2f}" y="{height - bottom + 22}" text-anchor="middle">'
            f"{users}</text>"
        )
    colors = ("#1764b2", "#b34716", "#348246", "#7850a0", "#a44b70")
    for repeat in sorted({item["repeat"] for item in results}):
        items = sorted(
            (item for item in results if item["repeat"] == repeat), key=lambda item: item["users"]
        )
        color = colors[(repeat - 1) % len(colors)]
        points = " ".join(
            f"{x(item['users']):.2f},{y(item['total'][field] or 0):.2f}" for item in items
        )
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
        for item in items:
            point_color = "#b02020" if item.get("stop_reasons") else color
            warning = html.escape("; ".join(item.get("stop_reasons", [])))
            parts.append(
                f'<circle cx="{x(item["users"]):.2f}" cy="{y(item["total"][field] or 0):.2f}" '
                f'r="4" fill="{point_color}"><title>repeat={repeat}, users={item["users"]}, '
                f"{field}={item['total'][field]} {warning}</title></circle>"
            )
        parts.append(
            f'<text x="{left + 150 * (repeat - 1)}" y="{height - 8}" fill="{color}">'
            f"重复 {repeat}</text>"
        )
    parts.append(f'<text x="{width - 150}" y="{height - 8}">用户数 / {html.escape(unit)}</text>')
    parts.append("</g></svg>")
    return "".join(parts)


def render(folder: Path) -> None:
    results = json.loads((folder / "campaign.json").read_text(encoding="utf-8"))
    if not results:
        raise ValueError("Cannot render an empty campaign")
    for field, title, unit in (
        ("success_rps", "稳态成功请求吞吐", "req/s"),
        ("p95_ms", "稳态聚合 P95", "ms"),
    ):
        (folder / f"{field}.svg").write_text(chart(results, field, title, unit), encoding="utf-8")
    rows = []
    for item in results:
        total = item["total"]
        cells = (
            item["repeat"],
            item["users"],
            item["measured_seconds"],
            total["requests"],
            total["failures"],
            round(total["success_rps"], 2),
            total["p95_ms"],
            total["p99_ms"],
            f"{total['failure_ratio']:.5%}",
            f"{item['generator_cpu_median_percent']:.1f}%",
            "; ".join(item["stop_reasons"]) or item["comparison"],
        )
        rows.append(
            "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in cells) + "</tr>"
        )
    (folder / "index.html").write_text(
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>阶梯读取负载实验</title>'
        "<style>body{font:16px sans-serif;max-width:1200px;margin:2rem auto;color:#243142}"
        "td,th{border:1px solid #ccc;padding:.5rem}table{border-collapse:collapse}"
        "img{width:100%;max-width:900px}</style><h1>阶梯读取负载实验</h1>"
        "<p>固定热点数据、单会员、独立会话；预热及登录不计入稳态。"
        "每档 P95 独立计算，不平均分位数。候选拐点不是已确认容量上限。</p>"
        '<img src="success_rps.svg" alt="成功 RPS 曲线"><img src="p95_ms.svg" alt="P95 曲线">'
        "<table><tr><th>重复</th><th>用户</th><th>窗口秒</th><th>请求</th>"
        "<th>失败数</th><th>成功 RPS</th>"
        "<th>P95 ms</th><th>P99 ms</th><th>失败率</th><th>压测进程 CPU 中位数</th>"
        "<th>判定</th></tr>" + "".join(rows) + "</table></html>",
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    render(parser.parse_args().folder)
