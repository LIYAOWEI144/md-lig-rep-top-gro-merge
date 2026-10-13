#!/usr/bin/env python
"""Merge two full GROMACS topologies into a conservative complex wrapper."""

from __future__ import annotations

import argparse
import json
import re
from collections import OrderedDict
from pathlib import Path

SECTION = re.compile(r"^\s*\[\s*([^\]]+)\s*\]")
INCLUDE = re.compile(r"^\s*#include\s+([\"<])([^\">]+)[\">]")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receptor-top", type=Path, required=True)
    parser.add_argument("--ligand-top", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--system-name", default="Receptor-ligand complex")
    parser.add_argument("--report", type=Path, help="Optional JSON report path.")
    return parser.parse_args()


def split_topology(path: Path) -> tuple[list[str], list[tuple[str, int]]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    sections: list[tuple[str, int]] = []
    for index, line in enumerate(lines):
        match = SECTION.match(line)
        if match:
            sections.append((match.group(1).strip().lower(), index))
    system_positions = [position for name, position in sections if name == "system"]
    molecule_positions = [position for name, position in sections if name == "molecules"]
    if len(system_positions) != 1 or len(molecule_positions) != 1:
        raise ValueError(f"{path} must be a full topology with exactly one [ system ] and [ molecules ] block")
    if system_positions[0] > molecule_positions[0]:
        raise ValueError(f"{path}: [ system ] must precede [ molecules ]")
    return lines[: system_positions[0]], sections


def molecule_table(path: Path) -> list[tuple[str, int]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = next(i for i, line in enumerate(lines) if (match := SECTION.match(line)) and match.group(1).strip().lower() == "molecules")
    molecules: list[tuple[str, int]] = []
    for line in lines[start + 1 :]:
        if SECTION.match(line):
            break
        stripped = line.split(";", 1)[0].strip()
        if not stripped:
            continue
        fields = stripped.split()
        if len(fields) < 2:
            raise ValueError(f"{path}: malformed [ molecules ] entry: {line!r}")
        molecules.append((fields[0], int(fields[1])))
    if not molecules:
        raise ValueError(f"{path}: empty [ molecules ] table")
    return molecules


def direct_molecule_types(lines: list[str]) -> set[str]:
    """Return molecule types defined directly in this wrapper, not in includes."""
    names: set[str] = set()
    awaiting_name = False
    for line in lines:
        match = SECTION.match(line)
        if match:
            awaiting_name = match.group(1).strip().lower() == "moleculetype"
            continue
        if not awaiting_name:
            continue
        stripped = line.split(";", 1)[0].strip()
        if stripped:
            names.add(stripped.split()[0])
            awaiting_name = False
    return names


def normalize_preamble(lines: list[str], owner: Path, seen_includes: set[str], defaults_seen: bool) -> tuple[list[str], bool, list[str]]:
    result: list[str] = []
    includes: list[str] = []
    current_section = None
    for line in lines:
        match = SECTION.match(line)
        if match:
            current_section = match.group(1).strip().lower()
            if current_section == "defaults":
                if defaults_seen:
                    raise ValueError("Both inputs define [ defaults ]; use one shared force-field topology instead.")
                defaults_seen = True
        include = INCLUDE.match(line)
        if include:
            delimiter, raw_path = include.groups()
            if delimiter == "\"":
                resolved = (owner.parent / raw_path).resolve()
                key = str(resolved).replace("\\", "/")
                rendered = f'#include "{key}"'
            else:
                key = f"<{raw_path}>"
                rendered = line
            if key in seen_includes:
                continue
            seen_includes.add(key)
            includes.append(key)
            result.append(rendered)
        else:
            result.append(line)
    return result, defaults_seen, includes


def main() -> int:
    args = parse_args()
    receptor_body, _ = split_topology(args.receptor_top)
    ligand_body, _ = split_topology(args.ligand_top)
    duplicate_direct_types = direct_molecule_types(receptor_body) & direct_molecule_types(ligand_body)
    if duplicate_direct_types:
        names = ", ".join(sorted(duplicate_direct_types))
        raise ValueError(f"Both inputs define the direct [ moleculetype ] name(s): {names}. Resolve the conflict before merging.")
    seen: set[str] = set()
    receptor_body, defaults_seen, receptor_includes = normalize_preamble(receptor_body, args.receptor_top, seen, False)
    ligand_body, defaults_seen, ligand_includes = normalize_preamble(ligand_body, args.ligand_top, seen, defaults_seen)
    forcefields = {
        entry for entry in [*receptor_includes, *ligand_includes]
        if not entry.startswith("<") and Path(entry).name.lower() == "forcefield.itp"
    }
    if len(forcefields) > 1:
        raise ValueError("Inputs reference different forcefield.itp files; review force-field compatibility before merging.")
    molecules: OrderedDict[str, int] = OrderedDict()
    for name, count in [*molecule_table(args.receptor_top), *molecule_table(args.ligand_top)]:
        molecules[name] = molecules.get(name, 0) + count

    output_lines = [
        "; Generated by merge_topologies.py. Inspect merge_report.json before MD.",
        *receptor_body,
        "",
        "; Ligand topology definitions",
        *ligand_body,
        "",
        "[ system ]",
        args.system_name,
        "",
        "[ molecules ]",
        "; Compound        #mols",
        *[f"{name:<16} {count}" for name, count in molecules.items()],
        "",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(output_lines), encoding="utf-8")
    report = {
        "receptor_top": str(args.receptor_top.resolve()),
        "ligand_top": str(args.ligand_top.resolve()),
        "output_top": str(args.output.resolve()),
        "receptor_includes": receptor_includes,
        "ligand_includes": ligand_includes,
        "shared_defaults": defaults_seen,
        "direct_molecule_types": {
            "receptor": sorted(direct_molecule_types(receptor_body)),
            "ligand": sorted(direct_molecule_types(ligand_body)),
        },
        "combined_molecules": list(molecules.items()),
    }
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
