# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Teaching macros for ANSA (pre) and META (post) that walk students through setting up a sheet
metal forming simulation for LS-DYNA, plus the springback pass that follows it. The point is that
students get correct pre-set values instead of having to know them.

There is **no build, no test suite, no package manager, and no version control**. The code only
runs inside ANSA's and META's embedded Python interpreters. "Running it" means clicking a button
in ANSA, or pressing F5 on a script in ANSA's script editor (every script has an
`if __name__ == '__main__'` guard for exactly that).

Target: ANSA / META **v25.1.1**, LS-DYNA (Student edition is installed at
`C:\Program Files\LS-DYNA Suite R16.1 Student`).

## Where the project is right now

**Last updated 2026-09-11.** Update this section when the situation changes; it is what a new
session reads first.

### Status

The ANSA setup pipeline works end to end and produces a forming model that solves cleanly in
LS-DYNA. Getting there took 15 solve runs and 9 meshing iterations over three weeks, all recorded
in `docs/test-log.md`. That log is the single most useful thing to read before changing anything
— it records what was tried, what failed, and several conclusions that were **wrong and later
retracted**.

The reference configuration is **run 14** (`docs/test-log.md`, "Run 14 is the new reference"):
normal termination, zero errors, exact force balance, 47% added mass, ~90 min.

### What is being worked on next

**A GUI addition for solve levels.** Two levels are decided but not built:

| Level | `DT2MS` | added mass | runtime | For |
|---|---|---|---|---|
| **Standard** | `-2.5E-7` | 47% | ~90 min | Real work. Formability and springback trustworthy; press forces indicative. |
| **Lecture** | `-1.0E-6` | 1685% | ~22 min | Demonstrating the workflow. Nothing quantitative. |

`DT2MS` lives in `explicit-main.k`, **not** in the ANSA model, so a level has to write a deck
field rather than set something in the database. `make_deck_variants.py` already generates named
deck variants by column address and is the obvious thing to build on.

Design decisions already made, in `docs/test-log.md` "Planned: two solve levels":

- The mesh is **not** part of the level. Only the time step differs.
- Punch stroke time stays a free student choice, defaulting to 0.1 s.
- A third "accurate" level (`-1.0E-7`, ~0% mass, ~3.7 h) is possible but deliberately not built.

### Open and unresolved

- **Validation on a second CAD model** is in progress. Both levels are calibrated on one part.
  The number that matters is added mass on Standard: near 47% means the levels generalise; far
  above means `DT2MS` cannot be a fixed per-level constant.
- **Sliding interface energy goes negative** from about t = 0.066, reaching -1.6e5 against an
  internal energy of ~5.9e5. It has survived a 4x finer blank, a 4x finer tool and a different
  tool mesher, so it is not discretisation. Unexplained, not destabilising anything.
- **Four solver settings** in `docs/open-decisions.md` have never been tested, two of them
  (`ORIENT`, `ORIEN`) load-bearing for tool orientation.
- **Scaffolding cleanup**: the switchable constants in `CreateContacts.py` are settled values
  now and were agreed to be hard-coded once the springback half is proven.

### What has NOT been touched

The springback and META post-processing halves of the pipeline. Everything above concerns the
forming setup only.

## How to document your work

The project has no version control, so these documents are the only record of why anything is the
way it is. Several settings here look arbitrary and are not; several obvious-looking changes have
already been tried and failed.

**Where things go:**

| File | Contents |
|---|---|
| `CLAUDE.md` | How the project works, and the "Where the project is right now" section above. Durable facts. |
| `docs/test-log.md` | Every run and meshing iteration, with settings and outcome. Also the change history for reverting. |
| `docs/solver-settings.md` | What each `*CONTROL_*` and contact field does, quoting the LS-DYNA manual. |
| `docs/open-decisions.md` | Settings that look wrong but have not been changed, with a recommendation. |

**Rules:**

1. **Log the attempt before the result.** Add the row when starting a run, not after. The point
   is to know afterwards which combination produced which outcome.
