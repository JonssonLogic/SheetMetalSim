import ansa
from ansa import guitk, constants,base, mesh
from os.path import expanduser


SCRIPT_DIR = expanduser("~") + "\\.BETA\\ANSA\\version_25.1.1\\3D-teknik\\"
BLANK_NAME = "blank"

# The blankholder is almost always coincident with the blank, so the plane
# test below cannot resolve which side it is on. It has its own rule: its
# YELLOW side faces the punch.
#
# In ANSA the yellow side is the side OPPOSITE the normal. That is why the
# vote below aims the normal AWAY from the punch. It also matches how the
# contact thickness behaves: the normal points at the blank (the slave) while
# the thickness is drawn on the yellow side, away from it.
BLANKHOLDER_NAME = "blankholder"
PUNCH_REFERENCE = "punch1"

# Two tool meshing strategies are available. Switch by changing TOOLS_MPAR.
#
#   tools_stl.ansa_mpar   STL, graded by chordal deviation across the whole
#                         surface. No feature recognition, so no radius or angle
#                         threshold to tune - every curved face is refined on its
#                         own curvature. Values are ANSA's own, saved from the
#                         GUI. Currently selected.
#
#   tools_fine.ansa_mpar  General mesher, 2 mm flats with 4 element rows across
#                         every fillet under 8 mm radius. Works well, but depends
#                         on fillet recognition: a curved face that is not
#                         recognised gets no refinement.
#
# Do not coarsen the tools to match the blank. A coarser tool represents the
# tool less accurately, and since ADPENE refines the blank against *tooling
# curvature* it would also give less blank refinement - the opposite of helping
# the sheet follow a radius. If the blank cannot follow, raise MAXLVL (and drop
# DT2MS with it) instead.
TOOLS_MPAR = "tools_stl.ansa_mpar"
BLANK_MPAR = "mesh_feature_parameters.ansa_mpar"

# A tool whose furthest face is closer than this to the blank plane is
# treated as coincident with it, and its side cannot be determined from
# geometry. Real setups offset tools by at least a fraction of a mm.
COINCIDENT_TOL = 1.0e-3


# --- solve levels -----------------------------------------------------------
# Three numbers decide how long a run takes and how much of the result can be
# believed, and they pull against each other:
#
#   blank element size   the starting mesh
#   MAXLVL               how many times LS-DYNA may halve it. R16 Vol I: values
#                        of 1, 2, 3 allow 1, 4, 16 shells per original shell, so
#                        1 is no refinement, 2 is one halving, 3 is two.
#   DT2MS                the mass scaling floor
#
# Only the first of the three is an ANSA setting. MAXLVL and DT2MS are
# *CONTROL_* fields, and ANSA is configured not to emit those, so this step
# records them on the blank and step 7 writes them into the copy of
# explicit-main.k it puts beside the exported model.

# level -> (blank element size, MAXLVL, DT2MS)
LEVELS = {
    # 4 mm base and one refinement level, so 2 mm finest. A quarter of run 15's
    # blank elements at the same cycle count, which is where the speed comes
    # from - an estimated 14 minutes against run 15's measured 25. The saving is
    # not the full 4x because the rigid tool mesh does not shrink with the blank.
    #
    # It still scales mass: at a -1.0E-6 floor everything below 5.37 mm is
    # scaled, and 2 mm elements carry x13.4. That is four times better than run
    # 15's x56.7 but it is not zero, and it cannot be - with adaptivity on, the
    # refined elements are always below the floor. Lecture is explicitly not
    # quantitative, so this is a cost it is allowed to pay.
    #
    # 2 mm cannot resolve the punch's 1-3 mm fillets: the sheet crosses each one
    # in about 1.5 elements, so they form as a crease rather than a radius. Those
    # fillets only initiate contact with the blank, they do not shape it, which
    # is what makes the trade acceptable here and nowhere else.
    "Lecture":  (4.0, 2, "-1.0E-6"),
    # Run 14, the reference configuration.
    "Standard": (2.0, 2, "-2.5E-7"),
}
LEVEL_NAMES = ["Lecture", "Standard", "Custom"]
DEFAULT_LEVEL = "Standard"

LEVEL_NOTES = {
    "Lecture":  "Demonstrating the workflow. Nothing quantitative.",
    "Standard": "Real work. Formability and springback trustworthy,"
                " press forces indicative.",
    "Custom":   "Your own combination. Watch the mass factor below.",
}

MAXLVL_CHOICES = ["1", "2", "3"]
DT2MS_CHOICES = ["-1.0E-6", "-5.0E-7", "-2.5E-7", "-1.0E-7"]

# explicit.ansa_qual rejects shells under 0.35 mm and over 10 mm, and FixQuality
# enforces both on the blank. Stay well inside that.
MIN_BLANK_LENGTH = 1.0
MAX_BLANK_LENGTH = 8.0

