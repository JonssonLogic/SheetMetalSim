# ANSA_TRANSL.py
# This file is executed upon ANSA startup.
# Place it in your <ansa_install_dir>/scripts/ directory.

import ansa
from ansa import utils
from os.path import expanduser


# Define the full path to the directory where your external scripts are stored.
# It's recommended to use an absolute path to avoid issues.
# Example path: 'C:/Users/YourUser/ansa_scripts'
# ansa.ImportCode() automatically adds the script's directory to the Python path.

# scripts_path = "C:\\Users\\CV\\KallePythonTemp\\SetPropertyName.py"
# ansa.ImportCode(scripts_path)

# # Now you can import your external modules
# try:
#     import SetPropertyName
# except ImportError as e:
#     print(f"Error importing external script: {e}")
#     # Assign a dummy function or handle the error gracefully
#     class DummyModule:
#         def run_naming(*args, **kwargs):
#             print("Could not load 'cad_cleanup_script'. Please check the path.")
#     PID_naming_script = DummyModule()
    

# --- Button Definition 1: Calling an External Script ---
@ansa.session.defbutton("Sheet metal forming","1. Open parts","Select name for the part after you import each file.")
    # image_file=utils.GetAnsaInstallationDir() + "/graphics/icons_32x32/geometry_heal.png"
def name_PID():
    """
    This function acts as a wrapper to call the main function
    from an external Python script.
    """
    print("Setting name...")
    # Call the function from the imported script
    # PID_naming_script.set_property_name()
    home = expanduser("~")
    script_path = home + "\\.BETA\\ANSA\\version_25.1.1\\3D-teknik\\SetPropertyName.py"
    ansa.ImportCode(script_path)
    SetPropertyName.set_property_name()
    print("Naming finished.")


# --- Button Definition 2 ---
@ansa.session.defbutton("Sheet metal forming", "2. Fix, mesh and check", "Fixes the geometry, creates the mesh and checks for penetrations.")
    # image_file=utils.GetAnsaInstallationDir() + "/graphics/icons_32x32/bolt.png"
def fix_mesh_check():

    print("Fix geometry, mesh, and check...")
    # Call the function from the imported script
    # PID_naming_script.set_property_name()
    home = expanduser("~")
    script_path = home + "\\.BETA\\ANSA\\version_25.1.1\\3D-teknik\\FixGeoAndMesh.py"
    ansa.ImportCode(script_path)
    FixGeoAndMesh.FixGeoMesh()
    print("Processing finished.")


# --- Button Definition 3 ---
@ansa.session.defbutton("Sheet metal forming", "3. Import materials", "Import the forming_materials.k file.")
    # image_file=utils.GetAnsaInstallationDir() + "/graphics/icons_32x32/bolt.png"
def import_mats1():

    print("Import materials...")
    # Call the function from the imported script
    # PID_naming_script.set_property_name()
    home = expanduser("~")
    script_path = home + "\\.BETA\\ANSA\\version_25.1.1\\3D-teknik\\ImportMaterials.py"
    ansa.ImportCode(script_path)
    ImportMaterials.main()
    print("Processing finished.")


# --- Button Definition 4 ---
@ansa.session.defbutton("Sheet metal forming", "4. Create contacts", "Creates contact between the Blank and the rest of the components.")
    # image_file=utils.GetAnsaInstallationDir() + "/graphics/icons_32x32/bolt.png"
def contact_creation():

    print("Creating contacts...")
    # Call the function from the imported script
    # PID_naming_script.set_property_name()
    home = expanduser("~")
    script_path = home + "\\.BETA\\ANSA\\version_25.1.1\\3D-teknik\\CreateContacts.py"
    ansa.ImportCode(script_path)
    CreateContacts.the_function() #Runs the script
    print("Processing finished.")


# --- Button Definition 5 ---
@ansa.session.defbutton("Sheet metal forming", "5. Create motion of punch", "Creates a prescribed motion for punches.")
    # image_file=utils.GetAnsaInstallationDir() + "/graphics/icons_32x32/bolt.png"
def create_motion():

    print("Creating motion...")
    # Call the function from the imported script
    # PID_naming_script.set_property_name()
    home = expanduser("~")
    script_path = home + "\\.BETA\\ANSA\\version_25.1.1\\3D-teknik\\CreatePrescribedMotion.py"
    ansa.ImportCode(script_path)
    CreatePrescribedMotion.punch_movement() #Runs the script
    print("Processing finished.")


