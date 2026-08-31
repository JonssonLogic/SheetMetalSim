# Open decisions

Settings found while implementing the 2026-08-21 contact changes that look wrong or worth
changing, but that were **not** changed because they sit outside what was asked for. Each is a
one-field edit in `explicit-main.k`.

Field reference and current values: [solver-settings.md](solver-settings.md).

Status: items 1-4 open as of 2026-08-21; item 5 worked around 2026-08-26; item 6 fixed
2026-08-28. Items 1-4 have still not been tested in a solve.

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

A blank carrying 9x its real mass is inertia-dominated; strain increments per
cycle go extreme, Barlat stops converging, and it goes unstable.

**Fix applied:** `DT2MS` -1.0E-6 -> **-2.5E-7** (line 16, field 5) and
`MAXLVL` 3 -> **2** (line 73, field 4). The two meet in the middle: the blank
now refines to 1 mm, where dt = 1.9e-7 against a floor of 2.25e-7, so about
1.4x on the finest elements instead of 86x. Expect roughly 3-4x the runtime.

`ENDMAS` deliberately left at 0 (no limit).

**Note for next time:** adaptivity itself was well behaved (684 -> 4470
elements, MAXLVL respected). But `ADPENE = 1.0` refines the blank against
*tooling curvature*, and the tool mesh was made much finer on 2026-08-26, so
blank refinement is likely more aggressive now than it used to be. If mass
climbs again, that coupling is where to look - `tools_fine.ansa_mpar` and
`MAXLVL` pull against each other.

---

## Not a solver setting, but open

**`ANSA_TRANSL.py` header comment is wrong.** It says the file belongs in
`<ansa_install>/scripts/`. It actually deploys to `<ansa_install>/config/`, which is where
`install.ps1` puts it and where the working copy has always been. Worth correcting the comment
so the next person does not go looking in the wrong place, as happened on 2026-08-26.
