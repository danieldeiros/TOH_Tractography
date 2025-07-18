# Preliminaries

## Import necessary packages
def imports():
    import os
    os.environ["http_proxy"] = "http://dahernandez:34732b8f774d6def@ohswg.ottawahospital.on.ca:8080"
    os.environ["https_proxy"] = "http://dahernandez:34732b8f774d6def@ohswg.ottawahospital.on.ca:8080"
    import pydicom
    import subprocess
    from pathlib import Path
    import nibabel as nib
    from dipy.io import read_bvals_bvecs
    from dipy.core.gradients import gradient_table
    from dipy.io.image import load_nifti, save_nifti
    from dipy.reconst.shm import CsaOdfModel
    from dipy.direction import peaks_from_model
    from dipy.data import default_sphere
    from dipy.segment.mask import median_otsu
    from dipy.viz import actor, colormap, has_fury, window
    from dipy.tracking.stopping_criterion import ThresholdStoppingCriterion
    from dipy.reconst.dti import TensorModel
    from dipy.tracking.utils import random_seeds_from_mask, path_length
    from dipy.tracking.streamline import Streamlines
    from dipy.tracking.tracker import eudx_tracking
    from dipy.io.stateful_tractogram import Space, StatefulTractogram
    from dipy.io.streamline import save_trk
    from rt_utils import RTStructBuilder
    import matplotlib.pyplot as plt
    import numpy as np
    from collections import defaultdict
    import shutil
    import re
    import ants

## Create necessary functions
### Function to check if a folder path has all the required NIfTI files
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

def dicom_to_nifti(dicom_dir, nifti_dir):
    nifti_dir.mkdir(parents=True, exist_ok=True) # make folder for NIFTI if it doesnt exist yet

    # Create command for dcm2niix
    # -z y creates compressed (.gz) .nii files
    # -f %p_%s defines output file name as %p (protocol name(DICOM tag 0018, 1030)) with %s (series(DICOM tag 0020, 0011))
    # -o specifies the output directory of the NIfTI files
    cmd = [
        "dcm2niix",
        "-z", "y",
        "-f", "%p_%s",
        "-o", str(nifti_dir),
        str(dicom_dir)
    ]

    # Run this command in the terminal. Print any errors
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        print("Return code:", e.returncode)

    print("✅ DICOM files successfully converted to NIfTI")