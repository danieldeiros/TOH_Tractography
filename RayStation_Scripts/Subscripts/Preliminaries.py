# Preliminaries

## Import necessary packages
import os
os.environ["http_proxy"] = "http://dahernandez:34732b8f774d6def@ohswg.ottawahospital.on.ca:8080"
os.environ["https_proxy"] = "http://dahernandez:34732b8f774d6def@ohswg.ottawahospital.on.ca:8080"
import pydicom
import subprocess
from pathlib import Path
from collections import defaultdict
import shutil
import re

## Create necessary functions

# Function to check if a folder path has all the required NIfTI files
def check_nifti_folder(path, bval_bvec_expected):
    # First set flag to false
    valid_folder = False

    if path.is_dir():
        # Define flags for file types we need
        niigz_flag = False
        bval_flag = False
        bvec_flag = False
        for file_path in path.rglob("*"): # parses every file recursively
            if not file_path.is_file():
                continue
            if str(file_path).lower().endswith(".nii.gz"):
                niigz_flag = True
            elif str(file_path).lower().endswith(".bval"):
                bval_flag = True
            elif str(file_path).lower().endswith(".bvec"):
                bvec_flag = True

        if bval_bvec_expected:
            if niigz_flag and bval_flag and bvec_flag:
                valid_folder = True # Set flag to indicate folder is valid to proceed
                print("✅ NIfTI folder contains the necessary NIfTI files to proceed without conversion.")
            elif not niigz_flag and not bval_flag and not bvec_flag:
                print("❌ NIfTI folder does not contain any of the necessary NIfTI files.")
            else:
                incomplete = True # Set flag to indicate incomplete conversion
                print("⚠️ NIfTI folder contains some of the necessary NIfTI files. Please delete the folder's contents to avoid errors.")
        elif not bval_bvec_expected:
            if niigz_flag:
                valid_folder = True # Set flag to indicate folder is valid to proceed
                print("✅ NIfTI folder contains the necessary NIfTI file to proceed without conversion.")
            else:
                print("❌ NIfTI folder does not contain the necessary NIfTI files.")
    else:
        print("❌ NIfTI folder does not exist.")

    return valid_folder

# Function to extract file name from a given folder of NIfTI files
def get_fname(path):
    fname = [] # Set empty first
    for file_path in path.rglob("*"): # parses every file recursively
        # Extract file name without extension and add to fname if unique
        if str(file_path).lower().endswith(".nii.gz"): 
            if re.sub(r"\.nii\.gz$","", file_path.name) not in fname:
                fname.append(re.sub(r"\.nii\.gz$","", file_path.name)) 
        elif str(file_path).lower().endswith(".bval"):
            if re.sub(r"\.bval$","", file_path.name) not in fname:
                fname.append(re.sub(r"\.bval$","", file_path.name)) 
        elif str(file_path).lower().endswith(".bvec"):
            if re.sub(r"\.bvec$","", file_path.name) not in fname:
                fname.append(re.sub(r"\.bvec$","", file_path.name)) 

    if len(fname) > 1:
        print("❌ Too many NIfTI files in folder. Please only include NIfTI files of diffusion imaging MR scan.")
    elif len(fname) < 1:
        print("❌ No NIfTI files found in folder.")
    else:
        fname = fname[0]
        print("✅ File name succesfully acquired.")

    return fname

