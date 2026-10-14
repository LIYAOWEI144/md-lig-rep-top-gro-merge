# Topology Merge Rules

## Compatibility Gate

Before producing a combined topology, compare the receptor and ligand files:

- The force-field family and nonbonded conventions must agree. CHARMM/CGenFF
  ligands belong with a CHARMM-compatible protein topology; do not mix with an
  AMBER or OPLS receptor topology without an explicitly designed conversion.
- Full topologies can contain a global `[ defaults ]` block only once. Differing
  defaults are a hard stop.
- Do not include the same `forcefield.itp` more than once. Identical includes
  can be deduplicated; different files with the same force-field role require
  manual review.
- Molecule-type names must be unique or intentionally identical. If both files
  define a type with the same name but different definitions, stop.
- The receptor GRO atom count must match the sum of molecule counts described
  by its topology, and likewise for the ligand before concatenation.

## Coordinate Rules

`merge_gro.py` copies GRO atom lines verbatim: receptor first, ligand second.
It uses the receptor box vector. This is appropriate only when both coordinate
sets already occupy the same coordinate frame and box. It does not dock,
superpose, re-image, center, solvate, or resolve steric clashes.

## Preprocessor Validation

Use an explicit GROMACS check such as:

```powershell
gmx grompp -f grompp_check.mdp -c PROA_LIG.gro -p PROA_LIG.top -o PROA_LIG_check.tpr -maxwarn 0
```

Warnings should be reviewed rather than suppressed. `-maxwarn 0` is intentional
for a validation gate. A successful output `.tpr` verifies that GROMACS can
resolve the topology and coordinate count; it does not prove the physical model
is equilibrated or production ready.

## Include Closure and Solvated Systems

- Inspect quoted includes transitively, not only the top-level `.top`. Record
  every file that supplies atom types, bonded defaults, molecule types,
  restraints, water, and ions.
- Type directives (`[ atomtypes ]`, `[ bondtypes ]`, `[ angletypes ]`, and
  `[ dihedraltypes ]`) must be read before a `[ moleculetype ]` definition.
  A supplement for an unusual receptor atom type therefore belongs after the
  force field and before water/protein/ligand molecule definitions.
- A coordinate file produced by `gmx solvate` needs a compatible `SOL`
  definition. A topology that lists `SOL` without including its water model is
  incomplete.
- After `gmx genion`, define only the ion molecule types that occur in the
  coordinate file and `[ molecules ]`. Do not include a broad ion file if it
  references atom types absent from a reduced force-field conversion.

## Restraints and Command Handoff

- A generated ligand position-restraint file is inert until conditionally
  included by `LIG.itp`.
- Keep protein and ligand restraint macros independent whenever possible. If a
  restraint table uses a symbolic constant, its MDP `define` line must assign a
  numerical value whenever that table is active.
- Before downstream equilibration/production, audit the user command file.
  Start `grompp` without `-maxwarn`; preserve the exact command and explain any
  necessary replacement in a Chinese text review.
