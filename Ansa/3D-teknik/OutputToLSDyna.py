import ansa
from ansa import constants, base
from ansa import guitk, utils
import io
import os
import re
import stat
from os.path import expanduser

# install.ps1 puts the master decks next to the scripts, so the student never
# browses for one and never copies one by hand.
SCRIPT_DIR = expanduser("~") + "\\.BETA\\ANSA\\version_25.1.1\\3D-teknik\\"
DECK_TEMPLATE = "explicit-main.k"

BLANK_NAME = "blank"

# Every blankholder needs a clamp force and every punch a prescribed motion.
# Neither omission is something LS-DYNA reports: a blankholder with no force is
# a rigid part free to be pushed aside, and a punch with no motion just stands
# still, so the run terminates normally and the result is quietly wrong.
BLANKHOLDER_PATTERN = re.compile(r"^blankholder\d*$")
PUNCH_PATTERN = re.compile(r"^punch\d*$")

# Written by step 2 onto the blank as user-defined attributes. The key is the
# attribute's "Full Name" - "User/<group>/<name>" - not the name it is created
# with; the bare name gives 'Field not found!'. See FixGeoAndMesh.py.
LEVEL_ATTRIBUTES = ("FORMING_LEVEL", "FORMING_BLANK", "FORMING_MAXLVL",
                    "FORMING_DT2MS")
ATTRIBUTE_GROUP = "Forming setup"

# Used only when step 2 has not been run - run 14, the reference configuration.
DEFAULT_LEVEL = "Standard"
DEFAULT_MAXLVL = "2"
DEFAULT_DT2MS = "-2.5E-7"


def _card_line(lines, keyword):
	"""Index of the line holding a keyword, or -1."""
	for i, line in enumerate(lines):
		if line.strip().upper() == keyword:
			return i
	return -1