# Plate wave speed of the blank, sqrt(E/(rho(1-nu^2))), and TSSFAC from
# *CONTROL_TIMESTEP. Mass is added to elements below L = c * |DT2MS|, which
# is 1.34 mm at -2.5E-7 and 5.37 mm at -1.0E-6.
#
# TSSFAC is NOT in that threshold: an element's step is TSSFAC * Lc / c and
# the floor is TSSFAC * |DT2MS|, so it cancels. It was in it until
# 2026-09-14, and the 1.16 mm that gave was never a measured figure despite
# the comment here having said so. TSSFAC is right in `cycles` below, where
# the step LS-DYNA actually takes is what matters. See open-decisions 7.
#
# Materials are not imported until step 3, so there is nothing to read the
# speed off here. One constant covers all three blanks in forming_materials.k
# to within 1.3%: 5.35e6 (STEEL_250_BH250), 5.37e6 (STEEL_420) and 5.44e6 mm/s
# (the aluminium). The old 5.17e6 was sqrt(E/rho) for the rigid tool steel -
# a bar speed, and the wrong material.
WAVE_SPEED = 5.37e6
TSSFAC = 0.9

# LS-DYNA adds twice what the arithmetic above predicts. Summed element by
# element over the real meshes it is a factor of two in all three cases
# measured, across a 370x range (added mass / blank mass):
#
#   first model, t=0, 2 mm unrefined, -1.0E-6   13.4 measured, 6.7 predicted
#   s_rail, t=0, 6 mm unrefined, -1.0E-6        0.036 measured, 0.018
#   s_rail, formed, end of run 18               3.66 measured, 1.84
#
# Why it is two is NOT known - d3hsp prints no per-element time step to check
# it against. This is a calibration, not a derivation. See open-decisions 7
# for the method and for the test that would explain it.
ADDED_MASS_CALIBRATION = 2.0

# Punch stroke time, for the cycle and runtime estimates only. The deck's ENDTIM
# is set at export from the actual motion curves, not from this.
NOMINAL_STROKE_TIME = 0.1

# Run 14: 444k cycles over 14,162 elements took 90 minutes. Runtime scales with
# cycle count and with element count, but only the blank's share of that count
# moves with the mesh size - the rigid tool mesh is identical at every level and
# is nearly half of it. Counting the tools matters: ignoring them predicts 6
# minutes for Lecture where including them predicts 14.
#
# Checked against run 15 - a 2 mm blank at -1.0E-6, measured 25 min - which this
# predicts as 23, so it is good to about 10% where there is anything to check it
# against. Coarser blanks than 2 mm are extrapolation.
REFERENCE_MINUTES = 90.0
REFERENCE_CYCLES = 444000.0
REFERENCE_LENGTH = 2.0
REFERENCE_TOOL_ELEMENTS = 6643.0     # run 14: die 2848 + blankholder 45 + punch1 3750
REFERENCE_BLANK_ELEMENTS = 7519.0    # the remainder of run 14's 14,162

# A mass factor on the finest element past this is worth saying out loud. Run 14
# sits at x2.6 and its forces are usable; run 15 sat at x56.7 and its were not.
#
# Kept at 5.0 when the formula was corrected (user, 2026-09-14), which means
# run 18's setting - 6 mm, MAXLVL 2, -1.0E-6, now x5.4 - starts warning. It
# carried 3.66x its own blank mass, which solver-settings.md calls qualitative
# only, so the warning is telling the truth even though that run looked fine.
MASS_FACTOR_WARNING = 5.0

# How step 7 finds out what was chosen here: user-defined attributes on the
# blank, which live inside the model and so need no file and no save.
#
# THE NAME YOU CREATE AN ATTRIBUTE WITH IS NOT THE KEY YOU SET IT BY.
# SetEntityCardValues wants the attribute's "Full Name", which ANSA forms as
# "User/<group>/<name>" - measured 2026-09-11. The bare name returns
# 'Field not found!'. ANSA's own attributes on this card, User/cad_material and
# User/cad_thickness, follow the same convention.
#
# _attribute_key reads the Full Name back off the attribute rather than
# assembling it, so a change to that convention cannot silently break this.
#
# FORMING_BLANK is carried alongside the two deck fields for two reasons: the
# dialog reopens on what is saved, which for Custom means restoring the blank
# size too, and step 7 puts all three numbers into *TITLE.
LEVEL_ATTRIBUTES = ("FORMING_LEVEL", "FORMING_BLANK", "FORMING_MAXLVL",
                    "FORMING_DT2MS")
ATTRIBUTE_GROUP = "Forming setup"

# One label per line of the readout, rewritten on every change.
READOUT_ROWS = 8


