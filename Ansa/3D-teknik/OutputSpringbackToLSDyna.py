import ansa
from ansa import constants, base
from ansa import guitk, utils
import io
import os
import stat
from os.path import expanduser

# install.ps1 puts the master decks next to the scripts. The springback deck
# needs no solve level: it is implicit, so there is no DT2MS and no adaptivity
# to set. Two things are written into it - the INCLUDE, pointed at the model
# just exported, and ENDTIM from the dialog.
SCRIPT_DIR = expanduser("~") + "\\.BETA\\ANSA\\version_25.1.1\\3D-teknik\\"
DECK_TEMPLATE = "implicit-main.k"

# Springback is quasi-static: the sheet is released and allowed to settle, so
# the end time only has to be long enough for it to come to rest. A student who
# sees it still moving at the end of the run raises this and solves again.
DEFAULT_END_TIME = 0.5


def _card_line(lines, keyword):
	"""Index of the line holding a keyword, or -1."""
	for i, line in enumerate(lines):
		if line.strip().upper() == keyword:
			return i
	return -1


def _field(lines, keyword, name):
	"""Locate a field by name within a card, as (line index, field index).

	The decks are hand-maintained, so addressing fields by absolute line number
	goes wrong silently the first time someone inserts a card above. This walks
	the card's own header comments and finds which 10-character column the field
	name sits in, so an edit is verified against the deck's own labels rather
	than against a line count.
	"""
	start = _card_line(lines, keyword)
	if start < 0:
		return None
	for i in range(start + 1, len(lines)):
		line = lines[i]
		if line.startswith("*"):
			break					# next card reached, field is not here
		if not line.startswith("$"):
			continue
		for f in range((len(line) + 9) // 10):
			# The comment marker sits in the first column of the first name.
			if line[f * 10:(f + 1) * 10].replace("$", " ").strip() == name:
				return i + 1, f
	return None


def _get_field(lines, keyword, name):
	where = _field(lines, keyword, name)
	if not where:
		return None
	i, f = where
	return lines[i][f * 10:(f + 1) * 10].strip()


def _set_field(lines, keyword, name, value):
	"""Write one 10-character right-justified field, addressed by name.

	Right-justifying into exactly 10 characters is what keeps the rest of the
	card in its columns however many digits the value has: the fields after it
	are untouched, and a line shorter than the field is padded first.
	"""
	where = _field(lines, keyword, name)
	if not where:
		print("[ERROR] " + keyword + " has no field " + name + " in "
		      + DECK_TEMPLATE + " - the deck has changed shape")
		return False
	i, f = where
	text = str(value)
	if len(text) > 10:
		print("[ERROR] " + name + " value " + text + " does not fit a"
		      " 10-character field")
		return False
	line = lines[i]
	if len(line) < (f + 1) * 10:
		line = line.ljust((f + 1) * 10)
	lines[i] = line[:f * 10] + text.rjust(10) + line[(f + 1) * 10:]
	return True


def _num(value):
	"""Shortest representation of a number that fits a 10-character field."""
	for digits in range(10, 3, -1):
		text = "%.*G" % (digits, value)
		if len(text) <= 10:
			return text
	return "%.3G" % value


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

	Two things this has to survive:

	  * BCLineEditGetDouble returns guitk.constants.blank - a sentinel, not a
	    number - when the field does not hold a valid double. Comparing that
	    with 0 says nothing, so it is checked for explicitly before the value
	    is used.
	  * A Swedish Windows shows and accepts the decimal comma, so "0,25" can
	    reach us as text that float() will not take. Both separators are
	    accepted here.

	Nothing locale-dependent reaches the deck either way: _num() formats with
	Python's own %, which always writes a period whatever the machine says.

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

	# Not a valid double to ANSA - try the raw text, with a comma read as a
	# decimal point.
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


def _write_deck(directory, model_filename, end_time):
	"""Copy the springback deck beside the exported model and fill it in."""
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

	old_endtim = _get_field(lines, "*CONTROL_TERMINATION", "ENDTIM")
	if not _set_field(lines, "*CONTROL_TERMINATION", "ENDTIM", _num(end_time)):
		print("[ERROR] " + DECK_TEMPLATE + " was NOT written - it would have"
		      " terminated at " + str(old_endtim) + " s instead.")
		return

	path = os.path.join(directory, DECK_TEMPLATE)
	if not _replace(path, "\n".join(lines), template):
		return

	print("[OK] Wrote " + path + " (replaced any earlier copy)")
	print("     ENDTIM " + str(_get_field(lines, "*CONTROL_TERMINATION",
	                                      "ENDTIM")) + " s")
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
	BCLabel_3 = guitk.BCLabelCreate(BCButtonGroup_1, "End time [s]:")
	BCLineEdit_3 = guitk.BCLineEditCreateDouble(BCButtonGroup_1, DEFAULT_END_TIME)
	BCSpacer_1 = guitk.BCSpacerCreate(BCButtonGroup_1)
	BCSpacer_2 = guitk.BCSpacerCreate(TopWindow)
	BCDialogButtonBox_1 = guitk.BCDialogButtonBoxCreate(TopWindow)

	guitk.BCWindowSetAcceptFunction(TopWindow, _ok_pressed,
		[BCLineEdit_1, BCLineEdit_2, BCLineEdit_3])

	guitk.BCShow(TopWindow)



def _ok_pressed(w, data):
	directory = guitk.BCLineEditGetText(data[1]).strip()
	name = guitk.BCLineEditGetText(data[0]).strip()
	end_time = _typed_number(data[2])

	# Checked before anything is written, and the dialog stays open so the
	# student can correct it rather than losing what they typed.
	if not directory:
		print("[ERROR] Choose a folder to export to.")
		_message("Choose a folder to export to.")
		return False
	if not os.path.isdir(directory):
		print("[ERROR] " + directory + " is not a folder that exists.")
		_message("This folder does not exist:<br><br>" + directory)
		return False
	if not name:
		print("[ERROR] Give the model a filename.")
		_message("Give the model a filename.")
		return False
	if end_time is None:
		print("[ERROR] The end time is not a number - type it as 0.5 or 0,5.")
		_message("The end time is not a number.<br><br>Type it as <b>0.5</b>"
		         " or <b>0,5</b>.")
		return False
	if end_time <= 0:
		print("[ERROR] The end time must be greater than zero.")
		_message("The end time must be greater than zero.")
		return False

	ret_val = base.Compress({"__MATERIALS__": 1, "Sets": 0, "F.E.": 1})
	if ret_val == 0: print("[OK] Compress")
	else: print("[ERROR] Compress")

	model_filename = name + ".k"
	filename = os.path.join(directory, model_filename)

	ret_val = base.OutputLSDyna(filename=filename, mode="all", comment_output_field_labels="on", output_element_thickness="at_element_card")

	if ret_val == 1: print("[OK] Export")
	else: print("[ERROR] Export")

	_write_deck(directory, model_filename, end_time)

	return True


if __name__ == '__main__':
	cleanup_output()
