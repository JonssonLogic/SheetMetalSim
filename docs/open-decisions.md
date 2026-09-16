# Open decisions

Settings found while implementing the 2026-08-21 contact changes that look wrong or worth
changing, but that were **not** changed because they sit outside what was asked for. Each is a
one-field edit in `explicit-main.k`. Item 7 is the exception: a script change, written up as a brief
for the session that implements it.

Field reference and current values: [solver-settings.md](solver-settings.md).

Status: items 1-4 open as of 2026-08-21; item 5 worked around 2026-08-26; item 6 fixed
2026-08-28. Items 1-4 have still not been tested in a solve. Item 7 decided 2026-09-14, not
implemented.

---

## 1. `*CONTROL_ADAPTIVE ORIENT = 0` discards the tool normal orientation

**Priority: high.** This one silently undoes work the ANSA side now does deliberately.

`explicit-main.k` line 75, field 7, columns 61–70. LS-DYNA manual, verbatim:

> This option applies to the FORMING contact option only. If this flag is set to one (1), **the
> user orientation for the contact interface is used.** If this flag is set to zero (0), LS-DYNA
> sets the global orientation of the contact surface the first time a potential contact is
> observed after the birth time. If slave nodes are found on both sides of the contact surface,
> the orientation is set based on the principle of "majority rules". **Experience has shown that
> this principle is not always reliable.**

`FixGeoAndMesh.orient_tools_towards_blank()` aims every tool's normals at the blank, and
`CreateContacts.py` refuses to build contacts if any tool is backwards. With `ORIENT = 0` the
solver throws that away and re-decides for itself, by a method its own manual calls unreliable.

**Recommendation: `ORIENT = 1`.**

```
$  ADPSIZE    ADPASS    IREFLG    ADPENE     ADPTH    MEMORY    ORIENT     MAXEL
       1.0         1         0       1.0      -0.5                   1         0
```

---

## 2. `*CONTROL_CONTACT ORIEN = 0` reorients the contact segments anyway

**Priority: high.** Same failure mode, different card.

`explicit-main.k` line 24, field 7, columns 61–70. Manual:

> Optional automatic reorientation of contact interface segments during initialization:
> EQ.0: default is set to 1. EQ.1: active for **automated (part) input only. Contact surfaces are
> given by `*PART` definitions.** EQ.2: active for manual (segment) and automated (part) input.
> EQ.3: inactive.

`CreateContacts.py` writes `SSTYP`/`MSTYP` = `"3: Part id"` — part-based input, exactly the case
`EQ.1` covers. `0` defaults to `1`, so reorientation is active today.

**Recommendation: `ORIEN = 3`** (inactive), so ANSA's orientation is authoritative.

Decide 1 and 2 together — they are the same question asked by two cards, and changing only one
leaves the other free to override.

**Evidence against `ORIEN = 3` as things stand (2026-09-14, run 18 — inferred, not tested).**
On s_rail the blankholder sits on the **die** side of the sheet: `matsum` shows it riding down with
`punch1` at the punch speed for the whole stroke, where on the first model it stays still. Step 2's
blankholder rule assumes the blankholder is on `punch1`'s side and aims its normal *away* from
`punch1` — which on s_rail points it away from the blank. `messag` agrees: Warning 40575 puts the
blank's nodes on the **negative** side of the blankholder segments on s_rail, and on the positive
side on the first model, while die and punch read positive on both. The run was unaffected (zero
force at t=0, clamp reaction exactly 200 kN), most likely because `ORIEN` is still at its default
and LS-DYNA reoriented the part-based segments itself. Setting `ORIEN = 3` now would make a
backwards blankholder authoritative on s_rail. ~~Fix the blankholder rule for both arrangements
first.~~ **Decided 2026-09-14 (user): the rule stays.** s_rail's die-side blankholder is intended, if
unusual, and the run was unaffected. The one consequence to keep in mind: if `ORIEN = 3` is ever
adopted, re-check a model laid out like s_rail. Details in `docs/test-log.md`, "Run 18".

**Superseded 2026-09-16: the rule was rewritten after all** (user's decision, on being shown that
the `punch1` assumption was in the way). Step 2 now decides every tool the same way — its own
off-plane geometry first, then opposite the `die`, then opposite the most clearly offset tool — so
a die-side blankholder with any depth places itself, and nothing depends on a part named exactly
`punch1` any more, which matters because punches are numbered now. This was not done to unblock
`ORIEN = 3`; it fell out of supporting several blankholders. **Measured on s_rail 2026-09-16:** its
blankholder now reports `sits below the blank (-1.00 mm)`, the same side as its die, and is
oriented correctly. So the specific evidence against `ORIEN = 3` above — that ANSA's own
orientation was backwards on s_rail — no longer holds. `ORIEN = 3` is still untested in LS-DYNA,
and the first model has not been re-run since the rewrite, so this is a removed objection rather
than a reason to adopt it.