# Function to get exported RayStation file PATHS
def rs_get_paths(path):

    # Define lists to add file paths to
    CT_File_Paths = []
    RD_File_Paths = []
    RP_File_Paths = []
    RS_File_Paths = []
    MR_File_Paths = []

    for file in path.glob("*.dcm"): # Go through every file in folder (non-recursively)
        if file.is_file():
            try: # Determine what type of file it is
                if "CT" in file.name.upper() and pydicom.dcmread(file, stop_before_pixels=True).Modality == 'CT':
                    CT_File_Paths.append(file)
                elif "RD" in file.name.upper() and pydicom.dcmread(file, stop_before_pixels=True).Modality == 'RTDOSE':
                    RD_File_Paths.append(file)
                elif "RP" in file.name.upper() and pydicom.dcmread(file, stop_before_pixels=True).Modality == 'RTPLAN':
                    RP_File_Paths.append(file)
                elif "RS" in file.name.upper() and pydicom.dcmread(file, stop_before_pixels=True).Modality == 'RTSTRUCT':
                    RS_File_Paths.append(file)
                elif "MR" in file.name.upper() and pydicom.dcmread(file, stop_before_pixels=True).Modality == 'MR':
                    MR_File_Paths.append(file)
                else:
                    print(f"Unknown DICOM file {file.name}")
            except:
                print(f"Skipped invalid DICOM: {file.name}")

    print(f"Found {len(CT_File_Paths)+len(RD_File_Paths)+len(RP_File_Paths)+len(RS_File_Paths)+len(MR_File_Paths)} valid DICOM files")

    file_paths = {
        "CT_File_Paths" : CT_File_Paths,
        "RD_File_Paths" : RD_File_Paths,
        "RP_File_Paths" : RP_File_Paths,
        "RS_File_Paths" : RS_File_Paths,
        "MR_File_Paths" : MR_File_Paths
    }

    return file_paths

# Function to get exported RayStation files
def rs_get_info(path):

    # Define lists to add file paths to
    CT_File_Paths = []
    RD_File_Paths = []
    RP_File_Paths = []
    RS_File_Paths = []
    MR_File_Paths = []

    # Define lists to add file info to
    CT_Files = []
    RD_Files = []
    RP_Files = []
    RS_Files = []
    MR_Files = []

    for file in path.glob("*.dcm"):
        if file.is_file():
            # print(f"Found file: {file.name}")
            try:
                if "CT" in file.name.upper() and pydicom.dcmread(file, stop_before_pixels=True).Modality == 'CT':
                    CT_Files.append(pydicom.dcmread(file)) 
                    CT_File_Paths.append(file)
                elif "RD" in file.name.upper() and pydicom.dcmread(file, stop_before_pixels=True).Modality == 'RTDOSE':
                    RD_Files.append(pydicom.dcmread(file))
                    RD_File_Paths.append(file)
                elif "RP" in file.name.upper() and pydicom.dcmread(file, stop_before_pixels=True).Modality == 'RTPLAN':
                    RP_Files.append(pydicom.dcmread(file))
                    RP_File_Paths.append(file)
                elif "RS" in file.name.upper() and pydicom.dcmread(file, stop_before_pixels=True).Modality == 'RTSTRUCT':
                    RS_Files.append(pydicom.dcmread(file))
                    RS_File_Paths.append(file)
                elif "MR" in file.name.upper() and pydicom.dcmread(file, stop_before_pixels=True).Modality == 'MR':
                    MR_Files.append(pydicom.dcmread(file))
                    MR_File_Paths.append(file)
                else:
                    print(f"Unknown DICOM file {file.name}")
            except:
                print(f"Skipped invalid DICOM: {file.name}")

    print(f"Found {len(CT_Files)+len(RD_Files)+len(RP_Files)+len(RS_Files)+len(MR_Files)} valid DICOM files")

    file_paths = {
        "CT_File_Paths" : CT_File_Paths,
        "RD_File_Paths" : RD_File_Paths,
        "RP_File_Paths" : RP_File_Paths,
        "RS_File_Paths" : RS_File_Paths,
        "MR_File_Paths" : MR_File_Paths
    }

    file_info = {
        "CT_Files" : CT_Files,
        "RD_Files" : RD_Files,
        "RP_Files" : RP_Files,
        "RS_Files" : RS_Files,
        "MR_Files" : MR_Files
    }

    return file_info, file_paths

