# PYTHON script
import os
import ansa
from ansa import base
from os.path import expanduser

# install.ps1 puts forming_materials.k next to the scripts, so there is nothing
# for the student to go and find. One file, one known state, the same for
# everyone in the room.
SCRIPT_DIR = expanduser("~") + "\\.BETA\\ANSA\\version_25.1.1\\3D-teknik\\"
MATERIALS_FILE = "forming_materials.k"


def main():

	path = SCRIPT_DIR + MATERIALS_FILE

	if not os.path.isfile(path):
		print("[ERROR] " + path + " not found")
		print("        Run install.ps1 - the materials file lives next to the")
		print("        scripts now.")
		return

	ret_val = base.InputLSDyna(filename=path)
	if ret_val == 1:
		print("[OK] Materials imported from " + MATERIALS_FILE)
	else:
		print("[ERROR] Failed to import " + path)


if __name__ == '__main__':
	main()
