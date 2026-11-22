# hazard/ (tier 4)

Hazard torture tests: programs whose output is wrong when a load-delay,
HI/LO, coprocessor or branch-delay hazard is mishandled
(see `docs/ps1/hazards.md` in the LLVM fork). Filled in by MIC-25.

| Test | Checks |
|---|---|
| `noreorder-old-value` | `lw; addu` in `.set noreorder` reads the old register value in the load delay slot; the same pair in reorder mode is padded and reads the new one (MIC-21). |