2. **Record failures and keep them.** Most of the value in `test-log.md` is what did not work.
   Deleting a failed attempt means someone repeats it.
3. **Retract wrong conclusions explicitly** rather than editing them away. Several entries are
   marked as superseded and say what replaced them. "ANSA's STL mesher produces zero elements"
   stood for two weeks and was wrong; it is left in place with the correction attached, because
   the reasoning that produced it is instructive.
4. **State what is measured and what is inferred.** If a number came from an output file, say so.
   If it is reasoning, say that instead. Inference has been wrong here repeatedly.
5. **Record the why, not just the what.** `MST = -(t + 0.1)` is meaningless without remark 10.
6. **Update the change history** in `docs/test-log.md` for anything that alters a setting —
   field address, old value, new value, reason. There is no other way to revert.
7. **Keep "Where the project is right now" current.** A stale status section is worse than none;
   two sections of this file had drifted into contradicting each other before 2026-09-11.

## Editing here does not change what runs

This is the single most important operational fact. Every script loads its siblings from a
hard-coded absolute path, so the copies under `Ansa/3D-teknik/` are **source**, not runtime:

| Source in this repo | Deployed to (what actually runs) |
|---|---|
| `Ansa/3D-teknik/` | `~/.BETA/ANSA/version_25.1.1/3D-teknik/` |
| `Ansa/Translators/` | `~/.BETA/Translators/` |
| `Ansa/ANSA_TRANSL.py` | `<ansa_install>/ansa_v25.1.1/config/` |
| `Ansa/ANSA.xml`, `ANSA.defaults`, `launcher.txt` | `~/.BETA/ANSA/version_25.1.1/` |
| `Meta/3D-teknik/` | `~/.BETA/META/version_25.1.1/3D-teknik/` |
| `Meta/default/` | `~/.BETA/META/version_25.1.1/default/` |

**Use `install.ps1` - never copy by hand, and never edit the deployed copies.**

```powershell
.\install.ps1 -DryRun     # show what would happen, change nothing
.\install.ps1 -Backup     # install, keeping a timestamped copy of what it replaces
.\install.ps1             # install
```

It hash-verifies every file afterwards and fails loudly if anything did not land.
Close ANSA and META first: both rewrite `ANSA.xml` / `ANSA.defaults` on exit and
will silently undo an install done while they were open. The script warns if it
sees them running.

`ANSA_TRANSL.py` goes to the install's `config/` folder, **not** `scripts/` -
despite what the comment at the top of that file says.

`version_25.1.1` is hard-coded in ~15 places (`ANSA_TRANSL.py` once per button,
`FixGeoAndMesh.py`, both `.ses` triggers). An ANSA upgrade silently breaks every button.

## The part-name contract

`SetPropertyName.py` constrains part names to a fixed list, and that list is the de facto API
between every script in the project:

```python
CVals_3 = ["blank", "die", "blankholder", "punch1", "punch2"]
```

Downstream code matches these as **bare string literals**:

- `"blank"` — everything keys off it. It is the contact slave, the springback set, the only part
  with `ADPOPT=1` adaptive remeshing, the only part whose thickness the student is asked for, and
  the reference the tool normals are aimed at.
- `"blankholder"` — `CreateClampForce.py` applies the clamp force to this name and nothing else.
  It reads `CON1` off the part's `*MAT_RIGID` to work out which translational DOF is free
  (4 → Z, 5 → X, 6 → Y) and pre-selects that direction, so `forming_materials.k`'s
  `RIGID_STEEL_47_z-free` family is load-bearing, not just descriptive naming.
- `"die"` — excluded from the prescribed-motion combo along with `blank`.
- Everything that is not `"blank"` is treated as a **tool** (rigid, STL-meshed, contact master).

Renaming a part in the dialog without updating the consumers breaks them silently. `punch2` is
offered in the combo and would get a contact and a motion, but no clamp force.

## Two-deck architecture: where solver behaviour lives

ANSA is configured **not** to emit `*CONTROL_*` cards (`Ls-Dyna Output All CONTROL Keywords =
false` in `ANSA.defaults`). So the model and the solver settings are split:

