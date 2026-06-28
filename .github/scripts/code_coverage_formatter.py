#!/usr/bin/env python3

import argparse
import glob
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


DEFAULT_PATTERN = "**/build/JacocoReports/test/jacocoTestReport.xml"

METRIC_ORDER = [
    "INSTRUCTION",
    "LINE",
    "BRANCH",
    "COMPLEXITY",
    "METHOD",
    "CLASS",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Format JaCoCo XML reports as a GitHub Actions summary."
    )

    parser.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help=f"Glob pattern for JaCoCo XML reports. Default: {DEFAULT_PATTERN}",
    )

    parser.add_argument(
        "--summary-file",
        default=os.environ.get("GITHUB_STEP_SUMMARY"),
        help="GitHub step summary file. Defaults to GITHUB_STEP_SUMMARY.",
    )

    parser.add_argument(
        "--min-line-coverage",
        type=float,
        default=None,
        help="Optional minimum line coverage percentage. Fails if below this value.",
    )

    return parser.parse_args()


def collect_reports(pattern):
    return sorted(glob.glob(pattern, recursive=True))


def add_counter(totals, counter_type, missed, covered):
    if counter_type not in totals:
        totals[counter_type] = {
            "missed": 0,
            "covered": 0,
        }

    totals[counter_type]["missed"] += missed
    totals[counter_type]["covered"] += covered


def parse_report(report_file):
    tree = ET.parse(report_file)
    root = tree.getroot()

    counters = {}

    for counter in root.findall("counter"):
        counter_type = counter.attrib["type"]
        missed = int(counter.attrib["missed"])
        covered = int(counter.attrib["covered"])

        counters[counter_type] = {
            "missed": missed,
            "covered": covered,
        }

    return counters


def percentage(covered, missed):
    total = covered + missed

    if total == 0:
        return None

    return covered / total * 100


def format_percentage(value):
    if value is None:
        return "n/a"

    return f"{value:.2f}%"


def metric_label(metric):
    return metric.title().replace("_", " ")


def write_summary(summary_file, report_files, totals):
    lines = []

    lines.append("## JaCoCo Code Coverage")
    lines.append("")
    lines.append("| Metric | Covered | Missed | Coverage |")
    lines.append("|---|---:|---:|---:|")

    for metric in METRIC_ORDER:
        if metric not in totals:
            continue

        covered = totals[metric]["covered"]
        missed = totals[metric]["missed"]
        coverage = percentage(covered, missed)

        lines.append(
            f"| {metric_label(metric)} | {covered} | {missed} | {format_percentage(coverage)} |"
        )

    lines.append("")
    lines.append("### Found reports")
    lines.append("")

    for report_file in report_files:
        lines.append(f"- `{report_file}`")

    lines.append("")

    output = "\n".join(lines)

    print(output)

    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as file:
            file.write(output)
            file.write("\n")


def main():
    args = parse_args()

    report_files = collect_reports(args.pattern)

    if not report_files:
        print(f"No JaCoCo XML reports found for pattern: {args.pattern}", file=sys.stderr)
        return 1

    totals = {}

    for report_file in report_files:
        counters = parse_report(report_file)

        for counter_type, values in counters.items():
            add_counter(
                totals,
                counter_type,
                values["missed"],
                values["covered"],
            )

    write_summary(args.summary_file, report_files, totals)

    if args.min_line_coverage is not None and "LINE" in totals:
        line_coverage = percentage(
            totals["LINE"]["covered"],
            totals["LINE"]["missed"],
        )

        if line_coverage is not None and line_coverage < args.min_line_coverage:
            print(
                f"Line coverage {line_coverage:.2f}% is below required minimum "
                f"of {args.min_line_coverage:.2f}%.",
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())