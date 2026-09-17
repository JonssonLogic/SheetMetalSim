import ansa
from ansa import guitk
from ansa import constants
from ansa import base
import re

# A model can hold several blankholders - blankholder1, blankholder2, ... -
# and each is a rigid part of its own, so each needs its own clamp force: two
# rigid parts are not tied together in LS-DYNA, and one left without a force is
# free to move away in the direction it is not constrained in. A plain
# "blankholder" from a model set up before the numbering matches as well.
BLANKHOLDER_PATTERN = re.compile(r"^blankholder\d*$")

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

FORCE_PREFIX = "Clamp force - "


def _blankholders():
	"""Every blankholder in the model, in name order.

	Name order rather than collection order, so the dialog lists blankholder1
	before blankholder2 whatever order they were imported in.
	"""
	pids = base.CollectEntities(constants.LSDYNA, None, "SECTION_SHELL", False)
	found = [pid for pid in pids if BLANKHOLDER_PATTERN.match(str(pid._name))]
	return sorted(found, key=lambda pid: str(pid._name))


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
	"""Which DOF this blankholder is free to move in, read from its material.

	Returns (dof, note). dof is None when the material cannot be read or does
	not pin down a single direction - the caller then falls back to Z and says
	so rather than pretending it detected something.

	Read per blankholder, not once for the model: each one carries its own
	material, and two of them can be free in different directions.
	"""
	if not pid:
		return None, "no blankholder selected"

	mat = _material_of(pid)
	if not mat:
		return None, "could not find a material on " + str(pid._name) + " - is one assigned?"
	try:
		values = base.GetEntityCardValues(constants.LSDYNA, mat, ("CON1",))
		con1 = str(values.get("CON1", "")).strip()
	except Exception:
		return None, "could not read CON1 from " + str(mat._name)

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


def _report(pid, dof, note):
	if dof:
		print("[OK] " + str(pid._name) + " is free in " + dof + " " + note)
	else:
		print("[ERROR] Could not detect the free direction: " + note)
		print("        Defaulting to " + DEFAULT_DOF + " - check it before continuing.")


def _select_dof(dof_box, dof):
	preset = dof if dof else DEFAULT_DOF
	if preset in DOF_CHOICES:
		guitk.BCComboBoxSetCurrentItem(dof_box, DOF_CHOICES.index(preset))


def _message(text):
	"""A message the student cannot miss.

	The console is the only feedback most steps give, and students do not look
	at it - a refusal has to stop them at the dialog they just pressed OK on.
	Always in ADDITION to the console line, never instead of it.
	"""
	try:
		window = guitk.BCMessageWindowCreate(guitk.constants.BCMessageBoxWarning,
		                                     text, True)
		guitk.BCMessageWindowExecute(window)
	except Exception:
		pass		# the console line above it still carries the message


def _typed_number(line_edit):
	"""Read a number from a dialog field, whichever decimal separator was used.

	BCLineEditGetDouble returns guitk.constants.blank - a sentinel, not a
	number - when the field does not hold a valid double, and a sentinel here
	would become the clamp force rather than an error. The class also runs on
	Swedish Windows, where the decimal separator is a comma, so "2000,5" can
	reach us as text that float() will not take. Both separators are accepted.

	Returns None when the field holds nothing usable.
	"""
	try:
		value = guitk.BCLineEditGetDouble(line_edit)
	except Exception:
		value = None

	if value is not None and value != guitk.constants.blank:
		try:
			return float(value)
		except (TypeError, ValueError):
			pass

	try:
		text = guitk.BCLineEditGetText(line_edit).strip()
	except Exception:
		return None
	if not text:
		return None
	try:
		return float(text.replace(",", "."))
	except ValueError:
		return None


