# Solver settings that affect contact and forming behaviour

Reference for the `*CONTROL_*` cards in `explicit-main.k` and the contact card that
`CreateContacts.py` writes. Quoted text is LS-DYNA's own keyword manual, read from the copy ANSA
ships at `<ansa_install>/config/ANSA_CARDS_HELP/CARDS_HELP` (format: `K CARDNAME`, then
`F FIELDNAME`, then `+` lines).

Values are as of 2026-08-21, after the node-to-surface / STL / normals changes.

Items needing a decision are in [open-decisions.md](open-decisions.md).

---

## The contact chain

Five things have to agree for the forming contact to behave. Changing any one of them in
isolation is how this setup breaks.

```
tool shell normal points at blank        FixGeoAndMesh.orient_tools_towards_blank()
        │                                 (+ the gate in CreateContacts.py)
        ▼
*CONTROL_CONTACT SHLTHK = 2              thickness considered, rigid bodies included
        │                                 ← without this, MST is ignored entirely
        ▼
contact card MST = -(t_blank + 0.1)      explicit master standoff, offset along +normal
        │
        ▼
FORMING_NODES_TO_SURFACE                 only blank nodes checked → mid-span free to dip
        │
        ▼
PENCHK = 0, XPENE default 4.0            deliberate penetration is NOT punished by releasing
                                          the node from contact
```

---

## `*CONTROL_CONTACT`

| Field | Value | Meaning and relevance |
|---|---|---|
| `SLSFAC` | `.1` | *"Scale factor for sliding interface penalties. EQ.0: default = .1."* Explicit default; raise only if the blank visibly passes through a tool. |
| `ISLCHK` | `0` | *"EQ.0: the default is set to 1, EQ.1: **no checking**, EQ.2: full check of initial penetration."* So this is currently **no initial-penetration reporting**. Set to `2` temporarily when debugging a model that behaves oddly at t=0. |
| `SHLTHK` | `2` | *"Shell thickness considered in … surface to surface and node to surface … EQ.2: thickness is considered including rigid bodies."* **Load-bearing.** The tools are rigid, so `EQ.1` or `EQ.0` would make `MST` do nothing. |
| `PENOPT` | `0` → 1 | *"EQ.0: the default is set to 1 … **Options 4 and 5 are recommended for metalforming calculations.**"* See open decisions. |
| `THKCHG` | `0` | *"Shell thickness changes considered in **single surface** contact."* Ours are not single surface — inert here. Thinning is still handled by `ISTUPD` on `*CONTROL_SHELL`. |
| `ORIEN` | `0` → 1 | *"Optional automatic reorientation of contact interface segments during initialization. EQ.0: default is set to 1. EQ.1: active for automated (part) input only … EQ.3: inactive."* Our contacts are part-based, so **LS-DYNA reorients them regardless of what ANSA set.** See open decisions. |
| `XPENE` | `0.` → 4.0 | *"Contact surface maximum penetration check multiplier. If … PENCHK … is active, then nodes whose penetration exceeds the product of XPENE and the element thickness **are set free**."* Only bites when `PENCHK` is on. |
| `SSTHK` | `1` | *"Flag for using actual shell thickness in **single surface** contact logic-types 4, 13, 15 and 26 … (sometimes recommended for metal forming calculations)."* Our contact type is not in that list — inert, but harmless and conventional for forming decks. |
| `IGNORE` | `2` | *"Ignore initial penetrations in the `*CONTACT_AUTOMATIC` options … EQ.2: allow initial penetrations to exist by tracking … penetration warning messages are printed with the original coordinates and the recommended coordinates."* Ours are `FORMING_`, not `AUTOMATIC_`, so this may not apply; `IGNORE` can also be set **per interface** on the third optional `*CONTACT` card if it turns out to be needed. `implicit-main.k` uses `-2`. |
| `SHLEDG` | `0` | *"Flag for assuming edge shape for shells when measuring penetration. **This is available for segment based contact (see SOFT on `*CONTACT`)**. EQ.0: Shell edges are assumed round (default), EQ.1: square."* Round edges let a blank node roll off a tool edge instead of catching a square corner. **Caveat: our contacts do not set `SOFT`,** so they use the penalty formulation and this flag may be inert. See open decisions. |
| `PSTIFF` | `0` | Penalty stiffness based on element thickness/material rather than nodal mass. Default. |

---

