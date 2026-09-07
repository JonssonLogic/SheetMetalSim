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
