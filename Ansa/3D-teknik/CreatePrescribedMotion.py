import os
import re
import ansa
from ansa import guitk
from ansa import constants
from ansa import base

# Punches only. The die never moves, and a blankholder is driven by its clamp
# force in step 6, not by a prescribed motion - giving it one would fight the
# force and hold the sheet open. Matches punch1, punch2, ... and a plain
# "punch" from a model set up before the numbering.
PUNCH_PATTERN = re.compile(r"^punch\d*$")


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
	would become a punch velocity rather than an error. The class also runs on
	Swedish Windows, where the decimal separator is a comma, so "0,1" can reach
	us as text that float() will not take. Both separators are accepted.

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


def punch_movement():

	pids = base.CollectEntities(constants.LSDYNA, None, "SECTION_SHELL", False)
	CVals_2 = [str(pid._name) for pid in pids if PUNCH_PATTERN.match(str(pid._name))]

	if not CVals_2:
		print("[ERROR] No punch in the model - run '1. Open parts' and name a part 'punch'")
		return

	CVals_3 = ["1 X-tra", "2 Y-tra", "3 Z-tra"]
	
	TopWindow = guitk.BCWindowCreate("Create prescribed motion", guitk.constants.BCOnExitDestroy)
	
	BCButtonGroup_1 = guitk.BCButtonGroupCreate(TopWindow, "Settings", guitk.constants.BCVertical)
	BCLabel_1 = guitk.BCLabelCreate(BCButtonGroup_1, "Part:")
	BCComboBox_1 = guitk.BCComboBoxCreate(BCButtonGroup_1, CVals_2)
	BCLabel_2 = guitk.BCLabelCreate(BCButtonGroup_1, "Direction:")
	BCComboBox_2 = guitk.BCComboBoxCreate(BCButtonGroup_1, CVals_3)
	BCLabel_3 = guitk.BCLabelCreate(BCButtonGroup_1, "Distance [mm]:")
	BCLineEdit_1 = guitk.BCLineEditCreateDouble(BCButtonGroup_1, 1.0000000000)
	BCLabel_4 = guitk.BCLabelCreate(BCButtonGroup_1, "Start time [s]:")
	BCLineEdit_2 = guitk.BCLineEditCreateDouble(BCButtonGroup_1, 0.0000000000)
	BCLabel_5 = guitk.BCLabelCreate(BCButtonGroup_1, "End time [s]:")
	# 0.1 s is the validated default and must match ENDTIM in explicit-main.k.
	# Shortening it is an independent way to cut solve time - it buys cycles
	# without adding mass, unlike coarsening DT2MS - but it raises inertia.
	# Students may experiment; see docs/test-log.md "Planned: two solve levels".
	BCLineEdit_3 = guitk.BCLineEditCreateDouble(BCButtonGroup_1, 0.1000000000)
	BCSpacer_1 = guitk.BCSpacerCreate(BCButtonGroup_1)
	BCSpacer_2 = guitk.BCSpacerCreate(TopWindow)
	BCDialogButtonBox_1 = guitk.BCDialogButtonBoxCreate(TopWindow)
	
	guitk.BCWindowSetAcceptFunction(TopWindow, _ok_pressed, [BCComboBox_1, BCComboBox_2, BCLineEdit_1, BCLineEdit_2, BCLineEdit_3, pids])
	
	guitk.BCShow(TopWindow)


def _ok_pressed(w, data):
	
	pid_name = guitk.BCComboBoxCurrentText(data[0])
	bc_name = "Prescribed motion - " + pid_name
	curve_name = pid_name + " motion curve"
	index = [i for i,  pid in enumerate(data[5]) if pid._name == pid_name][0]
	pid = data[5][index]
	
	dof = guitk.BCComboBoxCurrentText(data[1])
	vad = "0 Velo"
	
	distance = _typed_number(data[2])
	start_time = _typed_number(data[3])
	end_time = _typed_number(data[4])

	# False keeps the dialog open on every refusal below, so one bad field does
	# not cost the student the other three.
	if distance is None or start_time is None or end_time is None:
		print("[ERROR] The distance and both times must be numbers - type them")
		print("        as 0.1 or 0,1.")
		_message("The distance and both times must be numbers.<br><br>"
		         "Type them as <b>0.1</b> or <b>0,1</b>.")
		return False
	if distance == 0:
		print("[ERROR] The distance is zero - the punch would not move.")
		_message("The distance is zero, so the punch would not move.")
		return False

	p2_time = start_time + 0.0010
	p3_time = end_time - 0.0010
	# The curve ramps up over the first millisecond and back down over the last,
	# so the stroke has to be longer than that. Without this the velocity below
	# is a division by zero, or a negative that drives the punch backwards.
	area = end_time - start_time - 0.0010
	if area <= 0:
		print("[ERROR] The end time must be more than 1 ms after the start time.")
		_message("The end time must be more than <b>1 ms</b> after the start"
		         " time.<br><br>The punch ramps up to speed over the first"
		         " millisecond and back down over the last, so a shorter stroke"
		         " leaves it no time to move in.")
		return False

	sf = distance / area
	
	punch_curve = base.CreateLoadCurve("DEFINE_CURVE",{"Name": curve_name})
	base.SetLoadCurveData(punch_curve, ((start_time, 0.0), (p2_time, 1.0), (p3_time, 1.0), (end_time, 0.0)))
	
	print("Curve OK!")
	
	BC_properties = {"Name": bc_name, "by": "node", "node/rigid": "_RIGID", "prop_type": "PROP", "PID": pid._id, "DOF": dof, "VAD": vad, "LCID": punch_curve._id, "SF": sf}
	new_BC = base.CreateEntity(constants.LSDYNA, "BOUNDARY_PRESCRIBED_MOTION", BC_properties)
	
	if new_BC:
		print(f"Successfully created BC '{new_BC._name}'.")
	else:
		print("Failed to create the BC.")
	
	return True

if __name__ == '__main__':
	punch_movement()


