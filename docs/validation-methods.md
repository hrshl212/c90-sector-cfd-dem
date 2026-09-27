# Validation methods

## Scope labels

Results are labeled as focused, one-step, pre-contact, mature-window, or
production-scope. A focused component test is not treated as evidence for
sustained coupled behavior. Likewise, a one-step MPI comparison is not a
scaling result.

## Rotational comparisons

Particle and vector states are first rotated into a common canonical frame.
Absolute and relative errors are then computed on corresponding physical
components. Cross-seam contact tests compare the induced speeds or complete
vector states against a rotation-equivalent interior contact.

## Full-cylinder-equivalent quantities

The C90 simulation represents one quarter of the cylinder. Extensive C90
quantities are multiplied by four when compared with native full-cylinder
totals. The sanitized raw particle-count series uses this convention.
Normalized particle retention is computed independently for each
configuration:

\[
\eta(t)=100\,N(t)/N(0).
\]

The measured particle series retain their native sample times; no temporal
interpolation is used for the values reported near `0.8 s`.

## Pressure action

An exactly fourfold-symmetric full-domain field is acted on by both the
full-domain operator and the C90 quotient operator. The full-domain result is
reduced to canonical degrees of freedom before global and owner-line relative
errors are evaluated.

## Restart

The accepted coupled restart result uses an early window before strong
particle-piston contact and restores pressure history. It is evaluated against
a documented relative force criterion of `1e-4`. This is practical numerical
repeatability, not bitwise determinism.

## Timing

Timing is reported as seconds per fluid step over a stated window. Component
timers can overlap and must not be summed to reconstruct the total. No
cross-hardware or strong-scaling claim is inferred from the one-GPU results.