def _attribute_key(name):
    """The key SetEntityCardValues needs for one of our attributes, or None.

    CreateUserDefinedAttribute returns the existing attribute if it is already
    defined, so this is safe to call every time.
    """
    try:
        attr = base.CreateUserDefinedAttribute(
            deck=constants.LSDYNA, element_type="SECTION_SHELL", name=name,
            type="TEXT", default_value="", group_name=ATTRIBUTE_GROUP,
            read_only=False, accepted_values="")
        if attr is None:
            return None
        return base.GetEntityCardValues(constants.LSDYNA, attr,
                                        ("Full Name",)).get("Full Name")
    except Exception as e:
        print("[ERROR] Could not declare attribute '" + name + "': " + repr(e))
        return None


def _length_text(length):
    """A blank size as it is stored and shown: 4.0, 2.25, 3.125 - never 4.000."""
    text = ("%.3f" % length).rstrip("0")
    return text + "0" if text.endswith(".") else text


def _store_level(blank, level, length, maxlvl, dt2ms):
    """Record the level on the blank for step 7 to read back."""
    wanted = {"FORMING_LEVEL": level,
              "FORMING_BLANK": _length_text(length),
              "FORMING_MAXLVL": str(maxlvl),
              "FORMING_DT2MS": dt2ms}

    fields = {}
    for name, value in wanted.items():
        key = _attribute_key(name)
        if not key:
            print("[ERROR] Solve level not recorded - step 7 will fall back to "
                  + DEFAULT_LEVEL + ".")
            return
        fields[key] = value

    # All four in one call, because a single bad field makes ANSA discard the
    # whole set - its docs are explicit about that. REPORT_ALL so a rejection
    # says which field and why instead of failing mutely, which is exactly how
    # the first version of this went wrong.
    try:
        result = base.SetEntityCardValues(constants.LSDYNA, blank, fields,
                                          debug=constants.REPORT_ALL)
    except Exception as e:
        print("[ERROR] Could not store the solve level: " + repr(e))
        return

    code, problems = result if isinstance(result, tuple) else (result, {})
    if code != 0:
        print("[ERROR] Solve level not recorded - step 7 will fall back to "
              + DEFAULT_LEVEL + ".")
        for field, info in (problems or {}).items():
            print("        " + str(field) + ": " + str(info.get("message")))
        return

    print("[OK] Solve level '" + level + "': blank " + _length_text(length)
          + " mm, MAXLVL " + str(maxlvl) + ", DT2MS " + dt2ms)


def _read_level(blank):
    """The attributes as step 2 last wrote them, "" for any never set.

    None if an attribute could not be declared, which leaves nothing to read.
    """
    values = {}
    for name in LEVEL_ATTRIBUTES:
        key = _attribute_key(name)
        if not key:
            return None
        try:
            value = base.GetEntityCardValues(constants.LSDYNA, blank,
                                             (key,)).get(key)
        except Exception:
            value = None
        values[name] = "" if value is None else str(value).strip()
    return values


def _matching_choice(text, choices):
    """The entry in choices numerically equal to text, or None.

    Numeric rather than textual, so a "-1e-06" typed into ANSA's card still
    finds "-1.0E-6".
    """
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    for choice in choices:
        if abs(float(choice) - value) <= 1e-9 * abs(value):
            return choice
    return None


def _saved_choice(blank):
    """Where the dialog should start: what step 2 last recorded on this model.

    Returns (level, length, maxlvl, dt2ms), or None when nothing usable is
    saved, in which case the dialog opens on DEFAULT_LEVEL.
    """
    values = _read_level(blank)
    if not values or not values["FORMING_LEVEL"]:
        return None                     # step 2 has never run on this model

    level = values["FORMING_LEVEL"]
    maxlvl = _matching_choice(values["FORMING_MAXLVL"], MAXLVL_CHOICES)
    dt2ms = _matching_choice(values["FORMING_DT2MS"], DT2MS_CHOICES)
    if maxlvl is None or dt2ms is None:
        # Only reachable by editing the attributes in ANSA's card. Step 7 still
        # honours them; the dialog simply has no way to show them.
        print("[ERROR] The saved level (MAXLVL '" + values["FORMING_MAXLVL"]
              + "', DT2MS '" + values["FORMING_DT2MS"] + "') is not one this"
              " dialog offers.")
        print("        Starting from " + DEFAULT_LEVEL
              + " - pressing OK will replace what is saved.")
        return None

    if values["FORMING_BLANK"]:
        try:
            length = float(values["FORMING_BLANK"])
        except ValueError:
            length = None
        if length is None or not MIN_BLANK_LENGTH <= length <= MAX_BLANK_LENGTH:
            print("[ERROR] The saved blank size '" + values["FORMING_BLANK"]
                  + "' is not usable.")
            print("        Starting from " + DEFAULT_LEVEL
                  + " - pressing OK will replace what is saved.")
            return None
    elif level in LEVELS:
        length = LEVELS[level][0]
    else:
        # Set up before the blank size was carried (2026-09-14). The mesh size
        # cannot be recovered from the attributes, so say so rather than show a
        # default as though it had been saved.
        length = LEVELS[DEFAULT_LEVEL][0]
        print("[ERROR] This model's Custom level was saved without its blank"
              " size.")
        print("        The field shows " + _length_text(length) + " mm - set it"
              " to the size you want before pressing OK.")

    preset = LEVELS.get(level)
    if preset is None:
        level = "Custom"
    elif not (abs(preset[0] - length) <= 1e-9 * length
              and str(preset[1]) == maxlvl and preset[2] == dt2ms):
        # The preset has been redefined since this model was set up - Lecture
        # may well change after run 17. Show what the model was set up with,
        # not what the name means today.
        print("[OK] This model was set up as " + level + ", which has changed"
              " since. Its original values are shown as Custom.")
        level = "Custom"

    return level, length, int(maxlvl), dt2ms


