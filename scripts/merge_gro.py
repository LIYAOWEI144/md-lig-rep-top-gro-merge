#!/usr/bin/env python
"""Concatenate receptor and ligand GRO coordinates without changing atom lines."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receptor", type=Path, required=True)
    parser.add_argument("--ligand", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--title", default="Receptor-ligand complex")
    parser.add_argument("--report", type=Path, help="Optional JSON report path.")
    return parser.parse_args()


def read_gro(path: Path) -> tuple[str, list[str], str]:
    lines = path.read_text(encoding="ascii").splitlines()
    if len(lines) < 3:
        raise ValueError(f"{path} is too short to be a GRO file")
    try:
        count = int(lines[1].strip())
    except ValueError as error:
        raise ValueError(f"{path}: invalid atom count line") from error
    expected = count + 3
    if len(lines) != expected:
        raise ValueError(f"{path}: declares {count} atoms but contains {len(lines) - 3} atom records")
    atoms = lines[2 : 2 + count]
    if any(len(line) < 44 for line in atoms):
        raise ValueError(f"{path}: found a malformed GRO atom line")
    return lines[0], atoms, lines[-1]


def main() -> int:
    args = parse_args()
    receptor_title, receptor_atoms, receptor_box = read_gro(args.receptor)
    ligand_title, ligand_atoms, ligand_box = read_gro(args.ligand)
    del receptor_title, ligand_title
    if receptor_box != ligand_box:
        print("Warning: ligand box differs from receptor box; preserving receptor box.")

    merged = [args.title, f"{len(receptor_atoms) + len(ligand_atoms):5d}", *receptor_atoms, *ligand_atoms, receptor_box]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(merged) + "\n", encoding="ascii")
    report = {
        "receptor_gro": str(args.receptor.resolve()),
        "ligand_gro": str(args.ligand.resolve()),
        "output_gro": str(args.output.resolve()),
        "receptor_atom_count": len(receptor_atoms),
        "ligand_atom_count": len(ligand_atoms),
        "merged_atom_count": len(receptor_atoms) + len(ligand_atoms),
        "box_source": "receptor",
        "ligand_box_matches_receptor": ligand_box == receptor_box,
    }
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
