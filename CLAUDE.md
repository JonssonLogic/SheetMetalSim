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

`FixGeoAndMesh.py` runs two separate passes with two separate parameter files:

- **Tools** (rigid) — `tools_fine.ansa_mpar`, `mesh_type = General` at 3 mm with
  `general_curvature_minimum_length = 0.5` and fillet treatment on. Element quality and time step
  are irrelevant for rigid bodies and they cost nothing in the LS-DYNA time step, so the mesh is
  tuned purely for faithful radii. `Reconstruct`/`FixQuality` are deliberately **not** run on
  them, because moving nodes to satisfy quality criteria is exactly what pulls the mesh off the
  radii. This started as an STL mesh, which is the natural fit; ANSA's STL mesher produced zero
  elements under every invocation tried — see `docs/open-decisions.md`.
- **Blank** — `mesh_feature_parameters.ansa_mpar`, `mesh_type = General`, mixed quads at 4 mm.
  It needs quads for the `ELFORM 16` shells and the `ADPOPT=1` adaptive remeshing.

Both files set `orientation_definition = Fix` so the mesh inherits the geometry normals. Do not
change that — see below.

## The CAD carries no thickness offset — the contact does

The die and punch surfaces are **copies** of the blank surface, coincident with it. Nothing in
the geometry accounts for the sheet thickness, so `MST` on the contact card supplies it. It is
not an optional refinement: without it the tools sit inside the sheet from t = 0.

`v2025` builds its CAD with the offsets baked in, which is why that setup needs no `MST`. When
comparing the two, do not carry "the old one had no MST" across — they compensate for thickness
in different places.

Magnitude is blank thickness + 0.1, which assumes a shell's contact surface sits at half the
contact thickness off its mesh: 1.6 gives 0.80 mm against the blank's 0.75 mm half-thickness,
i.e. 0.05 mm clearance per side. See `MST_SIGN` in `CreateContacts.py` for why the sign is
positive despite the original note specifying a negative value.

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

## Working agreement (agreed 2026-08-31)

**Make changes in this project folder only.** Do not run `install.ps1`, and do not write to
`C:/Users/CV/Desktop/Forming_test/` or any other run directory, without asking first. State what
changed and wait. The user pushes when they are ready.

**Do not add code to make experimentation easier.** Only changes that belong in the finished tool.
Switches, knobs and diagnostic helpers added for a debugging session are scaffolding, not design —
if one is genuinely needed to make progress, say so and get agreement rather than slipping it in.

The exception currently in force: `CONTACT_TYPE` / `USE_MST` / `MST_SIGN` in `CreateContacts.py`
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