def _mass_factor(unscaled, size):
    """What LS-DYNA multiplies an element's mass by at this size.

    Elements at or above `unscaled` are left alone. Below it, mass is added
    to bring the element's time step up to the floor, which is a square law
    on the size - times ADDED_MASS_CALIBRATION, see there.
    """
    if size >= unscaled:
        return 1.0
    return 1.0 + ADDED_MASS_CALIBRATION * ((unscaled / size) ** 2 - 1.0)


def _derived(length, maxlvl, dt2ms):
    """Everything the dialog reports, from the three chosen numbers."""
    finest = length / (2.0 ** (maxlvl - 1))
    unscaled = WAVE_SPEED * abs(float(dt2ms))
    factor = _mass_factor(unscaled, finest)
    cycles = NOMINAL_STROKE_TIME / (TSSFAC * abs(float(dt2ms)))
    elements = (REFERENCE_TOOL_ELEMENTS
                + REFERENCE_BLANK_ELEMENTS * (REFERENCE_LENGTH / length) ** 2)
    minutes = (REFERENCE_MINUTES * (cycles / REFERENCE_CYCLES) * elements
               / (REFERENCE_TOOL_ELEMENTS + REFERENCE_BLANK_ELEMENTS))
    return finest, unscaled, factor, cycles, minutes


def _readout(level, length, maxlvl, dt2ms):
    """The lines under the fields. Always READOUT_ROWS of them."""
    if not MIN_BLANK_LENGTH <= length <= MAX_BLANK_LENGTH:
        rows = ["Blank element size must be between %.1f and %.1f mm."
                % (MIN_BLANK_LENGTH, MAX_BLANK_LENGTH),
                "Outside that, ANSA's own quality criteria reject the mesh."]
        return rows + [""] * (READOUT_ROWS - len(rows))

    finest, unscaled, factor, cycles, minutes = _derived(length, maxlvl, dt2ms)

    # Measured where a run exists, estimated otherwise - they are not the same
    # kind of number and the student should be able to tell which is which.
    if level == "Standard":
        # Not "47% added mass" any more. That is glstat's share of the
        # WHOLE model, rigid tools included, and would read as a
        # contradiction beside the per-element factor above. Against its
        # own mass the reference blank carried 2.2x. See test-log,
        # "glstat's added-mass percentage includes the rigid tools".
        runtime = "~90 min (measured, run 14)"
    else:
        runtime = "~%d min (estimated)" % max(1, int(round(minutes)))

    rows = [
        "Finest element      %.2f mm" % finest,
        "No scaling above    %.2f mm" % unscaled,
        "Mass on finest el.  x%.1f" % factor,
        # The finest element is the worst case. The blank as a whole sits
        # between the factor at its starting size and that, depending on how
        # much of it refines - which depends on the geometry and cannot be
        # known here. Every run with measured numbers falls inside this
        # range, and above what the old formula called the worst case.
        "Blank mass          x%.1f to x%.1f"
        % (_mass_factor(unscaled, length), factor),
        "Cycles              %s" % format(int(round(cycles)), ","),
        "Runtime             " + runtime,
    ]
    if factor > MASS_FACTOR_WARNING:
        rows.append("")
        rows.append("WARNING: the finest elements carry %.0f times their real"
                    " mass. Forces from this run are not usable." % factor)
    return rows + [""] * (READOUT_ROWS - len(rows))


def _chosen(data):
    """The level and the three numbers currently shown in the dialog."""
    level = guitk.BCComboBoxCurrentText(data[0])
    length = guitk.BCLineEditGetDouble(data[1])
    maxlvl = int(guitk.BCComboBoxCurrentText(data[2]))
    dt2ms = guitk.BCComboBoxCurrentText(data[3])
    return level, length, maxlvl, dt2ms


