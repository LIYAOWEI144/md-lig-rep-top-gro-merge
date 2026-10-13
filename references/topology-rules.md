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