- `Ansa/3D-teknik/OutputToLSDyna.py` exports **only the model** — parts, mesh, materials,
  contacts, loads.
- `explicit-main.k` / `implicit-main.k` are **hand-maintained master decks** at the repo root.
  They hold every `*CONTROL_*`, `*DATABASE_*`, and `*INTERFACE_SPRINGBACK_LSDYNA` card and pull
  the model in with `*INCLUDE model.k`.

Consequence: **model setup changes go in the Python; solver behaviour changes go in the `.k`
decks.** They are edited by completely different means and neither knows about the other.

The decks use fixed 10-character right-justified fields. Verify an edit by column, not by eye:

```bash
awk 'NR==34{printf "[%s] len=%d\n", substr($0,1,10), length($0)}' explicit-main.k
```

See `docs/` for what the individual solver settings do and which ones interact with the contacts.

**Deck variants for A/B testing.** `make_deck_variants.py` generates
`explicit-main_<suffix>.k` from the base deck, each with its own `*TITLE` so the output files
say which deck produced them. Every run goes in `docs/test-log.md` — a run is defined by *two*
halves, the exported model (contact type and `MST`, from the constants at the top of
`CreateContacts.py`) and the deck (`*CONTROL_*`), so recording only one of them is not enough
to reproduce a result.

**The LS-DYNA R16 manuals are in `LS-Dyna_manuals/`** as both PDF and converted Markdown. The
Markdown is searchable and accurate, but PDF artifacts matter: words are hyphenated across line
breaks, spacing is doubled, and tables are flattened — so grep for a distinctive phrase rather
than a field name, and expect `SST`/`MST` to appear as **`SAST`/`SBST`** (R16 renamed
slave/master to SURFA/SURFB).

## The ANSA API is visibility-driven

Non-obvious and easy to get wrong. Several `ansa.mesh` / `ansa.base` functions take **no entity
argument at all** and silently act on whatever is currently visible:

- `mesh.Reconstruct()`, `mesh.FixQuality()`, `base.PerformGeomOrientation()`
- `base.InvertGeomOrientation()`

Scoping them means calling `base.Or(entities)` to isolate first, then `base.All()` to restore.
`FixGeoAndMesh.py` does this in a `try/finally` — that is what keeps `FixQuality` from wrecking
the tools' STL mesh. If you add code near these calls, check what is visible.

The full stub API with docstrings is on this machine and is the authoritative reference:

```
<ansa_install>/docs/extending/python_api/html/_downloads/autocomplete/py_dev/pydev_ansa/ansa/*.py
```

LS-DYNA's own keyword manual text, keyed by card and field, is also shipped:

```
<ansa_install>/config/ANSA_CARDS_HELP/CARDS_HELP     # "K CARDNAME" then "F FIELD" then "+ text"
```

where `<ansa_install>` is `C:/Users/CV/AppData/Local/Apps/BETA_CAE_Systems/ansa_v25.1.1`.

## Meshing: the blank and the tools are meshed differently

`FixGeoAndMesh.py` runs two passes with two parameter files, selected by `TOOLS_MPAR` and
`BLANK_MPAR`:

- **Tools** (rigid) — `tools_stl.ansa_mpar`. STL, graded by chordal deviation across the whole
  surface, so it needs no feature recognition and no radius or angle thresholds. The file is
  ANSA's own GUI output with **one** value changed: `stl_max_length = 8.` instead of `0.`.
  ANSA's `0.` means no upper limit, which left 70 mm slivers on the flats and crashed LS-DYNA's
  contact bucket sort. `Reconstruct`/`FixQuality` are deliberately **not** run on the tools —
  moving nodes to satisfy quality criteria is what pulls a mesh off the radii.
- **Blank** — `mesh_feature_parameters.ansa_mpar`, General, mixed quads at 2 mm. It needs quads
  for the `ELFORM 16` shells and the `ADPOPT=1` adaptive remeshing.

`tools_fine.ansa_mpar` is kept as a fallback: General at 2 mm with 4 element rows forced across
every fillet under 8 mm radius. It works, but depends on fillet recognition — a curved face that
is not recognised gets no refinement. Switching is one line in `TOOLS_MPAR`.