def _refresh(data):
    """Rewrite the purpose line and the readout from the current fields."""
    level, length, maxlvl, dt2ms = _chosen(data)
    guitk.BCLabelSetText(data[4], LEVEL_NOTES.get(level, ""))
    for label, text in zip(data[5:], _readout(level, length, maxlvl, dt2ms)):
        guitk.BCLabelSetText(label, text)


def _level_changed(box, index, data):
    """Fill in a preset's values and lock the fields; Custom unlocks them.

    The preset writes its numbers into the visible fields rather than hiding
    them, so a student can see what Lecture and Standard actually are before
    switching to Custom and changing one.
    """
    preset = LEVELS.get(guitk.BCComboBoxCurrentText(box))
    if preset:
        length, maxlvl, dt2ms = preset
        # The typed setter, to match BCLineEditCreateDouble.
        guitk.BCLineEditSetDouble(data[1], length)
        guitk.BCComboBoxSetCurrentItem(data[2], MAXLVL_CHOICES.index(str(maxlvl)))
        guitk.BCComboBoxSetCurrentItem(data[3], DT2MS_CHOICES.index(dt2ms))
    for widget in (data[1], data[2], data[3]):
        guitk.BCSetEnabled(widget, preset is None)
    _refresh(data)
    return 0


def _field_changed(*args):
    """Any of the three fields changed.

    The argument lists differ between a combo box (box, index, data) and a line
    edit (edit, text, data); only the trailing data is wanted either way.
    """
    _refresh(args[-1])
    return 0


def _ok_pressed(w, data):
    level, length, maxlvl, dt2ms = _chosen(data)
    if not MIN_BLANK_LENGTH <= length <= MAX_BLANK_LENGTH:
        print("[ERROR] Blank element size must be between %.1f and %.1f mm"
              % (MIN_BLANK_LENGTH, MAX_BLANK_LENGTH))
        return False        # 0 leaves the dialog open
    _run(level, length, maxlvl, dt2ms)
    return True


def _faces_of(pid):
    """All geometry faces belonging to a property."""
    return base.CollectEntities(constants.LSDYNA, pid, "FACE", True)


def _part_centre(pid):
    """Average of a part's face centroids."""
    points = [c for c in (base.Cog(f) for f in _faces_of(pid)) if c]
    if not points:
        return None
    k = len(points)
    return tuple(sum(p[i] for p in points) / k for i in range(3))


def _unit(v):
    """Normalise a vector, or None if it has no length."""
    m = (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) ** 0.5
    if m == 0.0:
        return None
    return (v[0] / m, v[1] / m, v[2] / m)


def _blank_plane(blank):
    """Origin and unit normal of the blank.

    The blank is flat at setup time, and that makes its NORMAL a far better
    reference than its centroid. Tool surfaces frequently sit exactly on the
    blank - the flange of a die, or a blankholder face - and for those the
    centroid-to-centroid vector collapses to noise, which is precisely the
    case where getting the direction right matters most. A plane normal is a
    global direction and does not degrade when surfaces are coincident.
    """
    centres, normals = [], []
    for f in _faces_of(blank):
        c = base.Cog(f)
        n = base.GetFaceOrientation(f)
        if c and n:
            centres.append(c)
            normals.append(n)
    if not centres:
        return None, None
    k = len(centres)
    origin = tuple(sum(c[i] for c in centres) / k for i in range(3))
    normal = _unit(tuple(sum(n[i] for n in normals) / k for i in range(3)))
    return origin, normal


def _furthest_offset(faces, origin, normal):
    """Signed distance from the blank plane of the face furthest off it.

    The extreme, not the mean: a tool's flange region is often coincident with
    the blank while its walls and radii are not, and it is that off-plane
    geometry which reveals which side of the blank the tool sits on. Averaging
    would let a large coincident flange drown out the signal.
    """
    furthest = 0.0
    for f in faces:
        c = base.Cog(f)
        if not c:
            continue
        d = sum(normal[i] * (c[i] - origin[i]) for i in range(3))
        if abs(d) > abs(furthest):
            furthest = d
    return furthest


def _faces_point_along(faces, direction):
    """Majority vote: do these faces' normals point along 'direction'?

    The caller re-orients the part immediately before calling this, so the
    part is uniform and is either right or wrong as a whole - one vote, one
    decision. Voting over every face rather than testing one keeps a die with
    deep side walls from being decided by an unrepresentative facet.
    """
    score = 0
    for f in faces:
        normal = base.GetFaceOrientation(f)
        if not normal:
            continue
        score += 1 if sum(normal[i] * direction[i] for i in range(3)) > 0 else -1
    return score >= 0


def _inconsistent_edges(pid):
    """Shared edges where the two adjacent faces disagree on orientation.

    base.CheckAdjacentFacesOrientation returns True for single (red) and
    triple (blue) cons, so this only counts genuine double-cons mismatches.
    """
    bad = 0
    for c in base.CollectEntities(constants.LSDYNA, pid, "CONS", True):
        try:
            if base.CheckAdjacentFacesOrientation(c) is False:
                bad += 1
        except Exception:
            pass
    return bad