def _field(lines, keyword, name):
	"""Locate a field by name within a card, as (line index, field index).

	The decks are hand-maintained, so addressing fields by absolute line number
	- as make_deck_variants.py does - goes wrong silently the first time someone
	inserts a card above. This walks the card's own header comments and finds
	which 10-character column the field name sits in, so an edit is verified
	against the deck's own labels rather than against a line count.
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
	"""Write one 10-character right-justified field, addressed by name."""
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


def _num(value):
	"""Shortest representation of a number that fits a 10-character field."""
	for digits in range(10, 3, -1):
		text = "%.*G" % (digits, value)
		if len(text) <= 10:
			return text
	return "%.3G" % value


def _abscissae(points):
	"""The x values of a curve, whichever shape GetLoadCurveData returns."""
	if not points:
		return []
	# Either [[x, y], [x, y], ...] or [[x, x, ...], [y, y, ...]].
	if len(points) == 2 and len(points[0]) > 2:
		return list(points[0])
	return [row[0] for row in points if row]


def _stroke_end_time():
	"""Latest end time over every prescribed motion, or None if there are none.

	Prescribed motions only. The clamp force curve runs to 1.0 s, so scanning
	every load curve in the model would terminate the run ten times later than
	the stroke. Several punches may move over different intervals, so it is the
	latest end time that has to govern, not the first one found.
	"""
	latest = None
	for bc in base.CollectEntities(constants.LSDYNA, None,
	                               "BOUNDARY_PRESCRIBED_MOTION", False):
		try:
			lcid = base.GetEntityCardValues(constants.LSDYNA, bc,
			                                ("LCID",)).get("LCID")
			curve = base.GetEntity(constants.LSDYNA, "DEFINE_CURVE",
			                       int(float(str(lcid))))
			points = base.GetLoadCurveData(curve)
		except Exception:
			continue
		for time in _abscissae(points):
			if latest is None or time > latest:
				latest = time
	return latest


def _fallback(reason):
	print("[ERROR] " + reason)
	print("        Writing " + DEFAULT_LEVEL + " (MAXLVL " + DEFAULT_MAXLVL
	      + ", DT2MS " + DEFAULT_DT2MS + ") into the deck.")
	# No blank size. The mesh was built in step 2 and nothing here knows with
	# what, so the title leaves it out rather than stating a guess.
	return DEFAULT_LEVEL, "", DEFAULT_MAXLVL, DEFAULT_DT2MS


def _attribute_key(name):
	"""The key GetEntityCardValues needs for one of our attributes, or None."""
	try:
		attr = base.CreateUserDefinedAttribute(
			deck=constants.LSDYNA, element_type="SECTION_SHELL", name=name,
			type="TEXT", default_value="", group_name=ATTRIBUTE_GROUP,
			read_only=False, accepted_values="")
		if attr is None:
			return None
		return base.GetEntityCardValues(constants.LSDYNA, attr,
		                                ("Full Name",)).get("Full Name")
	except Exception:
		return None


def _stored_level():
	"""The solve level step 2 recorded on the blank.

	Returns (level, blank size, MAXLVL, DT2MS), all as text. Falls back to
	Standard - loudly, never silently - when step 2 has not been run or the
	values are not usable. The blank size is "" when it was not recorded, which
	is the case for models set up before 2026-09-14.
	"""
	blank = None
	for pid in base.CollectEntities(constants.LSDYNA, None, "SECTION_SHELL", False):
		if pid._name == BLANK_NAME:
			blank = pid
			break
	if not blank:
		return _fallback("No part named '" + BLANK_NAME + "' in the model.")

	values = {}
	for name in LEVEL_ATTRIBUTES:
		key = _attribute_key(name)
		if not key:
			return _fallback("Could not read the solve level off the blank.")
		try:
			value = base.GetEntityCardValues(constants.LSDYNA, blank,
			                                 (key,)).get(key)
		except Exception:
			value = None
		# The storage diagnostic saw a missing field come back as None as well
		# as "". str(None) would read as a level called "None".
		values[name] = "" if value is None else str(value).strip()

	level = values.get("FORMING_LEVEL", "")
	size = values.get("FORMING_BLANK", "")
	maxlvl = values.get("FORMING_MAXLVL", "")
	dt2ms = values.get("FORMING_DT2MS", "")

	# The attributes are created with an empty default, so blank means step 2
	# never ran on this model rather than that it chose nothing. The blank size
	# is deliberately not required: a model set up before it was carried still
	# has a valid level, and discarding that for Standard would be worse.
	if not (level and maxlvl and dt2ms):
		return _fallback("No solve level on the blank - run step 2, Fix, mesh"
		                 " and check, to choose one.")

	# They are editable in ANSA's card, so check they can go into a deck rather
	# than writing nonsense into the solver.
	try:
		int(maxlvl)
		scaled = float(dt2ms)
	except ValueError:
		return _fallback("The blank holds MAXLVL '" + maxlvl + "' and DT2MS '"
		                 + dt2ms + "' - at least one is not a number.")
	try:
		float(size)
	except ValueError:
		size = ""					# only the title and the dialog use it

	# Warned about, not overridden. A dropped minus sign is the likely cause and
	# it changes the solution, but someone may mean it, and quietly reverting to
	# Standard would be a worse surprise than saying so.
	if scaled >= 0.0:
		print("[ERROR] DT2MS is " + dt2ms + ", which is not negative.")
		print("        Mass scaling behaves differently for positive values -"
		      " check this is what you meant.")

	return level, size, maxlvl, dt2ms


def _title(level, size, maxlvl, dt2ms):
	"""The deck title: the level's name and the three numbers behind it.

	The name alone is not enough. Every Custom run would carry the same title in
	glstat, d3hsp and messag, and a preset can be redefined - Lecture may change
	after run 17 - which would leave an old LECTURE title ambiguous. A size of
	"" means it was not recorded, and is left out rather than guessed.
	"""
	parts = ["EXPLICIT_SHEET_METAL_FORMING", level.upper().replace(" ", "_")]
	if size:
		parts.append("BLANK" + size)
	parts.append("MAXLVL" + maxlvl)
	parts.append("DT2MS" + dt2ms)
	# *TITLE is one character field spanning the whole card, so 80 columns -
	# LS-DYNA R16 Vol I, 45-1.
	return "_".join(parts)[:80]


def _write_deck(directory, model_filename, level_values):
	"""Copy the master deck beside the exported model and set it up for it.

	The model and the solver settings are produced by completely different
	means - ANSA writes the model, this writes the CONTROL cards - and this is
	the one place the two are made to agree.
	"""
	level, size, maxlvl, dt2ms = level_values
	template = SCRIPT_DIR + DECK_TEMPLATE

	try:
		lines = io.open(template, encoding="utf-8").read().split("\n")
	except IOError:
		print("[ERROR] Could not read " + template)
		print("        Run install.ps1 - the master decks live next to the"
		      " scripts now.")
		return

	# TITLE, so that glstat, d3hsp and messag all say what produced them.
	title = _card_line(lines, "*TITLE")
	if title >= 0 and title + 1 < len(lines):
		lines[title + 1] = _title(level, size, maxlvl, dt2ms)

	# INCLUDE: the model this deck is written next to. Bare filename, since the
	# two end up in the same folder.
	include = _card_line(lines, "*INCLUDE")
	if include >= 0:
		for i in range(include + 1, len(lines)):
			if not lines[i].startswith("$"):
				lines[i] = model_filename
				break

	ok = _set_field(lines, "*CONTROL_TIMESTEP", "DT2MS", dt2ms)
	ok = _set_field(lines, "*CONTROL_ADAPTIVE", "MAXLVL", maxlvl) and ok

	old_endtim = _get_field(lines, "*CONTROL_TERMINATION", "ENDTIM")
	old_adpfreq = _get_field(lines, "*CONTROL_ADAPTIVE", "ADPFREQ")
	end_time = _stroke_end_time()

	if end_time:
		ok = _set_field(lines, "*CONTROL_TERMINATION", "ENDTIM",
		                _num(end_time)) and ok
		# ADPFREQ is a time interval, not a count, so it has to move with
		# ENDTIM or a shortened stroke silently gets fewer adaptive checks.
		# The ratio is taken from the template rather than hard-coded here, so
		# editing the deck keeps deciding it.
		try:
			checks = float(old_endtim) / float(old_adpfreq)
			ok = _set_field(lines, "*CONTROL_ADAPTIVE", "ADPFREQ",
			                _num(end_time / checks)) and ok
		except (TypeError, ValueError, ZeroDivisionError):
			print("[ERROR] Could not scale ADPFREQ - left at "
			      + str(old_adpfreq))
	else:
		print("[ERROR] No prescribed motion in the model - ENDTIM left at "
		      + str(old_endtim) + " s.")
		print("        Run step 5, Create motion of punch, and export again.")

	if not ok:
		print("[ERROR] " + DECK_TEMPLATE + " was NOT written - the solve"
		      " settings in it would have been wrong.")
		return

	path = os.path.join(directory, DECK_TEMPLATE)
	if not _replace(path, "\n".join(lines), template):
		return

	print("[OK] Wrote " + path + " (replaced any earlier copy)")
	print("     " + level + ": MAXLVL " + maxlvl + ", DT2MS " + dt2ms
	      + ", ENDTIM " + str(_get_field(lines, "*CONTROL_TERMINATION", "ENDTIM"))
	      + " s")
	print("     Solve this file, not " + model_filename + ".")


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


def _confirm_export(problems):
	"""Ask whether to export a model with a part nothing drives.

	Not a refusal - a half-built model is a legitimate thing to export and look
	at - but not something to let past on a console line either: the run would
	terminate normally and simply be wrong. So the student is made to choose.

	If the question cannot be put (no GUI, an ANSA that refuses the window), the
	export goes ahead rather than being blocked by a dialog nobody can answer.
	The console still carries every line.
	"""
	text = ("<b>Nothing drives these parts:</b><br><br>"
	        + "<br>".join(problems)
	        + "<br><br>LS-DYNA will not complain: the run finishes normally and"
	        " the result is simply wrong.<br><br>"
	        "Export anyway, or cancel and set them up first?")
	try:
		window = guitk.BCMessageWindowCreate(guitk.constants.BCMessageBoxWarning,
		                                     text, True)
		guitk.BCMessageWindowSetAcceptButtonText(window, "Export anyway")
		guitk.BCMessageWindowSetRejectButtonText(window, "Cancel export")
		return guitk.BCMessageWindowExecute(window) == guitk.constants.BCRetKey
	except Exception:
		print("[ERROR] Could not show the confirmation - exporting anyway.")
		return True


def _browse(button, data):
	"""Pick the export folder. An empty start opens the last folder used."""
	chosen = utils.SelectSaveDir(guitk.BCLineEditGetText(data))
	if chosen:
		guitk.BCLineEditSetText(data, chosen)
	return 0


def _driven_pids(keyword):
	"""The parts every entity of a keyword acts on, as text.

	The PID field is written as a number by steps 5 and 6, but a card read back
	from a deck can hand it over as text or as a name, so both the id and the
	name are matched against this set rather than assuming one shape.
	"""
	driven = set()
	for entity in base.CollectEntities(constants.LSDYNA, None, keyword, False):
		try:
			value = base.GetEntityCardValues(constants.LSDYNA, entity, ("PID",)).get("PID")
		except Exception:
			value = None
		if value in (None, ""):
			continue
		text = str(value).strip()
		driven.add(text)
		try:
			driven.add(str(int(float(text))))
		except (TypeError, ValueError):
			pass
	return driven


def _check_parts_are_driven():
	"""A blankholder with no clamp force, or a punch with no motion.

	Prints every one it finds and returns them as short lines for the
	confirmation dialog, so the console keeps the detail and the dialog stays
	readable. An empty list means there is nothing to ask about.
	"""
	pids = base.CollectEntities(constants.LSDYNA, None, "SECTION_SHELL", False)
	clamped = _driven_pids("LOAD")
	moved = _driven_pids("BOUNDARY_PRESCRIBED_MOTION")
	problems = []

	for pid in pids:
		name = str(pid._name)
		known = (str(pid._id), name)

		if BLANKHOLDER_PATTERN.match(name):
			if not [k for k in known if k in clamped]:
				print("[ERROR] '" + name + "' has no clamp force - run step 6 for it.")
				print("        It would be free to be pushed aside, and the sheet")
				print("        would not be held.")
				problems.append(name + " has no clamp force (step 6)")
		elif PUNCH_PATTERN.match(name):
			if not [k for k in known if k in moved]:
				print("[ERROR] '" + name + "' has no prescribed motion - run step 5 for it.")
				print("        It would stand still for the whole run.")
				problems.append(name + " has no prescribed motion (step 5)")

	return problems


def cleanup_output():

	# Only a default. The student picks where the export goes - the model does
	# not have to have been saved for this step to work.
	current_db_path = base.DataBaseName()
	base_name = os.path.splitext(os.path.basename(current_db_path))[0]
	db_directory = os.path.dirname(current_db_path)

	# Read once, here, so the label and the deck cannot disagree and so a
	# missing level is reported once rather than twice.
	level_values = _stored_level()

	TopWindow = guitk.BCWindowCreate("Export LS-Dyna file.", guitk.constants.BCOnExitDestroy)

	BCButtonGroup_1 = guitk.BCButtonGroupCreate(TopWindow, "Settings", guitk.constants.BCVertical)
	BCLabel_1 = guitk.BCLabelCreate(BCButtonGroup_1, "Folder:")
	FolderRow = guitk.BCBoxLayoutCreate(BCButtonGroup_1, guitk.constants.BCHorizontal)
	BCLineEdit_2 = guitk.BCLineEditCreate(FolderRow, db_directory)
	BCPushButton_1 = guitk.BCPushButtonCreate(FolderRow, "Browse...", _browse, BCLineEdit_2)
	BCLabel_2 = guitk.BCLabelCreate(BCButtonGroup_1, "Filename:")
	BCLineEdit_1 = guitk.BCLineEditCreate(BCButtonGroup_1, base_name)
	BCLabel_3 = guitk.BCLabelCreate(BCButtonGroup_1, "")
	BCLabel_4 = guitk.BCLabelCreate(BCButtonGroup_1,
		"Solve level: " + level_values[0] + " (set in step 2)")
	BCLabel_5 = guitk.BCLabelCreate(BCButtonGroup_1,
		"Blank " + (level_values[1] + " mm" if level_values[1] else "size not recorded")
		+ ", MAXLVL " + level_values[2] + ", DT2MS " + level_values[3])
	BCSpacer_1 = guitk.BCSpacerCreate(BCButtonGroup_1)
	BCSpacer_2 = guitk.BCSpacerCreate(TopWindow)
	BCDialogButtonBox_1 = guitk.BCDialogButtonBoxCreate(TopWindow)

	guitk.BCWindowSetAcceptFunction(TopWindow, _ok_pressed,
		[BCLineEdit_1, level_values, BCLineEdit_2])

	guitk.BCShow(TopWindow)



def _ok_pressed(w, data):
	directory = guitk.BCLineEditGetText(data[2]).strip()
	name = guitk.BCLineEditGetText(data[0]).strip()

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

	# Before anything is written, so it is not lost below the file paths.
	problems = _check_parts_are_driven()
	if problems and not _confirm_export(problems):
		print("[ERROR] Export cancelled - nothing was written.")
		# True closes the dialog: cancelling means going to step 5 or 6, and
		# step 7 is one click away again afterwards.
		return True

	ret_val = base.Compress({"__MATERIALS__": 1, "Sets": 0, "F.E.": 1})
	if ret_val == 0: print("[OK] Compress")
	else: print("[ERROR] Compress")

	model_filename = name + ".k"
	filename = os.path.join(directory, model_filename)

	ret_val = base.OutputLSDyna(filename=filename, mode="all", comment_output_field_labels="on")

	if ret_val == 1: print("[OK] Export")
	else: print("[ERROR] Export")

	# The deck goes out whatever the export did, so a student who hits a model
	# problem still has a matching deck once they have fixed it.
	_write_deck(directory, model_filename, data[1])

	return True


if __name__ == '__main__':
	cleanup_output()
