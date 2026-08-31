# PYTHON script
import os
import ansa
from ansa import base, utils, constants

def main():
	
	elements = base.CollectEntities(constants.LSDYNA, None, "NODE", False)
	
	ret_val = base.SurfacesFit(elements)
	if ret_val: print("success!")
	else: print("fail!")


if __name__ == '__main__':
	main()