def orient_tools_towards_blank(blank, tools):
    """Aim every tool's shell normals at the blank.

    *CONTACT_FORMING_* is one-way and orientation-sensitive: the tool's
    a tool's normal must point AT the blank, so a tool whose normals face
    away projects its contact surface to the wrong side of itself and the
    tools pass straight through the sheet. (ANSA draws the yellow side
    opposite the normal, so a correctly oriented tool shows GREY to the
    blank.)

    Direction is decided against the blank's PLANE, not its centroid - see
    _blank_plane(). The rule is: a tool above the blank must point down, a
    tool below must point up.

    The blankholder is the exception. It is almost always coincident with the
    blank, so no test based on the blank can resolve it; instead its yellow
    side is aimed at the punch - which means its normal is aimed away from
    the punch.

    Runs on the geometry before meshing. Both mesh parameter files set
    orientation_definition = Fix, so the mesh inherits what is set here.
    """
    origin, normal = _blank_plane(blank)
    if not origin or not normal:
        print("[ERROR] Blank has no usable geometry - cannot orient tool normals")
        return

    # --- pass 1: make each tool uniform, and measure which side it is on ---
    measured = []
    for tool in tools:
        if not _faces_of(tool):
            print("[ERROR] No geometry found for '" + tool._name + "'")
            continue

        # Make this part internally consistent HERE, not earlier. The
        # AutoCalculateOrientation up in FixGeoMesh runs before
        # CheckAndFixGeometry, which rebuilds triple cons and needle faces and
        # can leave individual faces inverted again. Flipping a whole part
        # preserves whatever inconsistency it inherits, so the part has to be
        # made uniform immediately before the vote.
        base.Or(tool)                     # InvertGeomOrientation is visible-only
        base.AutoCalculateOrientation([tool], True)

        bad = _inconsistent_edges(tool)
        if bad:
            print("[ERROR] '" + tool._name + "' still has " + str(bad)
                  + " inconsistently oriented face edges after re-orienting.")
            print("        Its macros are probably not all connected. Fix the")
            print("        geometry, or invert the odd faces by hand in ANSA.")

        # Re-collect: CheckAndFixGeometry and the re-orient may have changed them.
        faces = _faces_of(tool)
        measured.append((tool, faces, _furthest_offset(faces, origin, normal)))

    # The most clearly offset tool - usually the die, whose cavity walls put it
    # far off the blank plane. Used as the reference for anything coincident.
    reference = 0.0
    for _, _, offset in measured:
        if abs(offset) > abs(reference):
            reference = offset

    # For the blankholder rule below.
    punch_centre = None
    for tool, _, _ in measured:
        if tool._name == PUNCH_REFERENCE:
            punch_centre = _part_centre(tool)
            break

    # --- pass 2: decide direction and flip ---
    for tool, faces, offset in measured:
        direction = None
        note = ""

        if tool._name == BLANKHOLDER_NAME and punch_centre:
            # The blankholder sits on the blank, so neither its own offset nor
            # the opposite-the-die inference is trustworthy for it. Its yellow
            # side faces the punch - a rule that holds regardless of how the
            # press is arranged, and that does not care about coincidence.
            #
            # Yellow is the side opposite the normal, so the normal is voted
            # AWAY from the punch. Physically consistent: blankholder and punch
            # sit on the same side of the sheet, so pointing the normal away
            # from the punch is what points it at the blank.
            here = _part_centre(tool)
            if here:
                direction = _unit(tuple(here[i] - punch_centre[i] for i in range(3)))
                note = "yellow side toward " + PUNCH_REFERENCE

        if direction is None:
            if abs(offset) >= COINCIDENT_TOL:
                above = offset > 0
                note = "sits %s the blank (%.2f mm)" % (
                    "above" if above else "below", offset)
            elif abs(reference) >= COINCIDENT_TOL:
                # Every face lies in the blank plane, so its own geometry cannot
                # say which side it is on. Tools sandwich the sheet, so assume it
                # sits opposite the most clearly offset tool.
                above = reference < 0
                note = ("lies in the blank plane, inferred %s it (opposite the"
                        " other tools)" % ("above" if above else "below"))
            else:
                print("[ERROR] '" + tool._name + "' lies in the blank plane and no"
                      " other tool is offset either -")
                print("        cannot tell which side it is on. Orient it by hand:"
                      " its normals must point at the blank.")
                continue

            # On the +normal side it must point back along -normal, and vice versa.
            sense = -1.0 if above else 1.0
            direction = tuple(sense * normal[i] for i in range(3))

        base.Or(tool)
        if _faces_point_along(faces, direction):
            print("[OK] '" + tool._name + "' " + note + ", normals already correct")
        else:
            base.InvertGeomOrientation()
            print("[OK] '" + tool._name + "' " + note + ", flipped normals")


