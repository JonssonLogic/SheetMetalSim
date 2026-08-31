# diagnose_step2.py
#
# TEMPORARY diagnostic for the step 2 problems (normals not consistent within a
# part, tools not getting an STL mesh).
#
# HOW TO RUN: open this file in ANSA's script editor (File > Open, or the Script
# editor's open button) and press F5. Do it on a model where you have just run
# step 1 (Open parts) - i.e. geometry imported and named, nothing meshed yet.
#
# Sections A-C are read-only. Section D MESHES the tools, so run it on a
# throwaway session. Copy the whole console output back.

import ansa
from ansa import base, constants, mesh

BLANK_NAME = "blank"


def _faces_of(pid):
    return base.CollectEntities(constants.LSDYNA, pid, "FACE", True)


def _bad_cons(pid):
    """Number of shared edges where the two adjacent faces disagree."""
    cons = base.CollectEntities(constants.LSDYNA, pid, "CONS", True)
    bad = 0
    for c in cons:
        try:
            if base.CheckAdjacentFacesOrientation(c) is False:
                bad += 1
        except Exception:
            pass
    return bad, len(cons)


def _tria_quad(pid):
    shells = base.CollectEntities(constants.LSDYNA, pid, "SHELL", True)
    tria = quad = unknown = 0
    for s in shells:
        try:
            v = base.GetEntityCardValues(constants.LSDYNA, s, ("N3", "N4"))
            n3, n4 = v.get("N3"), v.get("N4")
            if n4 in (0, None, "", "0") or n4 == n3:
                tria += 1
            else:
                quad += 1
        except Exception:
            unknown += 1
    return tria, quad, unknown, len(shells)


def main():
    pids = base.CollectEntities(constants.LSDYNA, None, "SECTION_SHELL", False)
    if not pids:
        print("No parts. Run '1. Open parts' first.")
        return
    blank = next((p for p in pids if p._name == BLANK_NAME), None)
    tools = [p for p in pids if p._name != BLANK_NAME]

    print("")
    print("=========== A. CAN WE COLLECT FACES VIA THE PROPERTY? ===========")
    all_faces = base.CollectEntities(constants.LSDYNA, None, "FACE", False)
    print("  faces in whole database        = %d" % len(all_faces))
    total_via_prop = 0
    for pid in pids:
        f = len(_faces_of(pid))
        total_via_prop += f
        print("  %-14s faces via property = %-6d shells = %d"
              % (pid._name, f, len(base.CollectEntities(constants.LSDYNA, pid, "SHELL", True))))
    print("  sum via property               = %d" % total_via_prop)
    if total_via_prop == 0 and len(all_faces) > 0:
        print("  >>> VERDICT: collecting FACE from a property returns NOTHING.")
        print("      That alone would disable both the orientation fix and the")
        print("      blank mesh pass.")
    else:
        print("  >>> VERDICT: property container works.")

    print("")
    print("=========== B. DOES base.Or(property) ISOLATE THE GEOMETRY? ===========")
    for pid in pids:
        base.Or(pid)
        vis = base.CollectEntities(constants.LSDYNA, None, "FACE",
                                   False, filter_visible=True)
        print("  base.Or(%-14s) -> visible faces = %d" % (pid._name, len(vis)))
    base.All()
    print("  (if these are 0 or equal to the whole-database count, base.Or is not")
    print("   scoping the way FixGeoAndMesh assumes - that would break CreateStlMesh)")

    print("")
    print("=========== C. ARE NORMALS CONSISTENT WITHIN EACH PART? ===========")
    print("  'bad' = shared edges where the two adjacent faces disagree")
    print("")
    print("  --- as imported ---")
    for pid in pids:
        bad, tot = _bad_cons(pid)
        print("  %-14s bad = %-5d of %d cons" % (pid._name, bad, tot))

    print("")
    print("  --- after base.AutoCalculateOrientation(all pids, True) ---")
    base.AutoCalculateOrientation(pids, True)
    for pid in pids:
        bad, tot = _bad_cons(pid)
        print("  %-14s bad = %-5d of %d cons" % (pid._name, bad, tot))

    print("")
    print("  --- after per-part base.Or + base.PerformGeomOrientation() ---")
    for pid in pids:
        base.Or(pid)
        base.PerformGeomOrientation()
    base.All()
    for pid in pids:
        bad, tot = _bad_cons(pid)
        print("  %-14s bad = %-5d of %d cons" % (pid._name, bad, tot))
    print("  >>> if this last block is all zeros, PerformGeomOrientation is the")
    print("      fix and AutoCalculateOrientation was never enough.")

    print("")
    print("=========== D. DOES CreateStlMesh ACTUALLY RUN? (destructive) ===========")
    if not tools:
        print("  no tools found")
        return
    tool = tools[0]
    print("  test part: %s" % tool._name)

    base.Or(tool)
    vis_before = len(base.CollectEntities(constants.LSDYNA, None, "FACE",
                                          False, filter_visible=True))
    print("  visible faces before meshing   = %d" % vis_before)

    import os
    from os.path import expanduser
    mpar = expanduser("~") + "/.BETA/ANSA/version_25.1.1/3D-teknik/tools_stl.ansa_mpar"
    print("  mpar exists                    = %s" % os.path.isfile(mpar))
    r = mesh.ReadMeshParams(mpar)
    print("  ReadMeshParams returned        = %r" % (r,))

    try:
        mesh.AspacingSTL(0.05, 4.0, 10.0, 0.5)
        print("  AspacingSTL                    = ok")
    except Exception as e:
        print("  AspacingSTL RAISED             = %r" % (e,))

    try:
        r = mesh.CreateStlMesh()
        print("  CreateStlMesh returned         = %r" % (r,))
    except Exception as e:
        print("  CreateStlMesh RAISED           = %r" % (e,))

    tria, quad, unk, tot = _tria_quad(tool)
    print("  RESULT on %-12s tria = %d  quad = %d  unknown = %d  total = %d"
          % (tool._name, tria, quad, unk, tot))
    if tot == 0:
        print("  >>> VERDICT: CreateStlMesh produced NO elements.")
    elif quad > tria:
        print("  >>> VERDICT: quad-dominant - this is NOT an STL mesh.")
    else:
        print("  >>> VERDICT: all/mostly trias - STL mesh worked here.")

    base.All()
    print("")
    print("=========== END - copy everything above back ===========")


if __name__ == '__main__':
    main()