---

## 3. `PENOPT = 0` ignores the manual's metalforming recommendation

**Priority: medium.** A tuning question, not a correctness bug.

`explicit-main.k` line 24, field 5, columns 41–50. Manual:

> Penalty stiffness value option. EQ.0: the default is set to 1. EQ.1: minimum of master segment
> and slave node (default for most contact types) … EQ.4: use slave node value, area or mass
> weighted. EQ.5: same as 4 but inversely proportional to the shell thickness.
> **Options 4 and 5 are recommended for metalforming calculations.**

Currently `0`, i.e. the generic default. `EQ.4` bases the penalty on the slave (blank) node rather
than the minimum of blank and tool, which is the sensible choice when the master is rigid.

**Recommendation: try `PENOPT = 4`,** but only after 1 and 2 are settled — changing penalty
stiffness and contact orientation in the same run makes the result impossible to attribute. The
manual explicitly does not recommend `EQ.5` generally (*"may require special scaling"*).

---

## 4. `SHLEDG = 0` may be inert without `SOFT = 2`

**Priority: low — worth knowing, probably not worth acting on.**

`SHLEDG` was changed from `1` to `0` on 2026-08-21 as requested. The value is right: round edges
let a blank node roll off a tool edge instead of catching a square corner. But the manual qualifies
it:

> Flag for assuming edge shape for shells when measuring penetration. **This is available for
> segment based contact (see SOFT on `*CONTACT`).**

`CreateContacts.py` does not set `SOFT`, so the contacts use the plain penalty formulation
(`SOFT = 0`), not segment-based (`SOFT = 2`). `SHLEDG` may therefore have no effect on this model
as it stands.

Nothing is broken either way — `0` is the LS-DYNA default and the correct value if segment-based
contact is ever switched on. Two ways to close this out:

- Leave it. It is correct and costs nothing.
- Or, if edge catching actually shows up in results, set `SOFT = 2` on the contacts in
  `CreateContacts.py` to make `SHLEDG` bite. Note `SOFT = 4` also exists and is
  forming-specific (*"constraint approach for FORMING contact option"*).

---

## 5. ANSA's STL mesher produces zero elements (closed - worked around)

**Status: worked around on 2026-08-26. Reopen only if BETA explains it.**

The tool surfaces were meant to be STL-meshed: chordal-deviation driven, so the
mesh hugs die and punch radii instead of chording across them. ANSA's STL mesher
produced **zero elements** on these macros under every invocation tried.

Measured on `die` (91 faces, 287 cons), each variant clearing the mesh first:

| Variant | Result |
|---|---|
| `AspacingSTL` + `mesh.Mesh` | 0 elements |
| force `mesh_type = STL` via `SetANSAdefaultsValues` + `mesh.Mesh` | 0 elements |
| enable `stl_generator` + `mesh_type = STL` + `mesh.Mesh` | 0 elements |
| `InitPerimeters` + `AspacingSTL` + `CreateStlMesh` | 0 elements |
| `stl_generator` + `InitPerimeters` + `CreateStlMesh` | 0 elements |

Things ruled out along the way, all confirmed working:

- `ReadMeshParams` returns 1 **and** the session `mesh_type` really does become
  `'STL'` afterwards.
- `SetANSAdefaultsValues({"stl_generator": "true, 11"})` returns 0 (success) and
  reads back correctly, so the generator flags are valid and writable.
- `base.Or(<property>)` correctly isolates the 91 faces, so the visible-only
  functions had something to work on.
- The same macros mesh fine with `mesh_type = General`.

No error, no exception, no warning - `CreateStlMesh()` returns 0, which its own
docs say it does "in all cases", so the return value carries no information.

**Workaround in place:** `tools_fine.ansa_mpar` uses the General mesher tuned
hard for curvature (3 mm target, `general_curvature_minimum_length = 0.5`,
fillet treatment on, CONS distortion 5%). This meets the actual requirement -
faithful radii - and costs only element count, which is nearly free on rigid
bodies since they do not contribute to the LS-DYNA time step.

**If you ask BETA:** the question is why `mesh.CreateStlMesh()` silently
produces no elements on visible, topologically clean macros with `mesh_type =
STL` and `stl_generator` enabled, in ANSA 25.1.1. `diagnose_stl.py` at the
project root reproduces it.

