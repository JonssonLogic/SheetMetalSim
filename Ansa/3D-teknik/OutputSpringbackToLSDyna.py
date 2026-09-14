import ansa
from ansa import constants, base
from ansa import guitk, utils
import io
import os
import stat
from os.path import expanduser

# install.ps1 puts the master decks next to the scripts. The springback deck
# needs no solve level: it is implicit, so there is no DT2MS and no adaptivity
# to set. Only the INCLUDE has to be pointed at the model just exported.
SCRIPT_DIR = expanduser("~") + "\\.BETA\\ANSA\\version_25.1.1\\3D-teknik\\"
DECK_TEMPLATE = "implicit-main.k"


def _card_line(lines, keyword):
	"""Index of the line holding a keyword, or -1."""
	for i, line in enumerate(lines):
		if line.strip().upper() == keyword:
			return i
	return -1


def _replace(path, text, template):
	"""Write text to path, clearing whatever is already there first.

	The run folder normally already holds a deck from the previous export. A
	plain write would truncate it, but not if Windows has left it read-only -
	copying a file off a network share or out of an archive commonly does - and
	not if it is still open in an editor or in LS-DYNA. Deleting first turns the
	first case into a success and the second into a message that says which
	program to close, rather than a bare permission error.

	The deck is regenerated from the template on every export, so there is
	nothing of value in the copy being removed.
	"""
	if os.path.exists(path):
		# Refuse to eat the template itself, which would happen if the ANSA
		# database were saved into the script folder.
		if os.path.exists(template) and os.path.samefile(path, template):
			print("[ERROR] The model is saved in the script folder, so writing"
			      " the deck would overwrite")
			print("        the master template " + template)
			print("        Save the model somewhere else and export again.")
			return False
		try:
			os.chmod(path, stat.S_IWRITE)
			os.remove(path)
		except OSError as e:
			print("[ERROR] Could not replace " + path + ": " + repr(e))
			print("        It is probably open in another program - close it"
			      " and export again.")
			return False

	try:
		io.open(path, "w", encoding="utf-8", newline="\n").write(text)
	except IOError as e:
		print("[ERROR] Could not write " + path + ": " + repr(e))
		return False
	return True


def _write_deck(directory, model_filename):
	"""Copy the springback deck beside the exported model and point it at it."""
	template = SCRIPT_DIR + DECK_TEMPLATE

	try:
		lines = io.open(template, encoding="utf-8").read().split("\n")
	except IOError:
		print("[ERROR] Could not read " + template)
		print("        Run install.ps1 - the master decks live next to the"
		      " scripts now.")
		return

	include = _card_line(lines, "*INCLUDE")
	if include < 0:
		print("[ERROR] " + DECK_TEMPLATE + " has no INCLUDE card - not written")
		return
	for i in range(include + 1, len(lines)):
		if not lines[i].startswith("$"):
			lines[i] = model_filename
			break

	path = os.path.join(directory, DECK_TEMPLATE)
	if not _replace(path, "\n".join(lines), template):
		return

	print("[OK] Wrote " + path + " (replaced any earlier copy)")
	print("     Solve this file, not " + model_filename + ".")


def _browse(button, data):
	"""Pick the export folder. An empty start opens the last folder used."""
	chosen = utils.SelectSaveDir(guitk.BCLineEditGetText(data))
	if chosen:
		guitk.BCLineEditSetText(data, chosen)
	return 0


def cleanup_output():

	# Only a default. The student picks where the export goes - the model does
	# not have to have been saved for this step to work.
	current_db_path = base.DataBaseName()
	base_name = os.path.splitext(os.path.basename(current_db_path))[0]
	db_directory = os.path.dirname(current_db_path)

	TopWindow = guitk.BCWindowCreate("Export LS-Dyna file.", guitk.constants.BCOnExitDestroy)

	BCButtonGroup_1 = guitk.BCButtonGroupCreate(TopWindow, "Settings", guitk.constants.BCVertical)
	BCLabel_1 = guitk.BCLabelCreate(BCButtonGroup_1, "Folder:")
	FolderRow = guitk.BCBoxLayoutCreate(BCButtonGroup_1, guitk.constants.BCHorizontal)
	BCLineEdit_2 = guitk.BCLineEditCreate(FolderRow, db_directory)
	BCPushButton_1 = guitk.BCPushButtonCreate(FolderRow, "Browse...", _browse, BCLineEdit_2)
	BCLabel_2 = guitk.BCLabelCreate(BCButtonGroup_1, "Filename:")
	BCLineEdit_1 = guitk.BCLineEditCreate(BCButtonGroup_1, base_name)
	BCSpacer_1 = guitk.BCSpacerCreate(BCButtonGroup_1)
	BCSpacer_2 = guitk.BCSpacerCreate(TopWindow)
	BCDialogButtonBox_1 = guitk.BCDialogButtonBoxCreate(TopWindow)

	guitk.BCWindowSetAcceptFunction(TopWindow, _ok_pressed, [BCLineEdit_1, BCLineEdit_2])

	guitk.BCShow(TopWindow)



def _ok_pressed(w, data):
	directory = guitk.BCLineEditGetText(data[1]).strip()
	name = guitk.BCLineEditGetText(data[0]).strip()

	# Checked before anything is written, and the dialog stays open so the
	# student can correct it rather than losing what they typed.
	if not directory:
		print("[ERROR] Choose a folder to export to.")
		return False
	if not os.path.isdir(directory):
		print("[ERROR] " + directory + " is not a folder that exists.")
		return False
	if not name:
		print("[ERROR] Give the model a filename.")
		return False

	ret_val = base.Compress({"__MATERIALS__": 1, "Sets": 0, "F.E.": 1})
	if ret_val == 0: print("[OK] Compress")
	else: print("[ERROR] Compress")

	model_filename = name + ".k"
	filename = os.path.join(directory, model_filename)

	ret_val = base.OutputLSDyna(filename=filename, mode="all", comment_output_field_labels="on", output_element_thickness="at_element_card")

	if ret_val == 1: print("[OK] Export")
	else: print("[ERROR] Export")

	_write_deck(directory, model_filename)

	return True


if __name__ == '__main__':
	cleanup_output()