def _enable_feature_treatment():
    """Turn on Feature Manager treatment application.

    ANSA.defaults ships with:

        always_ask_apply_treatment = true
        apply_treatmment           = false      (ANSA's own spelling)

    Recognition and treatment are separate. base.FeatureHandler().recognize()
    identifies the fillets - that part demonstrably works - but with
    apply_treatmment off the treatment defined in treatment_fillet is never
    applied, so rows_number has no effect and the fillets fall back to whatever
    the general curvature criterion produces (measured: 0.75 mm at a 2 mm
    target, i.e. 2-3 elements across a small fillet).

    Set at runtime rather than in ANSA.defaults because ANSA rewrites that file
    when it exits, which would silently undo it.
    """
    for key, value in (("apply_treatmment", "true"),
                       ("always_ask_apply_treatment", "false")):
        try:
            base.SetANSAdefaultsValues({key: value})
            back = base.GetANSAdefaultsValues((key,)).get(key)
            print("[OK] " + key + " = " + str(back))
        except Exception as e:
            print("[ERROR] could not set " + key + ": " + repr(e))


def _report_tool_mesh(tools):
    """Confirm the tools actually got a mesh.

    Worth checking explicitly: an earlier version of this pass used ANSA's STL
    mesher, which returned success and silently produced nothing at all. The
    tools looked fine in the model tree and were simply unmeshed.
    """
    for tool in tools:
        n = len(base.CollectEntities(constants.LSDYNA, tool, "SHELL", True))
        if n == 0:
            print("[ERROR] '" + tool._name + "' got NO mesh. Check that "
                  + TOOLS_MPAR + " is installed.")
        else:
            print("[OK] '" + tool._name + "' meshed: " + str(n) + " elements")


def FixGeoMesh():
    """Ask for a solve level, then fix, mesh and check.

    The parts are checked before the dialog opens, so a student who has not run
    step 1 is told that rather than being asked questions about a model that
    does not exist yet.
    """
    pids = base.CollectEntities(constants.LSDYNA, None, "SECTION_SHELL", False)
    if not pids:
        print("[ERROR] No parts, import geometry!")
        return
    if not any(p._name == BLANK_NAME for p in pids):
        print("[ERROR] No part named '" + BLANK_NAME
              + "' - run '1. Open parts' first")
        return

    TopWindow = guitk.BCWindowCreate("Fix, mesh and check",
                                     guitk.constants.BCOnExitDestroy)
    group = guitk.BCButtonGroupCreate(TopWindow, "Solve level",
                                      guitk.constants.BCVertical)

    guitk.BCLabelCreate(group, "Level:")
    level_box = guitk.BCComboBoxCreate(group, LEVEL_NAMES)
    purpose = guitk.BCLabelCreate(group, "")

    guitk.BCLabelCreate(group, "Blank element size [mm]:")
    length_edit = guitk.BCLineEditCreateDouble(group, LEVELS[DEFAULT_LEVEL][0])
    guitk.BCLabelCreate(group, "Adaptive levels (MAXLVL):")
    maxlvl_box = guitk.BCComboBoxCreate(group, MAXLVL_CHOICES)
    guitk.BCLabelCreate(group, "Mass scaling floor (DT2MS):")
    dt2ms_box = guitk.BCComboBoxCreate(group, DT2MS_CHOICES)

    guitk.BCLabelCreate(group, "")
    readout = [guitk.BCLabelCreate(group, "") for _ in range(READOUT_ROWS)]

    guitk.BCSpacerCreate(group)
    guitk.BCSpacerCreate(TopWindow)
    guitk.BCDialogButtonBoxCreate(TopWindow)

    data = [level_box, length_edit, maxlvl_box, dt2ms_box, purpose] + readout

    # Start from what this model already has, so opening step 2 again after a
    # Custom setup does not quietly put it back to Standard. The fields are
    # filled before any callback is attached, so filling them fires none.
    blank = next(p for p in pids if p._name == BLANK_NAME)
    saved = _saved_choice(blank)
    level = saved[0] if saved else DEFAULT_LEVEL
    if saved:
        _, length, maxlvl, dt2ms = saved
        guitk.BCLineEditSetDouble(length_edit, length)
        guitk.BCComboBoxSetCurrentItem(maxlvl_box,
                                       MAXLVL_CHOICES.index(str(maxlvl)))
        guitk.BCComboBoxSetCurrentItem(dt2ms_box, DT2MS_CHOICES.index(dt2ms))
        print("[OK] Starting from the level saved on this model: " + level
              + " (blank " + _length_text(length) + " mm, MAXLVL "
              + str(maxlvl) + ", DT2MS " + dt2ms + ")")

    guitk.BCComboBoxSetActivatedFunction(level_box, _level_changed, data)
    guitk.BCComboBoxSetActivatedFunction(maxlvl_box, _field_changed, data)
    guitk.BCComboBoxSetActivatedFunction(dt2ms_box, _field_changed, data)
    guitk.BCLineEditSetTextChangeFunction(length_edit, _field_changed, data)
    guitk.BCWindowSetAcceptFunction(TopWindow, _ok_pressed, data)

    # A preset fills in its values and locks the fields; Custom leaves the
    # saved values where they are and unlocks them.
    guitk.BCComboBoxSetCurrentItem(level_box, LEVEL_NAMES.index(level))
    _level_changed(level_box, LEVEL_NAMES.index(level), data)

    guitk.BCShow(TopWindow)


