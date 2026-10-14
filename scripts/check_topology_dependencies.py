#!/usr/bin/env python
"""Report quoted GROMACS topology includes and basic directive-order risks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INCLUDE = re.compile(r'^\s*#include\s+"([^"]+)"')
SECTION = re.compile(r"^\s*\[\s*([^\]]+)\s*\]")
TYPE_SECTIONS = {"atomtypes", "bondtypes", "angletypes", "dihedraltypes", "pairtypes", "nonbond_params"}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def scan(path: Path, visited: set[Path], report: dict, molecule_started: bool) -> bool:
    path = path.resolve()
    if path in visited:
        return molecule_started
    visited.add(path)
    if not path.exists():
        report["missing"].append(str(path))
        return molecule_started

    report["files"].append(str(path))
    saw_molecule_type = False
    for number, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        include = INCLUDE.match(raw)
        if include:
            child = (path.parent / include.group(1)).resolve()
            if not child.exists():
                report["missing"].append(str(child))
            else:
                molecule_started = scan(child, visited, report, molecule_started)
            continue
        section = SECTION.match(raw)
        if not section:
            continue
        name = section.group(1).strip().lower()
        if name == "moleculetype":
            saw_molecule_type = True
            molecule_started = True
        elif molecule_started and name in TYPE_SECTIONS:
            report["ordering_risks"].append({"file": str(path), "line": number, "section": name})
    return molecule_started


def main() -> int:
    args = arguments()
    report = {"topology": str(args.top.resolve()), "files": [], "missing": [], "ordering_risks": []}
    scan(args.top, set(), report, False)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if report["missing"] or report["ordering_risks"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
