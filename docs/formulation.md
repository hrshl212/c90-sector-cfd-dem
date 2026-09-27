# Formulation

## Rotational identification

Let the simulated domain occupy the quadrant

\[
\Omega_{90}=\{(x,y,z): x\ge 0,\;y\ge 0\}.
\]

The quarter-turn matrix and its inverse are

\[
R=\begin{bmatrix}0&-1&0\\1&0&0\\0&0&1\end{bmatrix},
\qquad
R^{-1}=R^{T}.
\]

Points on the two radial faces are identified by this rotation. A scalar
field `q` satisfies

\[
q(Rx)=q(x),
\]

while a physical vector `u` satisfies

\[
u(Rx)=R\,u(x).
\]

Axial components are unchanged; the two transverse components rotate with the
geometry. Tensor quantities follow the corresponding two-sided transform.

## Particle state

When a particle leaves one radial face, its position, translational velocity,
and angular velocity are rotated into the canonical quadrant. Rotational
images make a physical neighbor visible across the identified faces. An image
is a representation of a real particle, not an additional degree of freedom,
so impulses are accumulated on the owning real particle exactly once.

## Conservative transfer

For an extensive quantity, sector contributions are summed over each
four-member rotational orbit. Local field values remain sector-scale, while
reported whole-cylinder totals use a factor of four. This distinction is
stated explicitly for particle counts and piston forces.

## Quotient pressure operator

Let `P` expand canonical sector unknowns into a fourfold-symmetric full-domain
field, and let `A` denote the full-domain discrete pressure operator. The
reduced action is

\[
A_{90}=P^{T} A P.
\]

This construction folds the contributions of rotationally equivalent rows
into one canonical degree of freedom. The fine-level action is validated
against an exactly fourfold-symmetric full-domain reference. That algebraic
result does not by itself qualify every coarse-grid or distributed solver
configuration.