---

## 6. Mass scaling was the real cause of the first error termination (fixed)

**Status: fixed on 2026-08-28. Not yet confirmed by a clean run.**

First LS-DYNA run died at t = 4.14e-3 of 0.02 with `*** Error 40024 termination
due to mass increase`, preceded by ~50 `Warning 40045 plasticity algorithm did
not converge for MAT36` and followed by `Error 40500 out-of-range velocities`
reaching 1e81. The contacts were not at fault - the cards were written
correctly (`FORMING_NODES_TO_SURFACE`, `MST = -1.6`), all three interfaces
engaged, and `rcforc` shows stable forces to the end (interface 1 reacting
~2.0e5 N against the 200 kN clamp).

`glstat` added mass over time: **84% at cycle 1**, 737%, 860%, 928%.

The arithmetic:

- `DT2MS = -1.0E-6` with `TSSFAC = 0.9` set a floor of dt = 9.0e-7 s.
- Steel here: E = 210000, rho = 7.85e-9, so c = sqrt(E/rho) = 5.17e6 mm/s.
- dt = L/c, so that floor needs elements >= 9.0e-7 x 5.17e6 = **4.65 mm**.
- The blank starts at 4 mm - already under, hence 84% before anything moves.
- `MAXLVL = 3` took it to ~0.5 mm, where the factor is (9.0e-7/9.7e-8)^2 = **86x**.

**Corrected 2026-09-14 (see item 7).** Two of those lines are wrong in exactly the way the
step 2 dialog was: 5.17e6 is the rigid tool steel's bar speed, not the blank's plate speed,
and `TSSFAC` does not belong in the threshold. Per the blank the threshold is
`5.37e6 × 1.0e-6` = **5.37 mm**, so the 4 mm blank was further under it than stated, and at
0.5 mm the factor is **x230** with the empirical calibration applied, not 86x. The diagnosis
and the fix are unchanged — if anything the case is stronger.

A blank carrying 9x its real mass is inertia-dominated; strain increments per
cycle go extreme, Barlat stops converging, and it goes unstable.

**Fix applied:** `DT2MS` -1.0E-6 -> **-2.5E-7** (line 16, field 5) and
`MAXLVL` 3 -> **2** (line 73, field 4). The two meet in the middle: the blank
now refines to 1 mm, where dt = 1.9e-7 against a floor of 2.25e-7, so about
~~1.4x~~ **x2.6** on the finest elements instead of ~~86x~~ **x230** (2026-09-14). Expect roughly 3-4x the runtime.

`ENDMAS` deliberately left at 0 (no limit).

**Note for next time:** adaptivity itself was well behaved (684 -> 4470
elements, MAXLVL respected). But `ADPENE = 1.0` refines the blank against
*tooling curvature*, and the tool mesh was made much finer on 2026-08-26, so
blank refinement is likely more aggressive now than it used to be. If mass
climbs again, that coupling is where to look - `tools_fine.ansa_mpar` and
`MAXLVL` pull against each other.

---

## 7. The step 2 dialog underestimates added mass (implementation brief)

**Status: implemented 2026-09-14**, as written below. Both calls the brief reserved for the
user were answered that day: `MASS_FACTOR_WARNING` stays at **5.0**, so run 18's setting now
warns, and the **blank-mass range row was added**. The brief is kept for the record, and for
the factor-of-two test under "Not part of this change", which is still open.

This is a script change in `FixGeoAndMesh.py`, not a deck field. The
measurements behind it are in `docs/test-log.md`, "The step 2 dialog underestimates added mass
about 3x" and "`glstat`'s added-mass percentage includes the rigid tools".

### Why

The step 2 dialog tells the student how much mass LS-DYNA will add, and warns when forces will not
be usable. It is the only place a student sees the cost of a Custom choice before committing to a
run. Checked against LS-DYNA's own output on both CAD models, it reports between a third and a half
of the real value — optimistic, in exactly the direction a student will not question.

`_derived()` computes it as

```python
unscaled = WAVE_SPEED * TSSFAC * abs(float(dt2ms))    # WAVE_SPEED = 5.17e6
factor = (unscaled / finest) ** 2 if finest < unscaled else 1.0
```

and `_readout()` shows `unscaled` as "No scaling above" and `factor` as "Mass on finest el.",
warning above `MASS_FACTOR_WARNING = 5.0`. Three things are wrong with it:

1. **The wave speed is the tool steel's bar speed.** 5.17e6 mm/s is `sqrt(E/rho)` for E = 210000,
   rho = 7.85e-9 — the `*MAT_RIGID` cards, not any blank. A shell's time step uses the plate speed
   `sqrt(E/(rho(1-nu^2)))`. For the three blank materials in `forming_materials.k` that is 5.35e6
   (`STEEL_250_BH250`), 5.37e6 (`STEEL_420`) and 5.44e6 mm/s (aluminium). One constant of 5.37e6 is
   within 1.3% of all three, so step 2 still needs no material — which matters, because materials
   are not imported until step 3.
2. **`TSSFAC` does not belong in the threshold.** An element's step is `TSSFAC × Lc / c` and the
   floor is `TSSFAC × abs(DT2MS)`, so `TSSFAC` cancels: mass is added to elements with
   `Lc < c × abs(DT2MS)`. That is 5.37 mm at `-1.0E-6` and 1.34 mm at `-2.5E-7`, not 4.65 and 1.16.
   `TSSFAC` is right where `cycles` uses it — the step LS-DYNA takes is `TSSFAC × abs(DT2MS)`,
   measured 9.0e-7 at `-1.0E-6`.
3. **LS-DYNA adds twice what the formula gives, even with 1 and 2 fixed.** Summed element by element
   over the real meshes, the corrected formula predicts exactly half of what `glstat` reports, in
   all three cases measured, across a 370x range:

| case | measured | current formula | 1 and 2 fixed | 1 and 2 fixed, x2 |
|---|---|---|---|---|
| first model, t=0 — 2 mm, unrefined, `-1.0E-6` | **13.4** | 4.8 | 6.7 | **13.4** |
| s_rail, t=0 — 6 mm, unrefined, `-1.0E-6` | **0.036** | 0.002 | 0.018 | **0.036** |
| s_rail, end of run 18 — the formed mesh | **3.66** | 1.20 | 1.84 | **3.69** |

All as added mass ÷ blank mass. Measured: `glstat`'s absolute added mass ÷ the blank's mass in
`d3hsp` "summary of mass". Predicted: per element over `forming.k` (t=0) or `dynain` (formed),
area-weighted, with `Lc` = area ÷ longest side. That is `ISDO = 0` per ANSA's `CARDS_HELP`
("area/(minimum of the longest side or the longest diagonal)"), which is the longest side for any
convex quad.

**Why the factor is two is not known.** `d3hsp` prints no per-element time step to check it against.
Implement it as a named empirical constant, say so in its comment, and quote the three measurements.

### The change

All in `Ansa/3D-teknik/FixGeoAndMesh.py` (4-space indentation):

| what | now | change to |
|---|---|---|
| `WAVE_SPEED` | `5.17e6`, commented as the steel's `sqrt(E/rho)` | `5.37e6`, commented as the blank materials' plate speed, with the three values above |
| new constant beside it | — | `ADDED_MASS_CALIBRATION = 2.0`, commented as empirical: the table above, cause unknown |
| `unscaled` in `_derived()` | `WAVE_SPEED * TSSFAC * abs(float(dt2ms))` | `WAVE_SPEED * abs(float(dt2ms))` |
| `factor` in `_derived()` | `(unscaled / finest) ** 2` | `1.0 + ADDED_MASS_CALIBRATION * ((unscaled / finest) ** 2 - 1.0)`, still 1.0 when `finest >= unscaled` |
| `cycles` in `_derived()` | uses `TSSFAC` | **unchanged** |
| Standard's runtime text in `_readout()` | `"~90 min, 47% added mass (measured, run 14)"` | `"~90 min (measured, run 14)"` — the 47% is `glstat`'s share of the whole model and would sit beside "x2.6" looking like a contradiction |
| comments | `LEVELS` (4.65 mm, x5.4, x21.7); the `WAVE_SPEED` block ("1.16 mm, which is the measured figure in the test log" — it never was measured); `MASS_FACTOR_WARNING` (1.4, 21.6) | the new figures below |

`MASS_FACTOR_WARNING = 5.0` can stay: it still falls between run 14 (forces usable, now x2.6) and
run 15 (not usable, now x56.7). But run 18's setting — 6 mm, `MAXLVL 2`, `-1.0E-6` — moves from x2.4
to x5.4 and **will start warning**. Ask the user whether that is wanted before touching the
threshold either way.

Expected readouts afterwards. Check these first:

