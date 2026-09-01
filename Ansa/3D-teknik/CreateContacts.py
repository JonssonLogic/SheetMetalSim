import ansa
from ansa import constants, base

BLANK_NAME = "blank"

# --- contact tuning ---------------------------------------------------------
# Two knobs, because the first LS-DYNA runs showed nodes at the initial contact
# areas being pushed further than they should be, and both of these changed at
# the same time as that appeared. Keeping them switchable makes A/B testing a
# one-line edit instead of a code change.

# "FORMING_NODES_TO_SURFACE" or "FORMING_ONE_WAY_SURFACE_TO_SURFACE"
#
# Node-to-surface lets the sheet dip into the tool between nodes, which is what
# keeps a 1st order element from spiking as it bends round a radius. The cost
# is that the penalty force lands on single slave nodes, so anything too deep
# shows up as an isolated dimple rather than being spread over a segment.
# Valid FORMING types (LS-DYNA R16 Vol I). There is no
# FORMING_ONE_WAY_NODES_TO_SURFACE - NODES_TO_SURFACE is already one-way, since
# only the slave nodes are ever checked against the master segments.
#
#   FORMING_NODES_TO_SURFACE            blank nodes vs tool segments
#   FORMING_ONE_WAY_SURFACE_TO_SURFACE  blank segments vs tool segments  <- v2025
#   FORMING_SURFACE_TO_SURFACE          symmetric
CONTACT_TYPE = "FORMING_NODES_TO_SURFACE"

# Nothing in the CAD accounts for the sheet. The die, blankholder and punch are
# built on the same surfaces as the blank - at full stroke the punch coincides
# with the die exactly - so the contact has to create the entire gap the sheet
# runs in. MST is what does that, and it is not optional.
USE_MST = True

# Clearance on top of the sheet thickness, so MST = -(t + TOOL_CLEARANCE).
TOOL_CLEARANCE = 0.1


def _master_thickness(blank):
	"""MST for the tool side of every contact: -(blank thickness + clearance).

	LS-DYNA R16 Vol I, *CONTACT General Remarks, remark 10:

	    For "Forming" contact, the surface thickness of SURFB is ignored (SURFB
	    should be the rigid tooling while SURFA should be the blank).
	    Furthermore, SURFB can be offset away from the blank by setting a
	    negative (meaning opposite of the positive normal of the SURFB surface)
	    value for SBST. This offsets SURFB from the surface midplane by
	    |SBST|/2 in the direction opposite to the SURFB positive normal
	    direction. A tool and die can be quickly offset (virtually, not
	    physically) with this field.

	Two consequences, both measured the hard way:

	  * A POSITIVE MST does nothing at all - the tool thickness is ignored. Runs
	    with MST = +1.6 and MST = +0.1 gave 3.89e6 N and 3.86e6 N at t=0, i.e.
	    identical, because both meant "no offset".
	  * The sign is what activates the feature, and the offset is |MST|/2. With
	    |MST| = t + clearance that is the blank's half thickness plus half the
	    clearance, which is exactly the room the tool has to give up.

	The offset direction is "opposite the SURFB positive normal", so it depends
	on the tool normals FixGeoAndMesh sets. Those point at the blank, so the
	offset moves each tool away from it. A tool oriented the wrong way would be
	offset INTO the sheet instead - which is why step 2's orientation work is
	load-bearing rather than cosmetic.

	SURFA (the blank) keeps its true thickness - that side is not ignored.
	"""
	values = base.GetEntityCardValues(constants.LSDYNA, blank, ("T1",))
	try:
		thickness = float(values["T1"])
	except (KeyError, TypeError, ValueError):
		thickness = 0.0

	if thickness <= 0.0:
		print("[ERROR] Blank has no thickness (T1). Set it in '1. Open parts'.")
		return None

	mst = -round(thickness + TOOL_CLEARANCE, 6)
	print("[OK] Blank %.3f mm -> MST %.3f, tools offset %.3f mm away from the blank"
	      % (thickness, mst, abs(mst) / 2.0))
	return mst


CONTACT_PREFIX = "Contact blank-"
SPRINGBACK_SET = "SET_SPRINGBACK"


def _clear_previous():
	"""Remove what a previous run of this step created.

	Without this, running step 4 twice leaves two sets of contacts and a second
	SET_SPRINGBACK sharing SID 1 - which would quietly break the PSID reference
	in *INTERFACE_SPRINGBACK_LSDYNA.
	"""
	stale = [c for c in base.CollectEntities(constants.LSDYNA, None, "CONTACT")
	         if str(c._name).startswith(CONTACT_PREFIX)]
	stale += [x for x in base.CollectEntities(constants.LSDYNA, None, "SET")
	          if str(x._name) == SPRINGBACK_SET]
	if not stale:
		return
	try:
		base.DeleteEntity(stale)
		print("[OK] Removed " + str(len(stale)) + " entities from a previous run")
	except Exception as e:
		print("[ERROR] Could not remove previous contacts: " + repr(e))
		print("        Delete them by hand before re-running, or you will get duplicates.")


def the_function():

	# Contacts here are part based - SSTYP/MSTYP = "3: Part id" - so the cards
	# reference parts, not elements. Nothing below needs a mesh, and nothing
	# below depends on shell orientation. Getting the tool normals pointing at
	# the blank is step 2's job and step 2 reports on it per part; re-checking
	# it here only duplicated those rules in a second place and blocked models
	# that were actually fine.
	pids = base.CollectEntities(constants.LSDYNA, None, "SECTION_SHELL", False)				# Select all pids

	if not pids:
		print("No parts, import geometry!")
		return

	blank_index = [i for i,  pid in enumerate(pids) if pid._name == BLANK_NAME]

	if not blank_index:
		print("No blank!")
		return
	blank_index = blank_index[0]
	blank_part = pids[blank_index]
	tools = [pid for pid in pids if pid._name != BLANK_NAME]

	# MST is derived from the blank's thickness, and a silently wrong MST gives
	# a run that completes and is simply wrong - so still guard it when used.
	mst = None
	if USE_MST:
		mst = _master_thickness(blank_part)
		if mst is None:
			return

	_clear_previous()

	# Create the springback set
	set_properties = {"Name": SPRINGBACK_SET, "SID": 1}
	new_set = base.CreateEntity(constants.LSDYNA, "SET", set_properties)
	base.AddToSet(new_set, blank_part)

	for pid in tools:

		contact_name = "".join([CONTACT_PREFIX, pid._name])
		# NODES_TO_SURFACE, not ONE_WAY_SURFACE_TO_SURFACE: only the blank's
		# nodes are checked against the tool, so an element's mid-span is free
		# to dip slightly into the tool. A 1st order element cannot curve, and
		# resisting penetration from both sides makes its corners dig into the
		# die radius and the penalty force spike.
		contact_properties = {"Name": contact_name, "TYPE": CONTACT_TYPE, "SSTYP": "3: Part id", "MSTYP": "3: Part id", "SSID": pids[blank_index]._id, "MSID": pid._id, "FS": 0.125, "FD": 0.125, "DC": 0.0001, "VDC": 20}
		if mst is not None:
			contact_properties["MST"] = mst

		new_contact = base.CreateEntity(constants.LSDYNA, "CONTACT", contact_properties)

		if new_contact:
			print(f"Successfully created contact '{new_contact._name}': {CONTACT_TYPE}, MST = {mst}")
		else:
			print("Failed to create the contact.")


if __name__ == '__main__':
	the_function()