## The contact card (`CreateContacts.py`)

Type: `*CONTACT_FORMING_NODES_TO_SURFACE`, slave = `blank` part, master = each tool part.

| Field | Value | Meaning and relevance |
|---|---|---|
| `FS`, `FD` | `0.125` | Static and dynamic Coulomb friction. Equal, so the exponential decay term is inactive regardless of `DC`. |
| `DC` | `0.0001` | *"Exponential decay coefficient. mc = FD + (FS − FD)·exp(−DC·|v_rel|)."* Does nothing while `FS == FD`. |
| `VDC` | `20` | *"Viscous damping coefficient in percent of critical. **In order to avoid undesirable oscillation in contact, e.g., for sheet forming simulation**, a contact damping perpendicular to the contacting surfaces is applied."* Correct and important for forming — do not drop it. |
| `MST` | `-(T1_blank + 0.1)` | *"Optional thickness for master surface (overrides true thickness)."* Set explicitly so the standoff is deliberate rather than inherited from whatever `T1` a student typed for each tool. Requires `SHLTHK ≥ 1`. |
| `SST` | *unset* | Blank keeps its true thickness. Deliberate. |
| `PENCHK` | `0` (off) | *"Small penetration in contact search option. If the slave node penetrates more than the segment thickness times the factor XPENE, **the penetration is ignored and the slave node is set free**."* **Keep this off.** The whole point of node-to-surface here is to let the blank sink slightly into the tool; turning `PENCHK` on would start releasing exactly those nodes. |
| `SOFT` | *unset* (0) | *"EQ.0: penalty formulation, EQ.1: soft constraint, EQ.2: pinball segment-based contact, **EQ.4: constraint approach for FORMING contact option**."* `EQ.2` is what would activate `SHLEDG`. `EQ.4` is forming-specific. Neither is currently used. |

---

## `*CONTROL_ADAPTIVE` — adaptive remeshing of the blank

Enabled per part: `SECTION_SHELL ADPOPT = 1` on `blank`, `0` on the tools
(`SetPropertyName.py`).

| Field | Value | Meaning and relevance |
|---|---|---|
| `ADPOPT` | `2` | *"EQ.2: total angle change in degrees relative to the surrounding element … if adptol=5 degrees, the element will be refined to the second level when the total angle change reaches 5 degrees."* |
| `ADPTOL` | `5.0` | The angle threshold above. |
| `ADPFREQ` | `0.0002475` | How often adaptivity is evaluated. `ENDTIM` is `0.01`, so ≈40 adaptive steps. |
| `MAXLVL` | `3` | Up to 3 levels of refinement — a 4 mm blank element can reach 0.5 mm. |
| `ADPENE` | `1.0` | *"Adapt the mesh when the contact surfaces approach or penetrate the tooling surface depending on whether the value … is positive (approach) or negative (penetrates). **The tooling adaptive refinement is based on the curvature of the tooling.**"* **Directly coupled to the STL tool mesh.** A finer tool mesh resolves tool curvature better, which changes where the blank gets refined. If blank element counts jump after the STL change, this is why. |
| `ADPTH` | `-0.5` | *"LT.0.0: Element thickness ratio. If the ratio of the element thickness to the original element thickness is less than the absolute value … the element will be refined."* Refines at 50% thinning. |
| `ADPASS` | `1` | One-pass adaptivity. The manual notes this is appropriate when `ADPENE` is positive, *"the refinement generally occurs before contact takes place; consequently, it is possible that the parameter ADPASS can be set to 1"* — consistent with `ADPENE = 1.0`. |
| `ORIENT` | `0` | **See open decisions — this one discards the tool normal orientation.** |

---

## Other cards that shape forming behaviour

