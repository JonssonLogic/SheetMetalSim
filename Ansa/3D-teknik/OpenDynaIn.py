# PYTHON script
import os
import ansa
from ansa import base, utils, constants

def main():
	
	files = utils.SelectOpenFile(0)
	if files: 
		print("[OK] File selected")
	else: 
		print("[ERROR] No file selected")
		return
	
	ret_val = base.InputLSDyna(filename=files[0])
	if ret_val==1: print("[OK] Open")
	else: 
		print("[ERROR] Failed to Open")
		return
	
	# Delete CONSTRAINED_ADAPTIVITY
	con = base.CollectEntities(constants.LSDYNA, None,  "CONSTRAINED_ADAPTIVITY")
	ret_val = base.DeleteEntity(con)
	if ret_val==0: print("[OK] Deleted constraints")
	
	
	# Get COG
	part = base.CollectEntities(constants.LSDYNA, None, "SECTION_SHELL")
	if part: print("Got part")
	else: print("No part")
	
	cog = base.Cog(part[0])
	if cog: print("Got COG")
	else: print("No COG")
	
	# Set Elform and NIP
	base.SetEntityCardValues(constants.LSDYNA, part[0], {'ELFORM': "16", 'NIP': "7", "DEFINED": "YES"})

	
	# Get node closest to COG
	nodes_of_part = base.CollectEntities(constants.LSDYNA, None, "NODE")
	if nodes_of_part: print("[OK] Got nodes")
	else: print("[ERROR] No nodes")
	
	closest_node = None
	min_distance_sq = float('inf')
	
	for node in nodes_of_part:
		node_pos = node.position
		distance_sq = (node_pos[0] - cog[0])**2 + (node_pos[1] - cog[1])**2 + (node_pos[2] - cog[2])**2
		
		if distance_sq < min_distance_sq:
			min_distance_sq = distance_sq
			closest_node = node
	
	if closest_node: 	print("[OK] Found node")
	else: print("[ERROR] No node found")
		
	# Create an SPC
	spc_name = "Fixed point"	
	spc_properties = {"Name": spc_name, "c": "123456", "N1": closest_node._id, "No.of.Nodes": "1"}
			
	new_spc = base.CreateEntity(constants.LSDYNA, "BOUNDARY_SPC", spc_properties)
	if new_spc: print("[OK] Created fixed point")
	else: print("[ERROR] No fix point created") 
	
	# Create set for exporting sprungback to CAD
	set_properties = {"Name": "SET_SPRINGBACK", "SID": 1}
	new_set = base.CreateEntity(constants.LSDYNA, "SET", set_properties)
	base.AddToSet(new_set, part[0])
	
	
	
	
	


if __name__ == '__main__':
	main()


