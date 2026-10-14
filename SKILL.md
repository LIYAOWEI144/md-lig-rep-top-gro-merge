---
name: gromacs-receptor-ligand-merge
description: Merge user-supplied receptor and ligand GROMACS topology and GRO coordinate files into a validated receptor-ligand package with reproducible scripts. Use when assembling an existing receptor and ligand for GROMACS analysis; do not use to parameterize a novel ligand.
---

# GROMACS Receptor-Ligand Merge

## Outcome

Merge existing receptor and ligand coordinate/topology inputs without changing
their atom order, bonded parameters, force-field definitions, or molecule
identity. Deliver a self-contained result folder containing:

```text
PROA_LIG.gro
PROA_LIG.top
merge_report.json
topology_dependencies.json
grompp_check.mdp
reproducible_scripts/
README.md
```

Use the names requested by the user when supplied; otherwise use `PROA` for
the receptor and `LIG` for the ligand only after verifying their molecule types.

## Required Clarification

Ask for the output directory before creating files when the user has not
provided one. Also request or infer the four input paths: receptor topology,
ligand topology, receptor GRO, and ligand GRO. If an input is ambiguous, ask
which file represents the final molecule definition rather than guessing.

When an extra project-facing file is needed beyond this merge delivery (for
example, an edited command file, a restraint topology, water/ion topology, or
an MDP), first ask for its output directory, desired file type/name, and
whether it is a runnable input, a report, or an analysis output. A command
review is a `.txt` report and may live inside the selected delivery folder only
when the user explicitly selects that folder.

## Workflow

1. Inspect both topology files. Identify their include hierarchy, molecule
   names/counts, force-field sources, and whether they are full `.top` files or
   molecule `.itp` fragments.
2. Verify compatibility before merging: shared force-field family, no duplicate
   incompatible `[ defaults ]`, unique molecule-type names, and matching
   coordinate/topology atom counts.
3. Use `scripts/merge_gro.py` to concatenate only atom records, preserve the
   receptor simulation box, and verify the resulting count exactly equals the
   sum of the inputs.
4. Use `scripts/merge_topologies.py` when both inputs are full `.top` files.
   It creates a wrapper topology from their definitions and combines their
   `[ molecules ]` tables. It must stop on incompatible force-field includes,
   direct duplicate `[ defaults ]` blocks, or conflicting molecule types.
5. Run `scripts/check_topology_dependencies.py` against the merged topology.
   Resolve the full quoted-include graph, record every source, and stop on a
   missing include, an unresolved molecule type, or a type-directive include
   placed after molecule definitions. A self-contained result copies the exact
   compatible include closure; never replace a CGenFF force field with a stock
   GROMACS force field just to satisfy an include.
6. If the user provides a command text, call the analysis-assistant workflow
   to produce a Chinese `原命令/建议命令/原因` review before any simulation is
   run. Do not silently keep tutorial group numbers, `-maxwarn`, water-model
   choices, or production barostats.
7. Copy the exact scripts used into `<output>/reproducible_scripts/`, alongside
   a command file with the concrete input paths and validation command.
8. Generate a minimal `grompp_check.mdp` and run ligand/receptor-complex
   `gmx grompp` using the output GRO/TOP with `-maxwarn 0`. A generated `.tpr`
   is required before saying the merge is usable for later GROMACS analysis.

Read [topology rules](references/topology-rules.md) before merging files with
different force-field include trees, solvent, ions, or multiple receptor chains.

## Boundaries

- Never concatenate two complete `.top` files blindly; each contains global
  directives and potentially duplicate force-field definitions.
- Do not merge systems from different force-field families merely because both
  use GROMACS syntax.
- Do not add solvent, ions, restraints, or positional restraints unless the
  user asks for them. If an existing solvated coordinate file contains `SOL`
  or ions, validate their molecule definitions and atom types before claiming
  it is usable.
- Do not share a generic `POSRES` macro between protein and ligand restraint
  blocks unless their force constants and activation policy truly match. An
  active symbolic force constant must be numerically defined in the MDP.
- If `grompp` fails, retain the package and report the exact failure. Run the
  original receptor and ligand controls where useful to determine whether the
  failure predates the merge.
