# Limitations

The repository deliberately separates accepted evidence from plausible but
unqualified capability.

- **Coupled MPI pressure:** focused cross-rank particle contacts and a
  one-step coupled comparison pass. Sustained coupled multi-rank pressure
  evolution is not qualified, so coupled production timing is reported only
  for one MPI rank.
- **Restart through active contact:** the early pre-contact restart has
  practical numerical repeatability. Restart through active particle-piston
  contact remains unresolved and is not claimed to be deterministic.
- **Higher multigrid levels:** the fine quotient action is validated, but
  sustained higher-level multigrid behavior is not accepted in the public
  capability scope.
- **AMR:** cyclic restriction, prolongation, and coarse/fine-interface behavior
  have not been qualified.
- **Formal convergence:** component invariance and conservation checks are
  available, but a manufactured scalar/vector mesh-refinement study remains
  future work.
- **Thermal physics:** validation is isothermal. Particle enthalpy and thermal
  transfer across cyclic interfaces are outside scope.
- **Embedded boundaries:** accepted evidence includes focused flux checks, a
  static six-case geometry matrix, and moving coupled pistons. Arbitrary
  orientations and moving cut-cell topology are not qualified.
- **Hardware portability:** the performance qualification and reproduction use
  the same GPU/toolchain family. Cross-generation reproducibility is not
  established.
- **Full-cylinder comparison figures:** the two full-cylinder comparison
  images in the README are interim context. They are not the basis of the
  quantitative claims. The measured-only particle dataset is the accepted
  public trajectory evidence.
