# PYTHON script
import os
import meta
from meta import utils, models, results, plot2d, windows

def import_forming_results():
	
	window_name_3plot = "MetaPost"
	deck = "DYNA"
	selected_files = utils.SelectOpenFile(0, "LS-Dyna Keyword (*.k)")
	main_model = models.LoadModel(window_name_3plot, selected_files[0], deck)
	
	directory = os.path.dirname(selected_files[0])
	d3plot_filepath = directory + "/d3plot"
	
	states = "all"
	data_disp = "Displacements"
	model_id = 0
	displacements = results.LoadAppendDeformations(model_id, d3plot_filepath, deck, states, data_disp)
	if displacements: print("[OK] Displacements")
	else: print("[ERROR] Displacements")
	
	data_major = "Strains,MajorPrincipal,MaxofInOut/AllLayers"
	major_strains = results.LoadAppendScalar(model_id, d3plot_filepath, deck, states, data_major)
	if major_strains: print("[OK] MajorPrincipal")
	else: print("[ERROR] MajorPrincipal")
	
	data_minor = "Strains,MinorPrincipal,MaxofInOut/AllLayers"
	minor_strains = results.LoadAppendScalar(model_id, d3plot_filepath, deck, states, data_minor)
	if minor_strains: print("[OK] MinorPrincipal")
	else: print("[ERROR] MinorPrincipal")
	
	data_thin = "ExtraVariables,Thinning(Original-Current),MaxofInOutMid"
	thinings = results.LoadAppendScalar(model_id, d3plot_filepath, deck, states, data_thin)
	if thinings: print("[OK] Thinning")
	else: print("[ERROR] Thinning")
	
	# Energy curve plot!
	d2plot_filepath = directory + "/binout*"
	utils.MetaCommand('xyplot create "Energy"')
	utils.MetaCommand('window active "Energy"')
	utils.MetaCommand('window shownormal "Energy"')
	utils.MetaCommand('window maximize "Energy"')
	utils.MetaCommand('xyplot loadtomodel active"')
	utils.MetaCommand('xyplot read lsdyna "Energy" "' + d2plot_filepath + '" glstat-Global ,  Kinetic_energy_(ke),Internal_energy_(ie),Sliding_interface_energy_(sie),Total_energy_(te)')
	utils.MetaCommand('xyplot curve rfunction newscale y "Energy" 1-4 0.001') # convert from mJ to J
	utils.MetaCommand('xyplot curve function userdef "Sliding work + Kinetic + Internal" "c4.x" "c3.y + c1.y + c2.y" "Energy"')
	utils.MetaCommand('xyplot axisoptions ylabel set "Energy" 0 "Energy [J]"')
	utils.MetaCommand('xyplot axisoptions xlabel set "Energy" 0 "Time [s]"')
	utils.MetaCommand('xyplot plotoptions legend on "Energy" 0')
	
	# Added mass curve plot!
	utils.MetaCommand('xyplot create "Added mass"')
	utils.MetaCommand('window active "Added mass"')
	utils.MetaCommand('window shownormal "Added mass"')
	utils.MetaCommand('window maximize "Added mass"')
	utils.MetaCommand('xyplot loadtomodel active"')
	utils.MetaCommand('xyplot read lsdyna "Added mass" "' + d2plot_filepath + '" glstat-Global , Added_mass_(am)')
	utils.MetaCommand('xyplot curve rfunction newscale y "Added mass" 1 1000000') # convert from ton to g
	utils.MetaCommand('xyplot axisoptions ylabel set "Added mass" 0 "Mass [g]"')
	utils.MetaCommand('xyplot axisoptions xlabel set "Added mass" 0 "Time [s]"')
	utils.MetaCommand('xyplot plotoptions legend on "Added mass" 0')
	


if __name__ == '__main__':
	import_forming_results()


