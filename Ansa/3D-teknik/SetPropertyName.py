import ansa
from ansa import guitk
from ansa import constants, utils
from ansa import base
import random
import re

# The function a part has in the setup. "blank" and "die" exist once per model;
# there can be several blankholders and punches, so those are numbered as they
# are imported - blankholder1, punch2 and so on. Everything downstream matches
# these names: see the part-name contract in CLAUDE.md.
PART_FUNCTIONS = ["blank", "die", "blankholder", "punch"]
UNIQUE_FUNCTIONS = ("blank", "die")

BLANK_NAME = "blank"

# Nominal thickness for the rigid tools. The forming contacts set MST
# explicitly (see CreateContacts.py), so this no longer reaches the contact
# and there is nothing for the student to get right here.
TOOL_THICKNESS = "1.0"

# One file is one tool, whatever it holds. ANSA's translator creates a property
# per body by default (TRANSL_BODY2PID), which splits a two-body blankholder
# into two rigid parts - two contacts, and a clamp force on only one of them.
# These settings put a whole file into one property instead. STEP and IGES are
# read either natively or through the CAD Translator, hence both pairs.
# The previous values are put back after the import, so nothing else the
# student does in this ANSA session is affected.
#
# Confirmed in ANSA 25.1.1 on 2026-09-16: a two-surface blankholder.STEP came in
# as one property, with no merge needed.
SINGLE_PROPERTY_PER_FILE = {
	"TRANSL_BODY2PID_NEUTRAL_FILES": "false",
	"TRANSL_SINGLEPID_NEUTRAL_FILES": "true",
	"TRANSL_BODY2PID_NEUTRAL_WITH_CT": "false",
	"TRANSL_SINGLEPID_NEUTRAL_WITH_CT": "true",
}


def set_property_name():

	# Shared between the Open Part button and OK: which function the student
	# picked, and the one property the import produced.
	state = {"combo": None, "imported": []}

	TopWindow = guitk.BCWindowCreate("Part name", guitk.constants.BCOnExitDestroy)

	# The function is picked FIRST and the file opened after it, so an import
	# that could not be named is refused before anything is read.
	BCButtonGroup_1 = guitk.BCButtonGroupCreate(TopWindow, "Select the name of the part", guitk.constants.BCVertical)
	BCLabel_1 = guitk.BCLabelCreate(BCButtonGroup_1, "Part name:")
	BCComboBox_1 = guitk.BCComboBoxCreate(BCButtonGroup_1, PART_FUNCTIONS)
	BCLabel_2 = guitk.BCLabelCreate(BCButtonGroup_1, "Thickness:")
	BCLineEdit_1 = guitk.BCLineEditCreateDouble(BCButtonGroup_1, 1.0000000000)
	BCPushButton_1 = guitk.BCPushButtonCreate(BCButtonGroup_1, "Open Part", open_part, state)
	BCSpacer_1 = guitk.BCSpacerCreate(BCButtonGroup_1)
	BCSpacer_2 = guitk.BCSpacerCreate(TopWindow)
	BCDialogButtonBox_1 = guitk.BCDialogButtonBoxCreate(TopWindow)

	# Before BCShow, and open_part only runs on a click, so it is always set.
	state["combo"] = BCComboBox_1

	# PART_FUNCTIONS[0] is "blank", so the field starts enabled and correct.
	guitk.BCComboBoxSetActivatedFunction(BCComboBox_1, _name_changed, [BCLabel_2, BCLineEdit_1])
	guitk.BCWindowSetAcceptFunction(TopWindow, _ok_pressed, [BCComboBox_1, BCLineEdit_1, state])

	guitk.BCShow(TopWindow)


def _name_changed(combo, index, data):
	# Thickness only means something for the blank now.
	is_blank = guitk.BCComboBoxCurrentText(combo) == BLANK_NAME
	guitk.BCSetEnabled(data[0], is_blank)		# "Thickness:" label
	guitk.BCSetEnabled(data[1], is_blank)		# the input field
	return 0


def _properties():
	return base.CollectEntities(constants.LSDYNA, None, "SECTION_SHELL", False)


