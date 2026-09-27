# Implementation overview

The implementation is organized around a rotational identification layer
rather than treating the two radial faces as ordinary planar periodic faces.
At an architectural level, the coupled time step performs four related tasks.

1. Ghost and face data are obtained from the partner face with the appropriate
   scalar, vector, or tensor rotation.
2. Particles crossing a face are canonicalized, and rotational images expose
   physical neighbors for seam and near-axis contact.
3. Flux and particle-source contributions from equivalent locations are
   accumulated conservatively.
4. Pressure projection operates on canonical quotient unknowns while the
   physical correction is interpreted in the expanded symmetric space.

The coupled piston calculation uses both an immersed fluid boundary and a DEM
contact boundary. Validation therefore checks that both move, that particles
remain accounted for, and that total piston force equals the sum of the fluid
and particle-contact contributions.

The production evidence in this repository is for an isothermal,
single-level, one-MPI-rank coupled calculation on one GPU. Two-rank evidence is
reported separately for focused particle contacts and a bounded one-step
coupled correctness comparison.

No private source layout, internal symbol names, kernels, or input controls are
described here. The repository is a scientific portfolio, not a distribution
of the underlying solver modification.
