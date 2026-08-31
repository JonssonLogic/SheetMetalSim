# PYTHON script
import os
import ansa
from ansa import base, utils


def main():
	
	files = utils.SelectOpenFile(0)
	if files: 
		print("[OK] File selected")
	else: 
		print("[ERROR] No file selected")
		return
	
	ret_val = base.InputLSDyna(filename=files[0])
	if ret_val==1: print("[OK] Materials imported")
	else: print("[ERROR] Failed to import materials")


if __name__ == '__main__':
	main()


