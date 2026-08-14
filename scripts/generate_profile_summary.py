#!/usr/bin/env python3

import json
import re
from pathlib import Path


README_PATH = Path("README.md")
SNAPSHOT_DIR = Path("snapshots")
START_MARKER = "<!-- impact-summary:start -->"
END_MARKER = "<!-- impact-summary:end -->"


def human_name(identity: str) -> str:
    if identity.startswith("github:"):
        return identity.removeprefix("github:").rsplit("/", 1)[-1]
    return identity


def metric_value(metric: dict) -> str | None:
    value = metric.get("value", {})
    kind = value.get("type")
    raw = value.get("value")
    if kind == "count" and isinstance(raw, int):
        return f"{raw:,}"
    if kind == "real" and isinstance(raw, (int, float)):
        return f"{raw:.2f}".rstrip("0").rstrip(".")
    if raw is None:
        return None
    return str(raw)


def first_metric(metrics: list[dict], *names: str) -> str | None:
    for name in names:
        for metric in metrics:
            if metric.get("name") == name:
                value = metric_value(metric)
                if value is not None:
                    return value
    return None


def build_summary_line(label: str, metrics: list[dict]) -> str:
    parts = []
    for metric_name, label_name in (
        ("stars", "stars"),
        ("contributors", "contributors"),
        ("release_downloads", "release downloads"),
        ("forks", "forks"),
    ):
        value = first_metric(metrics, metric_name)
        if value is not None:
            parts.append(f"{value} {label_name}")
        if len(parts) == 3:
            break
    if not parts:
        return f"- **{label}** — metrics available in [BOASTS.md](./BOASTS.md)"
    return f"- **{label}** — {', '.join(parts)} ([full report](./BOASTS.md))"


def build_summary_lines(snapshot_paths: list[Path]) -> list[str]:
    summary_lines = [
        "#### Impact summary",
        "",
        "_Updated automatically from the latest boast snapshots. See [BOASTS.md](./BOASTS.md) for the full report._",
        "",
    ]

    if not snapshot_paths:
        summary_lines.append(
            "- Snapshot metrics will appear here after the workflow generates [BOASTS.md](./BOASTS.md)."
        )
        return summary_lines

    for snapshot_path in snapshot_paths:
        data = json.loads(snapshot_path.read_text())
        repo_identity = next(
            (
                identity
                for identity in data.get("identities", [])
                if isinstance(identity, str) and identity.startswith("github:")
            ),
            None,
        )
        metrics = []
        for result in data.get("results", []):
            outcome = result.get("outcome", {})
            if outcome.get("status") != "values":
                continue
            if repo_identity is None:
                metrics.extend(outcome.get("metrics", []))
            else:
                metrics.extend(
                    metric
                    for metric in outcome.get("metrics", [])
                    if metric.get("identity") == repo_identity
                )
        summary_lines.append(
            build_summary_line(human_name(repo_identity or snapshot_path.stem), metrics)
        )

    return summary_lines


def main() -> None:
    snapshot_paths = sorted(SNAPSHOT_DIR.glob("*.json"))
    replacement = START_MARKER + "\n" + "\n".join(build_summary_lines(snapshot_paths)) + "\n" + END_MARKER
    readme = README_PATH.read_text()
    pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.S)

    if pattern.search(readme):
        updated = pattern.sub(replacement, readme, count=1)
    else:
        anchor = "#### For more information"
        if anchor in readme:
            updated = readme.replace(anchor, replacement + "\n\n" + anchor, 1)
        else:
            updated = readme.rstrip() + "\n\n" + replacement + "\n"

    README_PATH.write_text(updated)


if __name__ == "__main__":
    main()