Both files set `orientation_definition = Fix` and `existing_mesh_treatment = Erase`. Do not
change either.

**Never hand-write `.ansa_mpar` values.** `rows_option = specific` appears in no shipped ANSA
file, and guessing `number` by analogy caused a syntax error that silently dropped everything
after that line. Set the value in ANSA's GUI, save the params, and copy what ANSA wrote.

## The CAD carries no thickness offset — the contact does

Die, blankholder and punch are built on the same surfaces as the blank, with no offsets: at full
stroke the punch coincides with the die exactly. Nothing in the geometry leaves room for the
sheet, so the contact has to create it. `MST` does that, and it is not optional — without it the
tools sit inside the sheet from t = 0.

`v2025` builds its CAD with the offsets baked in, which is why that setup needs no `MST` at all.
Do not carry "the old one had no MST" across — the two compensate in different places.

**`MST` must be NEGATIVE.** LS-DYNA R16 Vol I, `*CONTACT` General Remarks, remark 10: for
FORMING contacts the tooling-side thickness is *ignored*, and a negative `MST` offsets the tool
away from the blank by `|MST|/2` in the direction opposite its normal. **A positive value does
nothing at all** — two runs at `+1.6` and `+0.1` gave identical 3.9 MN contact forces at t=0
because neither applied any offset. Magnitude is blank thickness + 0.1, computed from the
blank's `T1` in `CreateContacts._master_thickness()`.

Because the offset direction is "opposite the SURFB normal", it depends on the tool normals step
2 sets. A tool oriented the wrong way is offset *into* the sheet.

## Shell normals are load-bearing

`*CONTACT_FORMING_*` is one-way and orientation-sensitive: a tool's normal must point **at the
blank**, or it projects its contact surface to the wrong side and the tools pass through the
sheet.

**In ANSA the yellow side is the side opposite the normal.** A correctly oriented tool therefore
shows its *grey* side to the blank. This cost a debugging round on 2026-08-27 — the blankholder
rule is stated in terms of yellow, so it inverts when translated to a normal direction.

`base.AutoCalculateOrientation()` only makes a part *self-consistent* — it does not aim it
anywhere, and it must be re-run **after** `CheckAndFixGeometry`, which rebuilds geometry and can
re-invert faces. Aiming is done by `FixGeoAndMesh.orient_tools_towards_blank()`, which votes face
normals against the blank's **plane normal** — not its centroid, because tool and blank surfaces
are often coincident and centroid vectors then collapse to noise. A tool whose every face lies in
the blank plane is inferred to sit opposite the most clearly offset tool. The `blankholder` is
a special case with its own rule — it is almost always coincident with the blank, so its
yellow side is aimed at `punch1` instead — which means its normal is aimed *away* from
`punch1`, since blankholder and punch sit on the same side of the sheet. Step 2 is the **only** place orientation is set or
checked. `CreateContacts.py` deliberately does not re-check it: contacts are part based
(`SSTYP`/`MSTYP` = `"3: Part id"`), so the cards reference parts rather than elements and need
neither a mesh nor correct normals to be created. An earlier version gated on it, which
duplicated these rules in a second file and blocked models that were fine.

Students never see normals: `show_shellnormal = false` in `ANSA.defaults`.

## Workflow

Buttons are declared with `@ansa.session.defbutton(group, label, tooltip)` in `ANSA_TRANSL.py`,
one group per phase. Ordering is enforced **only** by the number in the label — nothing stops a
student clicking 4 before 2. Each handler re-imports its script via `ansa.ImportCode` on every
click, so a redeployed script takes effect without restarting ANSA.

```
ANSA "Sheet metal forming"          1 Open parts → 2 Fix, mesh and check → 3 Import materials
                                  → 4 Create contacts → 5 Punch motion → 6 Clamp force
                                  → 7 Output .k-file
        ↓ model.k  +  explicit-main.k
LS-DYNA (explicit)  →  dynain
        ↓
ANSA "Spring back"                  1 Import forming results → 2 Import materials → 3 Output .k
        ↓ model.k  +  implicit-main.k
LS-DYNA (implicit)  →  dynain
        ↓
ANSA "Deformed shape"               1 Import springback shape
META                                MetaFormingTrigger.ses / MetaSpringbackTrigger.ses
```

