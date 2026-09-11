import os
import ansa
from ansa import guitk
from ansa import constants
from ansa import base

def punch_movement():
	
	pids = base.CollectEntities(constants.LSDYNA, None, "SECTION_SHELL", False)
	CVals_2 = [pid._name for pid in pids if pid._name != "blank" if pid._name != "die"]

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
	
	start_time = guitk.BCLineEditGetDouble(data[3])
	end_time = guitk.BCLineEditGetDouble(data[4])
	p2_time = start_time + 0.0010
	p3_time = end_time - 0.0010
	area = end_time - start_time - 0.0010
	distance = guitk.BCLineEditGetDouble(data[2])
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