def clamp_force():

	holders = _blankholders()

	if not holders:
		print("[ERROR] No part named 'blankholder' - run '1. Open parts' first")
		return

	dof, note = _free_dof(holders[0])
	_report(holders[0], dof, note)

	TopWindow = guitk.BCWindowCreate("Create clamping force", guitk.constants.BCOnExitDestroy)

	BCButtonGroup_1 = guitk.BCButtonGroupCreate(TopWindow, "Settings", guitk.constants.BCVertical)
	BCLabel_0 = guitk.BCLabelCreate(BCButtonGroup_1, "Blankholder:")
	BCComboBox_0 = guitk.BCComboBoxCreate(BCButtonGroup_1, [str(pid._name) for pid in holders])
	# One force per blankholder: it is not split between them, so a blankholder
	# that is one physical tool cut into two parts needs its share in each.
	BCLabel_1 = guitk.BCLabelCreate(BCButtonGroup_1, "Total force on this blankholder [N]:")
	BCLineEdit_1 = guitk.BCLineEditCreateDouble(BCButtonGroup_1, 200000.00000)
	BCLabel_2 = guitk.BCLabelCreate(BCButtonGroup_1, "Direction:")
	BCComboBox_1 = guitk.BCComboBoxCreate(BCButtonGroup_1, DOF_CHOICES)
	BCLabel_3 = guitk.BCLabelCreate(BCButtonGroup_1, note)
	BCSpacer_1 = guitk.BCSpacerCreate(BCButtonGroup_1)
	BCSpacer_2 = guitk.BCSpacerCreate(TopWindow)
	BCDialogButtonBox_1 = guitk.BCDialogButtonBoxCreate(TopWindow)

	# Pre-select the detected direction; the student can still override it.
	_select_dof(BCComboBox_1, dof)

	# Each blankholder carries its own material, so the direction and the note
	# are read again whenever the selection changes.
	guitk.BCComboBoxSetActivatedFunction(BCComboBox_0, _holder_changed,
	                                     [holders, BCComboBox_1, BCLabel_3])
	guitk.BCWindowSetAcceptFunction(TopWindow, _ok_pressed,
	                                [BCLineEdit_1, BCComboBox_1, BCComboBox_0, holders])

	guitk.BCShow(TopWindow)


def _holder_changed(combo, index, data):
	holders, dof_box, note_label = data[0], data[1], data[2]

	pid = holders[index] if 0 <= index < len(holders) else None
	dof, note = _free_dof(pid)

	guitk.BCLabelSetText(note_label, note)
	_select_dof(dof_box, dof)
	if pid:
		_report(pid, dof, note)

	return 0


def _existing_force(force_name):
	for load in base.CollectEntities(constants.LSDYNA, None, "LOAD"):
		if str(load._name) == force_name:
			return load
	return None


def _ok_pressed(w, data):

	sf = _typed_number(data[0])
	dof = guitk.BCComboBoxCurrentText(data[1])
	holders = data[3]

	# False keeps the dialog open so the force can be corrected in place.
	# The SIGN is deliberately not policed: it sets which way along the chosen
	# DOF the blankholder is pushed, and a blankholder on the die side needs the
	# opposite sign to one above the sheet.
	if sf is None:
		print("[ERROR] The force is not a number - type it as 200000 or 200000,0.")
		_message("The force is not a number.<br><br>Type it as <b>200000</b>"
		         " or <b>200000,0</b>.")
		return False
	if sf == 0:
		print("[ERROR] The force is zero - the blankholder would not clamp.")
		_message("The force is zero, so the blankholder would not clamp.")
		return False

	index = guitk.BCComboBoxCurrentItem(data[2])
	pid = holders[index] if 0 <= index < len(holders) else None

	if not pid:
		print("[ERROR] No blankholder selected")
		return True

	force_name = FORCE_PREFIX + str(pid._name)
	curve_name = str(pid._name) + " clamp force curve"

	# Two loads on one blankholder clamp with the sum of the two, which looks
	# like a model that simply clamps too hard.
	if _existing_force(force_name):
		print("[ERROR] '" + force_name + "' already exists.")
		print("        Delete it first, or this blankholder will be clamped with")
		print("        the sum of the two forces.")
		_message("'" + force_name + "' already exists.<br><br>Delete it first,"
		         " or this blankholder would be clamped with the <b>sum</b> of"
		         " the two forces.")
		return False

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
