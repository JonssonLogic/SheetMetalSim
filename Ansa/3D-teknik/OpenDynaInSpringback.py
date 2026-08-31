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
	

if __name__ == '__main__':
	main()


