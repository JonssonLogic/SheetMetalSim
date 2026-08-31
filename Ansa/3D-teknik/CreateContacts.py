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
CONTACT_TYPE = "FORMING_NODES_TO_SURFACE"

# True  -> MST = -(blank thickness + MST_CLEARANCE) on every contact
# False -> leave the optional card blank, so LS-DYNA uses the true thicknesses
#
# Currently False. A negative MST is only documented for the *CONTACT_TIED_*
# options; for forming contacts it is undocumented, and 1.6 mm of tool contact
# thickness against a 1.5 mm blank is a large standoff. Set True to restore the
# original specification.
USE_MST = False

MST_CLEARANCE = 0.1


def _master_thickness(blank):
	"""MST for the tool side of every contact: -(blank thickness + 0.1).

	Negative and explicit, so the standoff is set deliberately instead of
	being inherited from whatever T1 the student typed for each tool.
	"""
	values = base.GetEntityCardValues(constants.LSDYNA, blank, ("T1",))
	try:
		thickness = float(values["T1"])
	except (KeyError, TypeError, ValueError):
		thickness = 0.0

	if thickness <= 0.0:
		print("[ERROR] Blank has no thickness (T1). Set it in '1. Open parts'.")
		return None
	return -round(thickness + MST_CLEARANCE, 6)


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

	# Create the springback set
	set_properties = {"Name": "SET_SPRINGBACK", "SID": 1}
	new_set = base.CreateEntity(constants.LSDYNA, "SET", set_properties)
	base.AddToSet(new_set, blank_part)

	for pid in tools:

		contact_name = "".join(["Contact blank-",pid._name])
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
