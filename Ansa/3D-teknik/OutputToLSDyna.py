import ansa
from ansa import constants, base
from ansa import guitk
import os

def cleanup_output():
	
	current_db_path = base.DataBaseName()
	db_filename = os.path.basename(current_db_path)
	base_name = os.path.splitext(db_filename)[0]
	db_directory = os.path.dirname(current_db_path)
	
	TopWindow = guitk.BCWindowCreate("Export LS-Dyna file.", guitk.constants.BCOnExitDestroy)
	
	BCButtonGroup_1 = guitk.BCButtonGroupCreate(TopWindow, "Settings", guitk.constants.BCVertical)
	BCLabel_1 = guitk.BCLabelCreate(BCButtonGroup_1, "Filename:")
	BCLineEdit_1 = guitk.BCLineEditCreate(BCButtonGroup_1, base_name)
	BCLabel_2 = guitk.BCLabelCreate(BCButtonGroup_1, db_directory)
	BCSpacer_1 = guitk.BCSpacerCreate(BCButtonGroup_1)
	BCSpacer_2 = guitk.BCSpacerCreate(TopWindow)
	BCDialogButtonBox_1 = guitk.BCDialogButtonBoxCreate(TopWindow)
	
	guitk.BCWindowSetAcceptFunction(TopWindow, _ok_pressed, [BCLineEdit_1])
	
	guitk.BCShow(TopWindow)
	
	
	
def _ok_pressed(w, data):	
	ret_val = base.Compress({"__MATERIALS__": 1, "Sets": 0, "F.E.": 1})
	if ret_val == 0: print("[OK] Compress")
	else: print("[ERROR] Compress")
	
	current_db_path = base.DataBaseName()
	db_filename = os.path.basename(current_db_path)
	db_directory = os.path.dirname(current_db_path)
	
	filename = db_directory + "\\" + guitk.BCLineEditGetText(data[0]) + ".k"
		
	ret_val = base.OutputLSDyna(filename=filename, mode="all", comment_output_field_labels="on")
	
	if ret_val == 1: print("[OK] Export")
	else: print("[ERROR] Export")
	
	return True


if __name__ == '__main__':
	cleanup_output()


