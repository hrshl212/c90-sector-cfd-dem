# GPU performance engineering

This case study separates application-level evidence from kernel-profiler
evidence. It documents optimization decisions without distributing the
underlying simulation source or private implementation symbols.

## Qualified workload

The accepted configuration advances a `58 × 58 × 470` C90 mesh with 111,907
particles on one NVIDIA H100 and one MPI rank. The qualified mature window
covers 100 fluid steps.

| Metric | Qualified mean |
|---|---:|
| Total step time | `0.363756838 s/step` |
| Fluid stage | `0.265633965 s/step` |
| Particle stage | `0.079816885 s/step` |
| Coupling stage | `0.016893967 s/step` |
| Nodal pressure solve | `0.069875217 s/step` |

Component timers can overlap or nest, so they must not be added to reconstruct
the total. A separate package-local reproduction measured
`0.366873283 s/step` over the same 100-step window.

## Optimization strategy

The optimization work targeted repeated work and synchronization before
attempting lower-level arithmetic tuning.

1. **Reduce the represented domain.** Fourfold rotational symmetry replaces
   the full cylinder with one canonical quadrant while retaining conservative
   transfers and rotated vector behavior.
2. **Reuse particle-neighborhood state.** Neighbor information and substep
   scratch storage are retained when their validity conditions hold, reducing
   repeated construction and allocation work.
3. **Avoid redundant image and scratch passes.** The one-GPU sector path uses
   in-place rotational-image updates and skips temporary state that is not
   consumed by the selected physics.
4. **Expose independent GPU work.** Force-to-motion and particle-motion stages
   are sequenced to avoid unnecessary host synchronization in the one-rank
   path.
5. **Warm-start the pressure solve.** A scaled previous-pressure estimate
   reduces iterative work while preserving the selected pressure-accuracy
   envelope.

These mechanisms were qualified as a combined configuration. The public data
do not support assigning an independent speedup to each mechanism.

## Performance versus accuracy

The fastest tested pressure warm start reached `0.332091 s/step`, but it was
rejected because its wall-pressure reference error was `3.35685%` on average
and `15.8208%` at maximum. The selected configuration is slower at
`0.363756838 s/step`, but limits the corresponding mean and maximum errors to
`0.434781%` and `2.04477%`.

This was therefore a constrained optimization problem: reduce time per step
while retaining particle count, timestep stability, and bounded pressure and
particle-state differences. A faster configuration was not promoted merely
because it had the lowest wall time.

## Large-particle DEM optimization campaign

A separate production trajectory was initialized with 5,073,064 particles.
The matched optimization windows occurred later in that trajectory, after
physical outlet loss had reduced the active population to approximately
3.7--3.9 million particles. This distinction prevents the initial population
from being mistaken for the exact population in every benchmark window.

Stage timers first showed that particle kernels consumed 89.58% of measured
DEM time, while neighbor-list construction consumed 10.21%. Cyclic-image
refresh, redistribution, exchange, and other measured stages together were
below 0.21%. A finer profile then assigned 97.94% of particle-kernel time to
contact/wall work, versus 1.71% to motion and 0.32% to scratch clearing. These
measurements ruled out communication and scratch fusion as useful first
targets.

Each promoted change was tested against a matched control while retaining the
contact model and production controller:

| Optimization | Matched result | Qualification scope |
|---|---:|---|
| Reject noncontacting particle-pair candidates before loading velocity, spin, and material state | 32.83% lower particle-kernel time; 26.22% lower mean accepted-step compute | 120 steps, same executable with a runtime A/B toggle |
| Split wall/piston and particle-pair work into specialized launches | 11.02% lower particle-kernel time; 7.96% lower mean step time; 7.61% lower elapsed time | 120-step matched A/B |
| Constrain only the pair launch to two resident blocks per SM | 27.42% lower pair-kernel time; 14.48% lower mean step time | Same-H100 120+120-step comparison |
| Sort particles spatially every 50 accepted fluid steps | 52.78% lower normalized DEM-substep time; 48.34% lower particle-kernel time; 68.52% lower neighbor-list time; 57.00% lower summed DEM compute | 120 steps crossing three sort events |

The comparisons also checked accepted overlap, piston-force behavior, finite
state, and final particle count. Small outlet-particle differences were
retained in the qualification record rather than hidden by reporting only
timing.

The percentages are sequential A/B results and must not be multiplied to
claim a synthetic total speedup. Later production advanced at roughly 2,150
accepted steps/hour (about 1.67 s/step), compared with roughly 506 steps/hour
(about 7.1 s/step) in an earlier production segment. This approximately 3.8x
operational throughput increase is reported as an end-to-end observation,
not as an isolated kernel speedup: the particle population, timestep history,
and controller activity also evolved along the production trajectory.

## Kernel-profiler evidence

A targeted Nsight Compute capture of the qualified, spatially sorted
particle-pair kernel measured:

| Metric | Measured value |
|---|---:|
| Kernel duration | `7.372096 ms` |
| Registers per thread | `128` |
| Theoretical / achieved occupancy | `25.00% / 19.88%` |
| Active / eligible warps per scheduler | `3.24 / 0.20` |
| Active scheduler cycles with no eligible warp | `82.40%` |
| Long-scoreboard share of sampled stalls | `68.01%` |
| Excessive L2 sectors | `67.77%` of theoretical sectors |
| DRAM throughput | `7.91%` of peak |
| L2 atomic-input activity | `2.61%` of peak |

The kernel was latency limited by irregular candidate and neighbor gathers,
with too little occupancy to hide those waits. It was not limited by peak
DRAM bandwidth or atomic throughput. That diagnosis prevented an unsupported
atomic-aggregation project and motivated tests of contact compaction and
higher occupancy.

Those follow-up tests were informative failures. A two-stage active-contact
compaction reduced the heavy force portion but added enough filtering and
prefix work to increase total DEM time. A three-block-per-SM launch reduced
register use from 128 to 80 registers/thread, but increased stack use from 48
to 232 bytes and made pair time 9.49% slower. The retained two-block launch is
therefore an evidence-based balance between occupancy and spill traffic.

A second bounded profile of the smaller 111,907-particle validation workload
found the nodal pressure-operator kernel at 124 registers/thread, 25%
theoretical occupancy, 20.13% achieved occupancy, and 42.18 microseconds per
captured launch. It identifies pressure-operator register pressure as a future
target, but no speedup is claimed because a corresponding implementation and
matched A/B gate have not been completed.

## Portability interpretation

The accepted measurement is CUDA/H100-specific. The optimization principles
map to AMD hardware—minimize launches and full-population traversals, reuse
storage, preserve coalesced access, and expose asynchronous work—but no HIP,
ROCm, wavefront, or AMD occupancy measurement has been performed. This
repository therefore makes no NVIDIA-to-AMD performance-portability claim.