# Function to convert from DICOM to NIfTI
def dicom_to_nifti(dicom_dir, nifti_dir):

    nifti_dir.mkdir(parents=True, exist_ok=True) # make folder for NIFTI if it doesnt exist yet

    # Create command for dcm2niix
    # -z y creates compressed (.gz) .nii files
    # -f %p_%s defines output file name as %p (protocol name(DICOM tag 0018, 1030)) with %s (series(DICOM tag 0020, 0011))
    # -o specifies the output directory of the NIfTI files
    cmd = [
        # "dcm2niix",
        "V:/Common/Staff Personal Folders/DanielH/RayStation_Scripts/Tractography/Subscripts/dcm2niix/dcm2niix.exe",
        "-z", "y",
        "-f", "%p_%s",
        "-o", str(nifti_dir),
        str(dicom_dir)
    ]

    print("Running command:", cmd)
    # Run this command in the terminal. Print any errors
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        print("Return code:", e.returncode)

    print("✅ DICOM files successfully converted to NIfTI")

# Function to define base directory to be used
def get_base_dir():
    ## Base directory to be used
    base_dir = Path("V:/Common/Staff Personal Folders/DanielH/DICOM_Files/TractographyPatient/Case 1 RS/")
    if base_dir.is_dir():
        print("Base folder: ", base_dir)
        return base_dir
    else:
        raise ValueError(f"Could not find folder: {base_dir}")

# Function to get diffusion MRIs    
def get_relevant_files(base_dir):
    # Define folder containing raw DICOM files
    dicom_raw_dir = base_dir / "combined"

    # Define dictionary to contain files with a given UID
    series_counts = defaultdict(list)

    FA_flag = False # Set a flag to check if FA is found in any of the folder's file's SeriesDescriptions

    for file_path in dicom_raw_dir.rglob("*"): # parses every file recursively
        if not file_path.is_file():
            continue
        try:
            # Try to read as DICOM using force=True
            ds = pydicom.dcmread(file_path, stop_before_pixels=True, force=True)

            uid = getattr(ds, "SeriesInstanceUID", None) # Get UID
            if uid: # if UID found, add to series_counts
                series_counts[uid].append(file_path)

            if "FA" in str(getattr(ds, "SeriesDescription", None)).upper():
                FA_flag = True # Set FA flag to true if FA found in Series Description
                
        except Exception as e:
            print(f"Skipping {file_path.name}: {e}")


    # Print whether FA flag true or false
    if FA_flag:
        print("\n✅ FA found in SeriesDescription of at least one file in folder. Folder valid for tractography")
    else:
        print("\n❌ No FA found in SeriesDescription of any file in folder. Folder NOT valid for tractography")

    # Print UID counts
    print("\nFound SeriesInstanceUIDs:")
    for uid, files in series_counts.items():
        print(f"{uid} - {len(files)} files")

    # Identify most populous UID
    if series_counts:
        most_populous_uid = max(series_counts, key=lambda k: len(series_counts[k]))
        print(f"\nMost populous UID: {most_populous_uid} ({len(series_counts[most_populous_uid])} slices)")
        relevant_files = series_counts[most_populous_uid] # assign files in most populous uid to relevant files
        return relevant_files
    else:
        raise ValueError("\nNo valid DICOMs found.")

# Function     
def copy_relevant_files(base_dir, relevant_files):
    output_dir = base_dir / "DICOM"
    output_dir.mkdir(parents=True, exist_ok=True) # make folder for derived relevant DICOM files if it doesnt exist yet

    for file_path in relevant_files:
        try:
            destination_path = output_dir / file_path.name # joins variables as path. (not division since path variable is involved)
            if destination_path.is_file(): continue # Skip if path already has file
            shutil.copy2(file_path, destination_path) # Copy file to folder if path doesn't have file
        except Exception as e:
            print(f"Unable to copy {file_path.name}: {e}")

    return output_dir