# --- Button Definition 6 ---
@ansa.session.defbutton("Sheet metal forming", "6. Create clamp force", "Creates a clamping force for the Blank Holder.")
    # image_file=utils.GetAnsaInstallationDir() + "/graphics/icons_32x32/bolt.png"
def create_clampforce():

    print("Creating load...")
    # Call the function from the imported script
    # PID_naming_script.set_property_name()
    home = expanduser("~")
    script_path = home + "\\.BETA\\ANSA\\version_25.1.1\\3D-teknik\\CreateClampForce.py"
    ansa.ImportCode(script_path)
    CreateClampForce.clamp_force() #Runs the script
    print("Processing finished.")


# --- Button Definition 7 ---
@ansa.session.defbutton("Sheet metal forming", "7. Output .k-file", "Cleans up unused data and outputs the setup to LS-Dyna format.")
    # image_file=utils.GetAnsaInstallationDir() + "/graphics/icons_32x32/bolt.png"
def compress_output():

    print("Outputing...")
    # Call the function from the imported script
    # PID_naming_script.set_property_name()
    home = expanduser("~")
    script_path = home + "\\.BETA\\ANSA\\version_25.1.1\\3D-teknik\\OutputToLSDyna.py"
    ansa.ImportCode(script_path)
    OutputToLSDyna.cleanup_output() #Runs the script
    print("Processing finished.")


# --- Button Definition 8 ---
@ansa.session.defbutton("Spring back", "1. Import forming results", "Imports the dynain-file and sets a fixed point.")
    # image_file=utils.GetAnsaInstallationDir() + "/graphics/icons_32x32/bolt.png"
def import_forming():

    print("Importing...")
    # Call the function from the imported script
    # PID_naming_script.set_property_name()
    home = expanduser("~")
    script_path = home + "\\.BETA\\ANSA\\version_25.1.1\\3D-teknik\\OpenDynaIn.py"
    ansa.ImportCode(script_path)
    OpenDynaIn.main() #Runs the script
    print("Processing finished.")


# --- Button Definition 9 ---
@ansa.session.defbutton("Spring back", "2. Import materials", "Import the forming_materials.k file.")
    # image_file=utils.GetAnsaInstallationDir() + "/graphics/icons_32x32/bolt.png"
def import_mats2():

    print("Import materials...")
    # Call the function from the imported script
    # PID_naming_script.set_property_name()
    home = expanduser("~")
    script_path = home + "\\.BETA\\ANSA\\version_25.1.1\\3D-teknik\\ImportMaterials.py"
    ansa.ImportCode(script_path)
    ImportMaterials.main()
    print("Processing finished.")


# --- Button Definition 10 ---
@ansa.session.defbutton("Spring back", "3. Output .k-file", "Cleans up unused data and outputs the setup to LS-Dyna format.")
    # image_file=utils.GetAnsaInstallationDir() + "/graphics/icons_32x32/bolt.png"
def springback_output():

    print("Outputing...")
    # Call the function from the imported script
    # PID_naming_script.set_property_name()
    home = expanduser("~")
    script_path = home + "\\.BETA\\ANSA\\version_25.1.1\\3D-teknik\\OutputSpringbackToLSDyna.py"
    ansa.ImportCode(script_path)
    OutputSpringbackToLSDyna.cleanup_output() #Runs the script
    print("Processing finished.")


# --- Button Definition 11 ---
@ansa.session.defbutton("Deformed shape", "1. Import springback shape", "Imports the dynain-file.")
    # image_file=utils.GetAnsaInstallationDir() + "/graphics/icons_32x32/bolt.png"
def import_deformed():

    print("Importing...")
    # Call the function from the imported script
    # PID_naming_script.set_property_name()
    home = expanduser("~")
    script_path = home + "\\.BETA\\ANSA\\version_25.1.1\\3D-teknik\\OpenDynaInSpringback.py"
    ansa.ImportCode(script_path)
    OpenDynaInSpringback.main() #Runs the script
    print("Processing finished.")


# --- Button Definition 12 ---
# @ansa.session.defbutton("Deformed shape", "2. Create surface from mesh", "Creates surfaces from the elements.")
#     # image_file=utils.GetAnsaInstallationDir() + "/graphics/icons_32x32/bolt.png"
# def create_surfacees():

#     print("Creating...")
#     # Call the function from the imported script
#     # PID_naming_script.set_property_name()
#     script_path = "C:\\Users\\CV\\KallePythonTemp\\CreateSurfaceFromFE.py"
#     ansa.ImportCode(script_path)
#     CreateSurfaceFromFE.main() #Runs the script
#     print("Processing finished.")