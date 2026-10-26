# Recomputed recorded long-run results

These are observed generated implementations, not intrinsic language rankings. CPU includes parsing, file IO, startup/JIT and shutdown. RSS is process peak resident memory, not private/billable memory. Two scheduled repetitions per cell; resource_n excludes flagged process trees and ineligible programs.

| Language | Workload | CPU median s | CPU min–max s | RSS min–max MiB | Resource n |
|---|---|---:|---:|---:|---:|
| python | invoice | 1.063850 | 1.017846–1.109854 | 14.969–15.000 | 2 |
| python | access_log | 1.365721 | 1.327903–1.403540 | 15.094–15.125 | 2 |
| python | telemetry | 2.382737 | 2.355554–2.409919 | 14.438–14.844 | 2 |
| typescript | invoice | 0.543720 | 0.536424–0.551017 | 82.922–83.156 | 2 |
| typescript | access_log | 0.506628 | 0.500993–0.512262 | 83.172–83.609 | 2 |
| typescript | telemetry | 0.327475 | 0.325751–0.329200 | 65.219–65.422 | 2 |
| go | invoice | 1.051086 | 0.997489–1.104683 | 11.594–11.984 | 2 |
| go | access_log | 1.045473 | 0.992340–1.098607 | 11.156–12.062 | 2 |
| go | telemetry | 0.621630 | 0.563274–0.679987 | 5.516–6.000 | 2 |
| rust | invoice | 0.689346 | 0.637701–0.740992 | 2.562–2.562 | 2 |
| rust | access_log | 0.561276 | 0.560915–0.561638 | 2.422–2.438 | 2 |
| rust | telemetry | 0.386777 | 0.375681–0.397874 | 2.203–2.203 | 2 |
| swift | invoice | 1.710523 | 1.516481–1.904564 | 9.547–9.594 | 2 |
| swift | access_log | 1.633408 | 1.576597–1.690219 | 9.547–9.641 | 2 |
| swift | telemetry | 0.548178 | 0.507522–0.588834 | 9.094–9.141 | 2 |
| kotlin | invoice | 2.026669 | 1.699620–2.353719 | 292.938–307.141 | 2 |
| kotlin | access_log | 1.726807 | 1.667448–1.786166 | 297.047–312.578 | 2 |
| kotlin | telemetry | 1.021692 | 1.021692–1.021692 | 184.344–184.344 | 1 |
| moonbit | invoice | 1.201754 | 1.171139–1.232369 | 4.234–4.266 | 2 |
| moonbit | access_log | 1.781397 | 1.217722–2.345071 | 4.344–4.359 | 2 |
| moonbit | telemetry | 0.648086 | 0.620347–0.675825 | 3.641–3.656 | 2 |
| baml | invoice | 5.313233 | 5.313233–5.313233 | 88.516–88.516 | 1 |
| baml | access_log | 6.363197 | 5.996801–6.729593 | 95.094–100.781 | 2 |
| baml | telemetry | 2.088259 | 2.053814–2.122704 | 86.281–86.422 | 2 |
| zero | invoice | ineligible | ineligible | ineligible | 0 |
| zero | access_log | ineligible | ineligible | ineligible | 0 |
| zero | telemetry | ineligible | ineligible | ineligible | 0 |
