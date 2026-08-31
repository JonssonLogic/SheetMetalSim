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
	
	data_magni = "Displacements,Magnitude"
	disp_magni = results.LoadAppendScalar(model_id, d3plot_filepath, deck, states, data_magni)
	if disp_magni: print("[OK] MajorPrincipal")
	else: print("[ERROR] MajorPrincipal")
	
	utils.MetaCommand('disp scale multiplier 5.000000E+00')
	utils.MetaCommand('grstyle scalarfringe enable')

if __name__ == '__main__':
	import_forming_results()