def _run(level, length, maxlvl, dt2ms):

    base.Topo()
    pids = base.CollectEntities(constants.LSDYNA, None, "SECTION_SHELL", False) 				# Select all pids

    if not pids:
        print("[ERROR] No parts, import geometry!")
        return

    blank = next((p for p in pids if p._name == BLANK_NAME), None)
    if not blank:
        print("[ERROR] No part named 'blank' - run '1. Open parts' first")
        return
    tools = [p for p in pids if p._name != BLANK_NAME]

    # Before meshing, so that a failure here is reported next to the mesh it
    # belongs with rather than half an hour later at export.
    _store_level(blank, level, length, maxlvl, dt2ms)

    base.AutoCalculateOrientation(pids, True) 													# Orient pids
    ret = base.CheckAndFixGeometry(pids, ["TRIPLE CONS", "NEEDLE FACE"], [1, 1], True, True)	# Geometry check and fix ([1,1] for two errors etc.)
    if ret != None: print("[OK] Geometry")
    else: print("[ERROR] Geometry")

    # base.Or() hides everything else, so restore the view whatever happens.
    try:
        # Aim the tools at the blank last, so nothing above can undo it.
        orient_tools_towards_blank(blank, tools)

        # Tools first. They are rigid, so element quality and time step are
        # irrelevant - only how faithfully the mesh follows the real radii
        # matters, and rigid bodies cost nothing in the LS-DYNA time step.
        #
        # Reconstruct and FixQuality are deliberately NOT run on the tools:
        # they move nodes to satisfy quality criteria, which is exactly what
        # pulls the mesh off the radii. (v2025 did run them here, because with
        # everything visible at once they could not be scoped to the blank.)
        if tools:
            base.Or(tools)
            mesh.ReadMeshParams(SCRIPT_DIR + TOOLS_MPAR)
            _enable_feature_treatment()
            # Feature recognition on the tools too. The General mesher only
            # applies fillet treatment to features that have been recognised,
            # and fillet treatment is how it resolves a tool radius.
            base.FeatureHandler(tools).recognize()
            tool_faces = []
            for tool in tools:
                tool_faces.extend(_faces_of(tool))
            mesh.Mesh(tool_faces)
            _report_tool_mesh(tools)

        # Then the blank, which does need quads - for the ELFORM 16 shells and
        # for the ADPOPT=1 adaptive remeshing. mesh.Reconstruct and
        # mesh.FixQuality act on whatever is visible, so isolating the blank
        # here is what keeps them off the tool mesh.
        base.Or(blank)
        mesh.ReadMeshParams(SCRIPT_DIR + BLANK_MPAR)
        # After ReadMeshParams, which would otherwise put target_element_length
        # straight back to the file's own value. Set through the API rather than
        # by editing the .ansa_mpar: hand-written values in those files have
        # silently dropped everything after the edited line before now.
        if mesh.SetMeshParamTargetLength("absolute", length) == 1:
            print("[OK] Blank element size " + ("%.1f" % length) + " mm")
        else:
            print("[ERROR] Could not set the blank element size - the mesh will"
                  " use " + BLANK_MPAR + "'s own value")
        # Feature recognition
        fh = base.FeatureHandler([blank])
        fh.recognize()

        # Read the criteria before meshing, not after - otherwise the first
        # pass runs on whatever happened to be loaded in the session.
        mesh.ReadQualityCriteria(SCRIPT_DIR + "explicit.ansa_qual")
        # Generate mesh
        blank_faces = _faces_of(blank)
        if blank_faces:
            mesh.Mesh(blank_faces)
            mesh.Reconstruct()
            mesh.FixQuality()
            print("[OK] Mesh on blank")
        else:
            print("[ERROR] Blank has no geometry to mesh")
    finally:
        base.All()

    # Intersection and penetration check
    ret_val = base.CheckIntersections(True, False, False)
    if ret_val != None: print("[OK] Intersections and penetrations")
    else: print("[ERROR] Intersections and penetrations")


if __name__ == '__main__':
    FixGeoMesh()