| Card / field | Value | Meaning and relevance |
|---|---|---|
| `*CONTROL_SHELL` `ISTUPD` | `1` | *"EQ.1: membrane straining causes thickness change in 3 and 4 node shell elements. **This option is very important in sheet metal forming** or whenever membrane stretching is important."* Correct. This is what produces the thinning result META plots. |
| `*CONTROL_SHELL` `ESORT`, `IRNXX`, `BWC`, `PROJ` | `1`, `-1`, `1`, `1` | Automatic tria sorting, nodal fibre update, warping stiffness. Conventional forming settings. |
| `*CONTROL_RIGID` `METALF` | `1` | *"Metalforming option, which should not be used for crash … Use fast update of rigid body nodes. **If this option is active the rotational motion of all rigid bodies should be suppressed.**"* The prescribed motions are pure translation (`CreatePrescribedMotion.py` offers only X/Y/Z-tra), so this holds — but adding a rotational tool motion would violate it. |
| `*CONTROL_ENERGY` `SLNTEN` | `2` | *"Sliding interface energy dissipation … energy dissipation is computed and included in the energy balance. Reported in ASCII files GLSTAT and SLEOUT."* Required for the META energy-balance plot in `MetaImport.py`. |
| `*CONTROL_TIMESTEP` `DT2MS` | `-1.0E-6` | *"If negative, TSSFAC·|DT2MS| is the minimum time step size permitted and mass scaling is done if and only if it is necessary to meet the Courant time step size criterion."* With `TSSFAC = 0.9`, floor is 0.9 µs. Watch the added-mass plot in META. The STL tool mesh does **not** affect this — rigid bodies do not contribute to the time step — but a finer *blank* mesh would. |
| `*CONTROL_ACCURACY` `INN` | `4` | Invariant node numbering for shells and solids. Makes results independent of element node ordering. |
| `*CONTROL_HOURGLASS` `IHQ`/`QH` | `4` / `0.1` | Stiffness-form hourglass control. `ELFORM 16` is fully integrated, so hourglassing is not the main concern, but this covers any reduced-integration parts. |
| `SECTION_SHELL` `ELFORM`/`NIP` | `16` / `7` | Fully integrated shell, 7 integration points through thickness. Set in `SetPropertyName.py` and again in `OpenDynaIn.py`. `ELFORM 16` is **1st order** — that linear-element limitation is the whole reason for the node-to-surface contact. |

---

## Things worth watching after the 2026-08-21 changes

- **Blank element count.** `ADPENE` refines against tool curvature, and the tools are now much
  better resolved. More refinement is expected; a runaway is not.
- **Added mass.** Refinement drives element size down, `DT2MS` scales mass to compensate. The
  META added-mass plot is the check.
- **Sliding energy.** Should rise smoothly. Spikes at the die radius were the original symptom.
- **`d3hsp` initial penetration messages.** `ISLCHK = 0` means none are printed. Set it to `2`
  for one run if the blank starts out wrong.

## What added mass invalidates, and what it does not

Measured on runs 14 and 15, which differ only in `DT2MS`:

| | `-2.5E-7` | `-1.0E-6` |
|---|---|---|
| added mass | 47% | **1685%** |
| die reaction | 7.291e5 | 5.895e5 (**-19%**) |
| punch force | 5.289e5 | 3.891e5 (**-26%**) |
| runtime | 90 min | 25 min |
| energy ratio | 1.000000 | 1.000000 |
| ke/ie | 1.7e-4 | 1.6e-4 |

**Press forces are directly wrong.** A punch force read off a heavily
mass-scaled run understates the real one - here by a quarter. Never quote
`rcforc` from such a run for press sizing or tooling loads.

**Formability and springback are not safe either, though it is less obvious.**
The forces are not an independent output: they reflect how the material flows,
and strain, thinning and FLD position follow the same flow. A 26% force
difference is evidence that the deformation itself differs, not merely its
reported load.

The likely mechanism is that the blank's artificial inertia resists the
blankholder restraint, so material draws in more freely and the sheet stretches
less. That makes the **FLD optimistic** - the simulation looks safer than
reality. For a formability check that is the worst error direction, and the one
a student is least likely to question.

Springback inherits the same problem: the implicit run starts from the stress
state the forming run produced.

**What the standard diagnostics do NOT catch.** Energy ratio and ke/ie were
*identical* between the two runs - 1.000000 and ~1.6e-4. Neither detects mass
scaling, because the energy balance treats scaled mass as real. **`added mass`
in `glstat` is the only indicator.**

### Rule of thumb

| added mass | usable for |
|---|---|
| under ~10% | everything, including press forces |
| 10-50% | formability and springback; treat forces as indicative |
| over ~100% | qualitative behaviour and teaching the workflow only |
| over ~500% | nothing quantitative |

Run 14 sits at 47%, run 15 at 1685%.

**This is reasoning from the force difference, not a measurement of strain.** The
definitive test is to run both and compare the thinning field directly - worth
doing once if a fast configuration is wanted for teaching, since it would put a
number on how wrong "fast" actually is.