def _typed_number(line_edit):
	"""Read a number from a dialog field, whichever decimal separator was used.

	Two things this has to survive:

	  * BCLineEditGetDouble returns guitk.constants.blank - a sentinel, not a
	    number - when the field does not hold a valid double. Comparing that
	    with 0 says nothing, so it is checked for explicitly.
	  * A Swedish Windows shows and accepts the decimal comma, so "1,5" can
	    reach us as text that float() will not take. Both separators are
	    accepted here.

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


def _number_text(value):
	"""A number as the card wants it: a period, and short enough for the field.

	The thickness used to go into T1 as the field's raw text. On a machine whose
	decimal separator is a comma that put "1,5" on the card, and T1 is what
	CreateContacts._master_thickness reads back with float() to compute MST -
	which fails, reports the blank as having no thickness at all, and stops
	step 4 two steps after the value was typed.

	Python's % formatting is locale-independent, so this always writes a period.
	"""
	for digits in range(10, 3, -1):
		text = "%.*G" % (digits, value)
		if len(text) <= 10:
			return text
	return "%.3G" % value


def _message(text):
	"""A message the student cannot miss.

	The console is the only feedback most steps give, but a refused import has
	to stop the student where they are looking - at the file browser they just
	came out of, not at the console behind the dialog.
	"""
	try:
		window = guitk.BCMessageWindowCreate(guitk.constants.BCMessageBoxWarning,
		                                     text, True)
		guitk.BCMessageWindowExecute(window)
	except Exception:
		pass		# the console lines above it still carry the message


def _duplicate_text(function):
	return ("This model already has a part named '<b>" + function + "</b>'.<br><br>"
	        "There is only ever one " + function + " in a setup.<br>"
	        "Choose another function in the list, or delete the "
	        + function + " that is already there before importing another one.")


def _next_name(function):
	"""The name this part gets, or None if the model already has one.

	blank and die are unique - a second one is a mistake, and renaming it would
	give two parts the same name, where every consumer silently takes the first.
	blankholder and punch are numbered from 1. A plain "blankholder" from a
	model set up before the numbering counts as number 1, so the next one
	becomes blankholder2 rather than colliding with it.
	"""
	taken = [str(pid._name) for pid in _properties()]

	if function in UNIQUE_FUNCTIONS:
		return None if function in taken else function

	used = set()
	numbered = re.compile("^" + function + r"(\d*)$")
	for name in taken:
		found = numbered.match(name)
		if found:
			used.add(int(found.group(1)) if found.group(1) else 1)

	number = 1
	while number in used:
		number += 1
	return function + str(number)


def _selected_function(state):
	combo = state.get("combo")
	if not combo:
		return PART_FUNCTIONS[0]
	return guitk.BCComboBoxCurrentText(combo)


def _use_one_property_per_file():
	"""Make the translator put a whole file in one property.

	Returns the settings as they were, to be put back after the import, or None
	if they could not be read or set - in which case nothing was changed and
	_merge_into_one() below deals with whatever the import produces.
	"""
	try:
		previous = base.BCSettingsGetValues(tuple(SINGLE_PROPERTY_PER_FILE))
	except Exception:
		previous = None

	if previous and base.BCSettingsSetValues(SINGLE_PROPERTY_PER_FILE) == 0:
		return previous

	print("[ERROR] Could not set ANSA's translator to one part per file.")
	print("        A file holding several bodies will be merged after the")
	print("        import instead.")
	return None


def _restore_settings(previous):
	if not previous:
		return
	try:
		base.BCSettingsSetValues(previous)
	except Exception:
		print("[ERROR] Could not restore ANSA's translator settings.")


def _merge_into_one(properties):
	"""Put every body the file brought in into one property.

	The translator settings normally make this unnecessary. It is the fallback
	for a file that still arrives as several properties, because everything
	downstream treats one property as one rigid tool: one contact, one clamp
	force, one prescribed motion.
	"""
	keep = properties[0]
	merged = 0

	for extra in properties[1:]:
		faces = base.CollectEntities(constants.LSDYNA, extra, "FACE", True)
		if faces and base.ReplaceProperty(None, keep, faces) != 0:
			print("[ERROR] Could not move the geometry of '" + str(extra._name)
			      + "' onto '" + str(keep._name) + "'")
			continue
		# force=False: the faces just moved to 'keep' are referenced by it now
		# and must not be dragged along with the empty property.
		base.DeleteEntity(extra, False)
		merged += 1

	if merged:
		print("[OK] The file held " + str(merged + 1)
		      + " bodies - merged into one part")
	return keep


def _ok_pressed(w, data):
	function = guitk.BCComboBoxCurrentText(data[0])
	imported = data[2]["imported"]

	# False keeps the dialog open on every refusal below, so the student can
	# correct the choice instead of starting the step again.
	if not imported:
		print("[ERROR] No part was imported - press 'Open Part' first.")
		print("        Nothing was renamed.")
		return False

	if function == BLANK_NAME:
		typed = _typed_number(data[1])
		if typed is None:
			print("[ERROR] The thickness is not a number - type it as 1.5 or 1,5.")
			return False
		if typed <= 0:
			print("[ERROR] The thickness must be greater than zero.")
			return False
		thickness = _number_text(typed)
	else:
		thickness = TOOL_THICKNESS

	pid = imported[0]
	name = _next_name(function)

	if name is None:
		# open_part checked this before importing, so getting here means the
		# function was changed to a taken one after the file was opened.
		print("[ERROR] This model already has a part named '" + function + "'.")
		print("        '" + str(pid._name) + "' was left as it is - choose another")
		print("        function, or delete the existing " + function + ".")
		_message(_duplicate_text(function)
		         + "<br><br>The part you imported is still called '"
		         + str(pid._name) + "'.")
		return False

	values = {'Name': name, 'ELFORM': "16", 'NIP': "7", 'T1': thickness,
	          'COLOR_R': str(random.randint(0, 255)),
	          'COLOR_G': str(random.randint(0, 255)),
	          'COLOR_B': str(random.randint(0, 255)),
	          'ADPOPT': "1" if function == BLANK_NAME else "0"}

	# One failing field stops the others being set, and the only sign of that
	# is the return code.
	returned = base.SetEntityCardValues(constants.LSDYNA, pid, values,
	                                    debug=constants.REPORT_ALL)
	code = returned[0] if isinstance(returned, tuple) else returned

	if code == 0:
		print("[OK] Part named '" + name + "'")
	else:
		print("[ERROR] Could not set the card values on '" + name + "'")
		print("        Check the part's SECTION_SHELL card before continuing.")

	return True


def open_part(b, data):
	"""Import one file, leaving exactly one property behind.

	The function is read from the dialog BEFORE the file browser opens, so a
	second blank or die is refused without importing anything and the model is
	left exactly as it was. Importing first and refusing the name afterwards
	left an unnamed part in the model for the student to find and delete.
	"""
	function = _selected_function(data)

	if _next_name(function) is None:
		print("[ERROR] This model already has a part named '" + function + "'.")
		print("        Nothing was imported. Choose another function, or delete")
		print("        the " + function + " that is already there.")
		_message(_duplicate_text(function))
		return 0

	before = set()
	for pid in _properties():
		before.add(pid._id)

	previous_settings = _use_one_property_per_file()
	try:
		# Open starts a database; everything after it merges into that one.
		if base.DataBaseName():
			opened = open_merge_file()
		else:
			opened = open_first_file()
	finally:
		_restore_settings(previous_settings)

	if not opened:
		return 0

	new = [pid for pid in _properties() if pid._id not in before]
	if not new:
		print("[ERROR] The file brought in no new part")
		return 0

	data["imported"] = [_merge_into_one(new) if len(new) > 1 else new[0]]

	# One import per dialog: the name given at OK applies to this part only.
	guitk.BCBlockCallBackFunctions(b, True)

	return 0


def open_first_file():
	files = utils.SelectOpenFile(0)
	if not files:
		print("[ERROR] No file selected")
		return False

	print("[OK] File selected")
	if base.Open(files[0]) == 0:
		print("[OK] Open")
		return True

	print("[ERROR] Failed to Open")
	return False


def open_merge_file():
	files = utils.SelectOpenFile(0)
	if not files:
		print("[ERROR] No file selected")
		return False

	print("[OK] File selected")
	if utils.Merge(filename=files[0], property_offset="offset", model_action="merge_model") == 1:
		print("[OK] Open")
		return True

	print("[ERROR] Failed to Open")
	return False


if __name__ == '__main__':
	set_property_name()
