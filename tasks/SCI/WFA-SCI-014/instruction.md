> The working directory is `/workspace`. This task has no input files. Write your deliverables to `/workspace/submission/`: the `outputs/`, `code/` and `logs/` directories mentioned in the task correspond to `/workspace/submission/outputs/`, `/workspace/submission/code/` and `/workspace/submission/logs/` (grading reads only `/workspace/submission/`).
>
> No network access at runtime. Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, statsmodels 0.14.4, matplotlib 3.9.2, h5py 3.12.1.

# The momentum-mixing Hatsugai–Kohmoto model: approaching Hubbard physics from a solvable model

## Background and method (adapted from a physics journal article)

The Hatsugai–Kohmoto (HK) model replaces the Hubbard interaction by an interaction that is local in momentum space, U Σ_k n_k↑ n_k↓, and is therefore exactly solvable, but it differs strongly from the Hubbard model. One generalization "mixes" n momenta: group every n sites of the original lattice into a supercell and, in the reduced Brillouin zone of the supercell (rBZ_n, 1/n of the original Brillouin zone), write an n-orbital local Hamiltonian for each supercell momentum K:

H_n = Σ_{K∈rBZ_n} [ Σ_{α,α',σ} g_{αα'}(K) c†_{Kασ} c_{Kα'σ} − μ Σ_{α,σ} n_{Kασ} + U Σ_α n_{Kα↑} n_{Kα↓} ],

where g(K) is the Bloch hopping matrix of the n sites in the supercell: g_{αα'}(K) = Σ_δr t_{αα'}^{δr} e^{iK·(r_α − r_α' + δr)}. Different K are not coupled, so the whole model is a sum of many independent n-site clusters; the cluster at each K is equivalent to an n-site Hubbard cluster with K-dependent twisted boundary conditions. n=1 recovers the original HK model; n→N recovers the Hubbard model. The thermodynamic limit corresponds to K taking continuous values in rBZ_n (numerically: use a sufficiently dense grid and check convergence). Below, t=1 is the unit of energy.

Specific settings:

- **One dimension**: chain with nearest-neighbour hopping −t; the supercell is n adjacent sites (n even); supercell momentum K∈[−π/n, π/n).
- **Two-dimensional square lattice** (nearest-neighbour t, next-nearest-neighbour t′):
  - n=1: single site, ε_k = −2t(cos k_x + cos k_y) (for t′=0).
  - n=2: supercell of two sublattices (checkerboard), g(K) = [[0, ε_K],[ε_K, 0]], i.e. mixing k and k+(π,π).
  - n=4: 2×2 supercell with sites 1=(0,0), 2=(1,0), 3=(0,1), 4=(1,1),
    g(K) = [[0, ε_x, ε_y, ε′],[ε_x, 0, ε′, ε_y],[ε_y, ε′, 0, ε_x],[ε′, ε_y, ε_x, 0]],
    ε_x = −2t cos K_x, ε_y = −2t cos K_y, ε′ = −4t′ cos K_x cos K_y.
- All quantities are averages **per original lattice site**, at half filling (on average 1 electron per site). For t′=0, half filling corresponds to μ=U/2.

## Quantities to compute

1. **1D ground-state energy**: for n = 4, 6, 8, 10, 12, the ground-state energy per site E_n(U) at T=0 and half filling (i.e. ⟨kinetic + U Σ n↑n↓⟩/N, without the −μN term), U = 0.1, 1, 2, 3, 4, 5, 6, 7, 8.
2. **2D double occupancy**: at t′=0, half filling, inverse temperature β=100, D_n = (1/N) Σ_{K,α} ⟨n_{Kα↑} n_{Kα↓}⟩, n = 1, 2, 4, U = 0, 1, 2, 3, 4, 6, 8, 10, 12, 16, 20.
3. **2D antiferromagnetic susceptibility**: n=4, t′=0, half filling, static susceptibility S(Q, ω=0) = (1/N) Σ_{i,j} e^{iQ·(r_i−r_j)} ∫_0^β dτ ⟨S^z_i(τ) S^z_j(0)⟩, Q=(π,π), S^z_i = (n_i↑ − n_i↓)/2; U = 2, 4, 6, 8, 10, temperatures T = 0.1, 0.2, 0.48, 1.0.
4. **2D single-particle charge gap**: n=4, half filling, T=0, Δ = E(N+1) + E(N−1) − 2E(N) (the sum of the lowest energy costs of adding / removing one electron to / from the whole system in the thermodynamic limit), t′ = 0 and t′ = −0.25, U = 0.5, 1, 2, 3, 4, 6, 8. If there is no gap (metal), report 0.
5. **Mott critical interaction**: at n=4, half filling, T=0, the critical value U_c at which the gap opens, as a function of |t′|, for |t′| = 0.1, 0.2, …, 0.9 (the sign of t′ does not affect U_c).

## Given inputs

No external data; everything is numerical computation. You may use any open-source software or implement exact diagonalization yourself.

## Deliverables

Write CSV files under `outputs/` (comma-separated, first line is the header, decimal numbers):

| File | Columns | Rows |
|---|---|---|
| `energy_1d.csv` | n,U,value | the 45 combinations of item 1 |
| `double_occupancy.csv` | n,U,value | the 33 combinations of item 2 |
| `af_susceptibility.csv` | U,T,value | the 20 combinations of item 3 |
| `charge_gap_2d.csv` | tp,U,value | the 14 combinations of item 4 (tp is 0 or −0.25) |
| `uc_vs_tp.csv` | abs_tp,value | the 9 values of item 5 |

Also submit the code (`code/`) and run logs (`logs/`), and record a K-grid convergence check for each quantity in `logs/`.

## Acceptance

Each value is compared with a hidden reference value within a numerical tolerance; each file is one scoring target, and the task as a whole succeeds only if all targets pass. Searching online for the original paper or its data is forbidden.
