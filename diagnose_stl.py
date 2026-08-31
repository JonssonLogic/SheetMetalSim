# diagnose_stl.py  (v2)
#
# TEMPORARY. Finds which call sequence actually produces an STL (all-tria) mesh
# on a tool surface.
#
# v1 was invalid: it called mesh.Reset() between variants, which without
# reset_level_option set does a deeper reset than "erase mesh" and left the
# macros unmeshable. Every variant reported 0 elements, including the one we
# already knew produces quads. This version clears the mesh by deleting shells.
#
# It also checks the thing v1 never did: whether ReadMeshParams actually
# switches the session mesh_type to STL. If it does not, that alone explains
# why mesh.Mesh() keeps producing quads.
#
# HOW TO RUN: open in ANSA's script editor, press F5, on a model where you have
# just run step 1 (Open parts). Meshes repeatedly - use a throwaway session.

import ansa
from ansa import base, constants, mesh
from os.path import expanduser

BLANK_NAME = "blank"
MPAR = expanduser("~") + "/.BETA/ANSA/version_25.1.1/3D-teknik/tools_stl.ansa_mpar"
SPACING = (0.05, 4.0, 10.0, 0.5)   # chordal dev, max len, feature angle, min len


def _faces_of(pid):
    return base.CollectEntities(constants.LSDYNA, pid, "FACE", True)


def _cons_of(pid):
    return base.CollectEntities(constants.LSDYNA, pid, "CONS", True)


def _defaults(key):
    try:
        return base.GetANSAdefaultsValues((key,)).get(key)
    except Exception as e:
        return "unreadable (%r)" % (e,)


def _count(pid):
    tria = quad = 0
    for sh in base.CollectEntities(constants.LSDYNA, pid, "SHELL", True):
        try:
            v = base.GetEntityCardValues(constants.LSDYNA, sh, ("N3", "N4"))
            n3, n4 = v.get("N3"), v.get("N4")
        except Exception:
            continue
        if n4 in (0, None, "", "0") or n4 == n3:
            tria += 1
        else:
            quad += 1
    return tria, quad


def _verdict(tria, quad):
    if tria + quad == 0:
        return "NO ELEMENTS"
    if quad > tria:
        return "quad dominant - NOT stl"
    if quad == 0:
        return "*** ALL TRIA - THIS IS THE ANSWER ***"
    return "tria dominant - probably stl"


def _clear_mesh(pid):
    """Delete the shells. NOT mesh.Reset() - see header."""
    shells = base.CollectEntities(constants.LSDYNA, pid, "SHELL", True)
    if shells:
        try:
            base.DeleteEntity(shells, force=True, compress=False)
        except Exception as e:
            print("      (clear raised %r)" % (e,))


def _run(name, pid, fn):
    print("")
    print("  --- %s ---" % name)
    _clear_mesh(pid)
    print("      shells after clear   = %d" % sum(_count(pid)))
    base.Or(pid)
    try:
        r = mesh.ReadMeshParams(MPAR)
        print("      ReadMeshParams -> %r, session mesh_type now = %r"
              % (r, _defaults("mesh_type")))
    except Exception as e:
        print("      ReadMeshParams raised %r" % (e,))
    try:
        fn(pid)
    except Exception as e:
        print("      RAISED %r" % (e,))
    tria, quad = _count(pid)
    print("      tria = %-7d quad = %-7d  %s" % (tria, quad, _verdict(tria, quad)))


def _set(key, value):
    try:
        r = base.SetANSAdefaultsValues({key: value})
        print("      set %s = %r -> %r (0 = success), reads back %r"
              % (key, value, r, _defaults(key)))
    except Exception as e:
        print("      set %s raised %r" % (key, e))


# ---------------------------------------------------------------- variants
def v1_plain_mesh(pid):
    """Today's code. Known to give quads when step 2 runs it."""
    mesh.AspacingSTL(*SPACING)
    mesh.Mesh(_faces_of(pid))


def v2_force_mesh_type(pid):
    """Theory: ReadMeshParams does not push mesh_type into the session."""
    _set("mesh_type", "STL")
    mesh.AspacingSTL(*SPACING)
    mesh.Mesh(_faces_of(pid))


def v3_enable_generator(pid):
    """Theory: mesh.Mesh only picks among ENABLED generators.

    ANSA.defaults ships stl_generator = 'false, 11' while adv_fr_generator is
    'true, 4'. If the mesher chooses among enabled generators only, STL can
    never win regardless of mesh_type.
    """
    _set("stl_generator", "true, 11")
    _set("mesh_type", "STL")
    mesh.AspacingSTL(*SPACING)
    mesh.Mesh(_faces_of(pid))


def v4_initperims_createstl(pid):
    """Theory: CreateStlMesh is only the final step and needs perimeters."""
    mesh.InitPerimeters(_cons_of(pid), remesh_macros=False,
                        initialize_number=True, initialize_spacing=True,
                        use_ansa_defaults_values=False)
    mesh.AspacingSTL(*SPACING)
    mesh.CreateStlMesh()


def v5_generator_plus_createstl(pid):
    """Both: generator enabled AND perimeters initialised, then CreateStlMesh."""
    _set("stl_generator", "true, 11")
    mesh.InitPerimeters(_cons_of(pid), remesh_macros=False,
                        initialize_number=True, initialize_spacing=True,
                        use_ansa_defaults_values=False)
    mesh.AspacingSTL(*SPACING)
    mesh.CreateStlMesh()


def main():
    pids = base.CollectEntities(constants.LSDYNA, None, "SECTION_SHELL", False)
    tools = [p for p in pids if p._name != BLANK_NAME]
    if not tools:
        print("No tools found. Run '1. Open parts' first.")
        return
    pid = tools[0]

    print("")
    print("=========== STL VARIANT TEST v2 on '%s' ===========" % pid._name)
    print("  faces = %d   cons = %d" % (len(_faces_of(pid)), len(_cons_of(pid))))
    print("  mesh_type before anything = %r" % _defaults("mesh_type"))

    _run("V1  AspacingSTL + mesh.Mesh            (today's code)", pid, v1_plain_mesh)
    _run("V2  force mesh_type=STL + mesh.Mesh", pid, v2_force_mesh_type)
    _run("V3  enable stl_generator + mesh.Mesh", pid, v3_enable_generator)
    _run("V4  InitPerimeters + CreateStlMesh", pid, v4_initperims_createstl)
    _run("V5  stl_generator + InitPerimeters + CreateStlMesh", pid, v5_generator_plus_createstl)

    base.All()
    print("")
    print("=========== END - copy everything above back ===========")


if __name__ == '__main__':
    main()