| setting | finest | "No scaling above", now → after | "Mass on finest el.", now → after |
|---|---|---|---|
| Standard — 2 mm, `MAXLVL 2`, `-2.5E-7` | 1.00 mm | 1.16 → **1.34** mm | x1.4 → **x2.6** |
| Lecture — 4 mm, `MAXLVL 2`, `-1.0E-6` | 2.00 mm | 4.65 → **5.37** mm | x5.4 → **x13.4** |
| run 18 — 6 mm, `MAXLVL 2`, `-1.0E-6` | 3.00 mm | 4.65 → **5.37** mm | x2.4 → **x5.4** |
| run 15 — 2 mm, `MAXLVL 2`, `-1.0E-6` | 1.00 mm | 4.65 → **5.37** mm | x21.7 → **x56.7** |
| 2 mm, `MAXLVL 3`, `-1.0E-7` | 0.50 mm | 0.47 → **0.54** mm | x1.0 → **x1.3** |

**Optional, recommended: show a range, not just the finest element.** The finest element's factor is
meant to be the worst case, but the blank as a whole carries something between the factor at its
starting size and the factor at the finest, depending on how much of it refines — which depends on
the geometry and cannot be known in step 2. Every run with numbers falls inside that range under the
new formula, and above the current formula's supposed worst case:

| run | whole-blank mass multiplier, from output | current "finest" | new: starting size → finest |
|---|---|---|---|
| 14 | 2.2 *(masses inferred from run 15)* | x1.4 | x1.0 → x2.6 |
| 15 | 43.8 | x21.7 | x13.4 → x56.7 |
| 16 | 42.0 *(masses inferred from run 18)* | x21.7 | x13.4 → x56.7 |
| 18 | 4.7 | x2.4 | x1.0 → x5.4 |

A row such as `Blank mass          x1.0 to x5.4` would say that honestly. The readout is padded to a
fixed `READOUT_ROWS`; raise it if a row is added.

### Check it without ANSA

Stub the `ansa` package as CLAUDE.md describes under "Checking work without ANSA", import
`FixGeoAndMesh`, and call `_derived()` and `_readout()` for the five settings in the readout table.
Then syntax-check the file with `ast.parse`. Nothing here needs ANSA or LS-DYNA.

### Documents to update in the same pass

The old figures are quoted in many places. Per the documentation rules, add a correction beside each
rather than rewriting it:

- `docs/test-log.md`: the change history (constant, old value, new value, why); the run table rows
  for runs 15 and 17; "What we know" (≥ 4.65 mm); "Refinement vs mass vs runtime" (+35%, +442%);
  run 15's section (`-5.0E-7` as a compromise at x1.4 / x5.4); "Planned: revisit DT2MS" (the
  threshold and factor table); "Solve levels — built 2026-09-11" (its mass column already carries a
  2026-09-14 correction — update it to the implemented figures); "Retracted 2026-09-11: the mesh is
  not part of the level" (4.65 mm, x5.4, x21.7); "A third level" (~0% added mass and x1.0 at
  `-1.0E-7`, now x1.3).
- `docs/open-decisions.md`: item 6's arithmetic (4.65 mm, 86x) and this item's status.
- `make_deck_variants.py`: the `+442%` comment.
- `CLAUDE.md`: the "Open and unresolved" bullet, and the solve-level table if it gains a mass column.

The rule of thumb in `docs/solver-settings.md` also needs restating per blank mass, but that is a
separate open item — a judgement about thresholds, not arithmetic.

### Not part of this change

- **If the user wants the factor of two explained rather than calibrated,** the cheapest test is a
  single flat 2 mm quad and a 4 x 4 patch of them: `ELFORM 16`, t = 1.0, `STEEL_420`,
  `DT2MS -1.0E-6`, no contact, a few cycles. The corrected formula without the two says 6.2x added.
  If `glstat` says 12.4x for both, the two is a constant; if the single element and the patch
  differ, it comes from how mass is shared between nodes (a guess). That is an LS-DYNA run for the
  user with a throwaway deck, not tool code — ask first.
- **The runtime estimate has the same kind of problem and is out of scope.** It is calibrated on the
  first model's 6643 tool elements. s_rail's tools are 9992, and run 16 took 70 min where the
  formula gives 22 for the same settings. Using the real tool element count would need the tools to
  be meshed before the dialog opens. Record it; do not fix it in the same pass.

---

## Not a solver setting, but open

**`ANSA_TRANSL.py` header comment is wrong.** It says the file belongs in
`<ansa_install>/scripts/`. It actually deploys to `<ansa_install>/config/`, which is where
`install.ps1` puts it and where the working copy has always been. Worth correcting the comment
so the next person does not go looking in the wrong place, as happened on 2026-08-26.
