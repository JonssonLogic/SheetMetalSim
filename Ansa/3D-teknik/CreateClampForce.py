import ansa
from ansa import guitk
from ansa import constants
from ansa import base

BLANKHOLDER_NAME = "blankholder"

# The clamp force must act along the one translational DOF the blankholder is
# free to move in, and *MAT_RIGID CON1 says exactly which that is (CMO = 1,
# global constraints):
#     4 = x and y constrained  -> free in z
#     5 = y and z constrained  -> free in x
#     6 = z and x constrained  -> free in y
# 0 leaves everything free and 7 constrains everything, so neither identifies a
# single direction. forming_materials.k ships one rigid steel per case, named
# after it - RIGID_STEEL_47_z-free and so on.
FREE_DOF_BY_CON1 = {
	"4": "3: Fz",
	"5": "1: Fx",
	"6": "2: Fy",
}

DOF_CHOICES = ["1: Fx", "2: Fy", "3: Fz"]
DEFAULT_DOF = "3: Fz"


def _blankholder(pids):
	for pid in pids:
		if pid._name == BLANKHOLDER_NAME:
			return pid
	return None


def _material_of(pid):
	"""The material assigned to a property.

	CollectEntities will not walk from a property to its material unless
	mat_from_entities is set - its own docs say "otherwise None will be
	returned". Passing True positionally sets 'recursive' instead, which is
	what made this report "no material" on a correctly assigned blankholder.

	The MID fallback covers the case where that traversal still comes up empty.
	"""
	try:
		mats = base.CollectEntities(constants.LSDYNA, pid, "__MATERIALS__", True,
		                            mat_from_entities=True)
		if mats:
			return mats[0]
	except Exception:
		pass

	try:
		mid = base.GetEntityCardValues(constants.LSDYNA, pid, ("MID",)).get("MID")
	except Exception:
		mid = None
	if mid in (None, "", 0, "0"):
		return None
	try:
		mid = int(float(str(mid)))
	except (TypeError, ValueError):
		return None

	for mat in base.CollectEntities(constants.LSDYNA, None, "__MATERIALS__"):
		if getattr(mat, "_id", None) == mid:
			return mat
	return None


def _free_dof(pid):
	"""Which DOF the blankholder is free to move in, read from its material.

	Returns (dof, note). dof is None when the material cannot be read or does
	not pin down a single direction - the caller then falls back to Z and says
	so rather than pretending it detected something.
	"""
	if not pid:
		return None, "no part named '" + BLANKHOLDER_NAME + "'"

	mat = _material_of(pid)
	if not mat:
		return None, "could not find a material on the blankholder - is one assigned?"
	try:
		values = base.GetEntityCardValues(constants.LSDYNA, mat, ("CON1",))
		con1 = str(values.get("CON1", "")).strip()
	except Exception:
		return None, "could not read CON1 from the blankholder material"

	# ANSA may hand this back as "4", "4.0" or "4." depending on the card.
	key = con1.rstrip("0").rstrip(".") if "." in con1 else con1

	dof = FREE_DOF_BY_CON1.get(key)
	if dof:
		return dof, "from " + str(mat._name) + " (CON1 = " + con1 + ")"
	if key == "7":
		return None, str(mat._name) + " is fully constrained (CON1 = 7) - it cannot move"
	if key == "0":
		return None, str(mat._name) + " is unconstrained (CON1 = 0) - no single free direction"
	return None, str(mat._name) + " has CON1 = " + con1 + ", which leaves more than one axis free"


def clamp_force():

	pids = base.CollectEntities(constants.LSDYNA, None, "SECTION_SHELL", False)
	pid = _blankholder(pids)
	dof, note = _free_dof(pid)

	if dof:
		print("[OK] Blankholder is free in " + dof + " " + note)
	else:
		print("[ERROR] Could not detect the free direction: " + note)
		print("        Defaulting to " + DEFAULT_DOF + " - check it before continuing.")

	TopWindow = guitk.BCWindowCreate("Create clamping force", guitk.constants.BCOnExitDestroy)

	BCButtonGroup_1 = guitk.BCButtonGroupCreate(TopWindow, "Settings", guitk.constants.BCVertical)
	BCLabel_1 = guitk.BCLabelCreate(BCButtonGroup_1, "Force [N]:")
	BCLineEdit_1 = guitk.BCLineEditCreateDouble(BCButtonGroup_1, 200000.00000)
	BCLabel_2 = guitk.BCLabelCreate(BCButtonGroup_1, "Direction:")
	BCComboBox_1 = guitk.BCComboBoxCreate(BCButtonGroup_1, DOF_CHOICES)
	BCLabel_3 = guitk.BCLabelCreate(BCButtonGroup_1, note)
	BCSpacer_1 = guitk.BCSpacerCreate(BCButtonGroup_1)
	BCSpacer_2 = guitk.BCSpacerCreate(TopWindow)
	BCDialogButtonBox_1 = guitk.BCDialogButtonBoxCreate(TopWindow)

	# Pre-select the detected direction; the student can still override it.
	preset = dof if dof else DEFAULT_DOF
	if preset in DOF_CHOICES:
		guitk.BCComboBoxSetCurrentItem(BCComboBox_1, DOF_CHOICES.index(preset))

	guitk.BCWindowSetAcceptFunction(TopWindow, _ok_pressed, [BCLineEdit_1, BCComboBox_1])

	guitk.BCShow(TopWindow)


def _ok_pressed(w, data):

	pids = base.CollectEntities(constants.LSDYNA, None, "SECTION_SHELL", False)
	sf = guitk.BCLineEditGetDouble(data[0])
	dof = guitk.BCComboBoxCurrentText(data[1])
	force_name = "Clamp force - blankholder"
	curve_name = "Clamp force curve"

	pid = _blankholder(pids)
	if not pid:
		print("[ERROR] No part named '" + BLANKHOLDER_NAME + "'")
		return True

	force_curve = base.CreateLoadCurve("DEFINE_CURVE",{"Name": curve_name})
	base.SetLoadCurveData(force_curve, ((0.0, 0.0), (0.001, 1.0), (1, 1.0)))

	print("Curve OK!")

	load_properties = {"Name": force_name, "by": "rigid", "PID": pid._id, "DOF": dof, "LCID": force_curve._id, "SF": sf}
	new_load = base.CreateEntity(constants.LSDYNA, "LOAD", load_properties)

	if new_load:
		# Read the DOF back. The enum strings are ANSA's, not LS-DYNA's, and a
		# silently rejected one would give a load pushing the wrong way.
		try:
			written = base.GetEntityCardValues(constants.LSDYNA, new_load, ("DOF",)).get("DOF")
		except Exception:
			written = None
		print(f"Successfully created Load '{new_load._name}' in {dof} with SF = {sf}.")
		if written is not None and str(written) not in (dof, dof.split(":")[0].strip()):
			print("[ERROR] DOF read back as '" + str(written) + "', not '" + dof + "'.")
			print("        Check the load card before exporting.")
	else:
		print("Failed to create the Load.")

	return True


if __name__ == '__main__':
	clamp_force()