`SET_SPRINGBACK` (SID 1) is created twice — once in `CreateContacts.py` for the forming pass and
again in `OpenDynaIn.py` for the springback pass. `*INTERFACE_SPRINGBACK_LSDYNA` in
`explicit-main.k` consumes `PSID = 1`.

`forming_materials.k` at the repo root is the file button 3 asks the student to pick.

## Conventions

- Console feedback uses `[OK]` / `[ERROR]` prefixes. Keep it — it is the only feedback a student
  gets, and several scripts have no other failure signal.
- Indentation is inconsistent across files: `CreateContacts.py`, `SetPropertyName.py`,
  `CreateClampForce.py` use **tabs**; `FixGeoAndMesh.py` uses **4 spaces**. Match the file you are
  editing rather than normalising it.
- Scripts are standalone — no shared module, no imports between them. Small duplication is
  preferred over introducing a shared import, because each is loaded independently by
  `ansa.ImportCode`.

## Checking work without ANSA

There is no test runner. What you can do offline:

```bash
# Syntax-check a script (the ansa module is unavailable outside ANSA, so parse rather than import)
python -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" Ansa/3D-teknik/CreateContacts.py

# Confirm a keyword field by column position in a deck
grep -n -A2 'CONTROL_CONTACT' explicit-main.k
```

## Known-good configuration

A full forming run terminated normally on 2026-09-02 with zero errors or warnings — the first
one that did. `docs/test-log.md` records the exact settings under "First working configuration",
along with the ten runs it took to get there and what each one ruled out.

Two things that took the longest to find, both worth knowing before changing anything:

- **`MST` must be negative.** `*CONTACT` General Remarks, remark 10: for FORMING contacts the
  tooling-side thickness is *ignored*, and a **negative** `MST` offsets the tool away from the
  blank by `|MST|/2` along the direction opposite its normal. A positive value does nothing at
  all. This is what compensates for CAD that carries no thickness offsets.
- **Sharp tool corners cannot be meshed around.** Refining the blank made the dimpling *worse*,
  not better — the signature of a geometric singularity. Fillets on the punch fixed it.

## Working agreement (agreed 2026-08-31)

**Make changes in this project folder only.** Do not run `install.ps1`, and do not write to
`C:/Users/CV/Desktop/Forming_test/` or any other run directory, without asking first. State what
changed and wait. The user pushes when they are ready.

**Do not add code to make experimentation easier.** Only changes that belong in the finished tool.
Switches, knobs and diagnostic helpers added for a debugging session are scaffolding, not design —
if one is genuinely needed to make progress, say so and get agreement rather than slipping it in.

The exception currently in force: `CONTACT_TYPE` / `USE_MST` / `TOOL_CLEARANCE` / `FRICTION` in `CreateContacts.py`
and `_clear_previous()` stay **only until a configuration runs cleanly in LS-DYNA**. Then they are
stripped in one pass and the winning values hard-coded with a comment saying why.

`v2025/` is read-only. See below.

## `../v2025/` is the reference baseline - never edit it

The sibling `v2025/` folder is the setup that ran acceptably in LS-DYNA. It is the control
against which every change here is judged, so treat it as **read-only**: never edit, deploy,
or regenerate anything in it. `docs/test-log.md` carries a table of every difference between
the two trees.

It holds no `.k` decks - those came from `C:\Users\CV\KallesDyna\` and only entered this
project on 2026-08-21, so the deck baseline is that original, not anything in `v2025`.

`v2025/` next to this folder is the previous snapshot — it was byte-identical to `v2026/` until
the 2026-08-21 contact and meshing changes, so `diff -rq ../v2025 .` is a usable stand-in for
"what changed since last year". `AnsaMeta automation.zip` is a zipped snapshot of the older tree.
