import ansa
from ansa import guitk
from ansa import constants, utils
from ansa import base
import random

BLANK_NAME = "blank"

# Nominal thickness for the rigid tools. The forming contacts set MST
# explicitly (see CreateContacts.py), so this no longer reaches the contact
# and there is nothing for the student to get right here.
TOOL_THICKNESS = "1.0"


def set_property_name():

	CVals_3 = ["blank", "die", "blankholder", "punch1", "punch2"]
	
	TopWindow = guitk.BCWindowCreate("Part name", guitk.constants.BCOnExitDestroy)
	
	BCButtonGroup_1 = guitk.BCButtonGroupCreate(TopWindow, "Select the name of the part", guitk.constants.BCVertical)
	BCPushButton_1 = guitk.BCPushButtonCreate(BCButtonGroup_1, "Open Part", open_part, any)
	#guitk.BCButtonSetClickedFunction(BCPushButton_1, open_part, any)
	BCLabel_1 = guitk.BCLabelCreate(BCButtonGroup_1, "Part name:")
	BCComboBox_1 = guitk.BCComboBoxCreate(BCButtonGroup_1, CVals_3)
	BCLabel_2 = guitk.BCLabelCreate(BCButtonGroup_1, "Thickness:")
	BCLineEdit_1 = guitk.BCLineEditCreateDouble(BCButtonGroup_1, 1.0000000000)
	BCSpacer_1 = guitk.BCSpacerCreate(BCButtonGroup_1)
	BCSpacer_2 = guitk.BCSpacerCreate(TopWindow)
	BCDialogButtonBox_1 = guitk.BCDialogButtonBoxCreate(TopWindow)
	
	# CVals_3[0] is "blank", so the field starts enabled and correct.
	guitk.BCComboBoxSetActivatedFunction(BCComboBox_1, _name_changed, [BCLabel_2, BCLineEdit_1])
	guitk.BCWindowSetAcceptFunction(TopWindow, _ok_pressed, [BCComboBox_1, BCLineEdit_1])

	guitk.BCShow(TopWindow)


def _name_changed(combo, index, data):
	# Thickness only means something for the blank now.
	is_blank = guitk.BCComboBoxCurrentText(combo) == BLANK_NAME
	guitk.BCSetEnabled(data[0], is_blank)		# "Thickness:" label
	guitk.BCSetEnabled(data[1], is_blank)		# the input field
	return 0


def _ok_pressed(w, data):
	name = guitk.BCComboBoxCurrentText(data[0])
	thickness = guitk.BCLineEditGetText(data[1]) if name == BLANK_NAME else TOOL_THICKNESS
	pids = base.CollectEntities(constants.LSDYNA, None, "SECTION_SHELL", False)
	
	if not pids:
		return True
	
	base.SetEntityCardValues(constants.LSDYNA, pids[len(pids)-1], {'Name': name, 'ELFORM': "16", 'NIP': "7", 'T1': thickness, 'COLOR_R': str(random.randint(0, 255)), 'COLOR_G': str(random.randint(0, 255)), 'COLOR_B': str(random.randint(0, 255))})
	
	if name == BLANK_NAME:
		base.SetEntityCardValues(constants.LSDYNA, pids[len(pids)-1], {'ADPOPT': "1"})
	else:
		base.SetEntityCardValues(constants.LSDYNA, pids[len(pids)-1], {'ADPOPT': "0"})	
		
	return True


def open_part(b, data):
	# Open part
	current_file_path = base.DataBaseName()
	if current_file_path: 
		open_merge_file()
	else:
		open_first_file()
		
	guitk.BCBlockCallBackFunctions(b, True)
	
	return 0
		
		

def open_first_file():
	files = utils.SelectOpenFile(0)
	if files: 
		print("[OK] File selected")
	else: 
		print("[ERROR] No file selected")
		#return
	
	ret_val = base.Open(files[0])
	if ret_val==0: print("[OK] Open")
	else: print("[ERROR] Failed to Open")
	
	
def open_merge_file():
	files = utils.SelectOpenFile(0)
	if files: 
		print("[OK] File selected")
	else: 
		print("[ERROR] No file selected")
		#return
	
	ret_val = utils.Merge(filename=files[0], property_offset="offset", model_action="merge_model")
	if ret_val==1: print("[OK] Open")
	else: print("[ERROR] Failed to Open")


if __name__ == '__main__':
	set_property_name()