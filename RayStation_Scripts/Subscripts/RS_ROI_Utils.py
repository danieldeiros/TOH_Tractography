# Functions for obtaining ROIs from RayStation

## Import necessary packages
import os
os.environ["http_proxy"] = "http://dahernandez:34732b8f774d6def@ohswg.ottawahospital.on.ca:8080"
os.environ["https_proxy"] = "http://dahernandez:34732b8f774d6def@ohswg.ottawahospital.on.ca:8080"
import nibabel as nib
from dipy.io.image import load_nifti
from rt_utils import RTStructBuilder
import numpy as np
import shutil
import ants

# Import necessary functions
from Subscripts.Preliminaries import rs_get_paths, dicom_to_nifti, check_nifti_folder, get_fname

# Check if necessary folders exist and if they contain files required
def rs_folders(base_dir):
    # Define Paths
    rs_dir = base_dir / "RayStation" # Folder containing RayStation (RS) exports
    rs_ct_dcm_dir = rs_dir / "CT_DICOM" # Folder containg RS CT DICOM exports
    rs_mr_dcm_dir = rs_dir / "MR_DICOM" # Folder containing RS MR DICOM exports
    rs_rois_dir = rs_dir / "ROIs" # Folder containing RS ROIs (in RT struct)

    # Flags to indicate whether folders contain necessary files
    rs_ct_dcm_flag = False
    rs_mr_dcm_flag = False
    rs_rois_flag = False

    # Check if folders exist, if they do, check if they contain the appropriate file type
    # Delete files in folders if they don't contain what we want to prepare for the movement of files into the proper folders
    if rs_ct_dcm_dir.is_dir():
        file_paths = rs_get_paths(rs_ct_dcm_dir)
        rs_ct_dcm_flag = True if file_paths["CT_File_Paths"] else False
        if not rs_ct_dcm_flag:
            shutil.rmtree(rs_ct_dcm_dir)
        
    if rs_mr_dcm_dir.is_dir():
        file_paths = rs_get_paths(rs_mr_dcm_dir)
        rs_mr_dcm_flag = True if file_paths["MR_File_Paths"] else False
        if not rs_mr_dcm_flag:
            shutil.rmtree(rs_mr_dcm_dir)

    if rs_rois_dir.is_dir():
        file_paths = rs_get_paths(rs_rois_dir)
        rs_rois_flag = True if file_paths["RS_File_Paths"] else False
        if not rs_rois_flag:
            shutil.rmtree(rs_rois_dir)

    # Move files into their appropriate folders if necessary

    # Set flag to false first
    valid_folders = False

    if rs_ct_dcm_flag and rs_mr_dcm_flag and rs_rois_flag: # Continue if all folders valid
        valid_folders = True
    else: # Create folders for missing file types
        file_paths = rs_get_paths(rs_dir) # Get all file paths from original RayStation folder

        if not file_paths["CT_File_Paths"] and not file_paths["MR_File_Paths"] and not file_paths["RS_File_Paths"]:
            raise ValueError(f"No RayStation files found in {rs_dir}")
        
        if not rs_ct_dcm_flag:
            rs_ct_dcm_dir.mkdir(parents=True, exist_ok=True) # make folder if it doesn't exist
            for file in file_paths["CT_File_Paths"]: # Get all files and move to new folder
                # Move file to new folder
                shutil.move(file, rs_ct_dcm_dir)
            rs_ct_dcm_flag = True # Set flag to true when process complete

        if not rs_mr_dcm_flag:
            rs_mr_dcm_dir.mkdir(parents=True, exist_ok=True) # make folder if it doesn't exist
            for file in file_paths["MR_File_Paths"]: # Get all files and move to new folder
                # Move file to new folder
                shutil.move(file, rs_mr_dcm_dir)
            rs_mr_dcm_flag = True # Set flag to true when process complete

        if not rs_rois_flag:
            rs_rois_dir.mkdir(parents=True, exist_ok=True) # make folder if it doesn't exist
            for file in file_paths["RS_File_Paths"]: # Get all files and move to new folder
                # Move file to new folder
                shutil.move(file, rs_rois_dir)
            rs_rois_flag = True # Set flag to true when process complete

        valid_folders = True # Set flag to true when all processes complete

    return valid_folders

# Load necessary ROIs
def load_rois(base_dir, valid_folders):
    # First check if masks already exist
    if not valid_folders:
        raise ValueError("Folders containing RayStation files not validated.")

    # Define folders/paths
    rs_dir = base_dir / "RayStation" # Folder containing RayStation (RS) exports
    rs_ct_dcm_dir = rs_dir / "CT_DICOM" # Folder containg RS CT DICOM exports
    rs_mr_dcm_dir = rs_dir / "MR_DICOM" # Folder containing RS MR DICOM exports
    rs_rois_dir = rs_dir / "ROIs" # Folder containing RS ROIs (in RT struct)
    rs_rois_nii_dir = rs_dir / "ROIs_NIfTI" # Folder containing RS ROIs in NIfTI
    rs_rois_nii_dir.mkdir(parents=True, exist_ok=True) # make folder if it doesnt exist yet
    gtv_mask_nii_path = rs_rois_nii_dir / "gtv_mask.nii.gz" # define file path
    external_mask_nii_path = rs_rois_nii_dir / "external_mask.nii.gz" # define file path
    brain_mask_nii_path = rs_rois_nii_dir / "brain_mask.nii.gz" # define file path

    if gtv_mask_nii_path.is_file() and external_mask_nii_path.is_file() and brain_mask_nii_path.is_file():
        # Get masks from pre-defined files
        gtv_mask_nii = nib.load(gtv_mask_nii_path); gtv_mask = gtv_mask_nii.get_fdata()
        external_mask_nii = nib.load(external_mask_nii_path); external_mask = external_mask_nii.get_fdata()
        brain_mask_nii = nib.load(brain_mask_nii_path); brain_mask = brain_mask_nii.get_fdata()
        
    else:
        # Using RT_Utils package

        # Get path for RT Struct with ROIs
        file_paths = rs_get_paths(rs_rois_dir)
        rt_struct_path = file_paths["RS_File_Paths"][0] # Should only be one RT Struct file

        # Load RTStruct
        rtstruct = RTStructBuilder.create_from(dicom_series_path=rs_ct_dcm_dir, rt_struct_path=rt_struct_path)

        # List available ROI names
        print(f"ROI Names: {rtstruct.get_roi_names()}")

        # Choose ROI(s) to convert to NIfTI mask. Note that names must be exact
        gtv_name = [name for name in rtstruct.get_roi_names() if "GTV" in name] # Get names that contain GTV
        gtv_name = gtv_name[0] # Take first name from list of GTV names 
        gtv_mask = rtstruct.get_roi_mask_by_name(gtv_name)  # 3D binary numpy array
        gtv_mask = np.transpose(gtv_mask, (1, 0, 2)) # change to [x y z]
        gtv_mask = gtv_mask[:, ::-1, :] # flip y-axis to work properly for ANTs

        external_mask = rtstruct.get_roi_mask_by_name("External") # Get External
        external_mask = np.transpose(external_mask, (1, 0, 2)) # change to [x y z]
        external_mask = external_mask[:, ::-1, :] # flip y-axis to work properly for ANTs

        brain_mask = rtstruct.get_roi_mask_by_name("Brain") # Get Brain
        brain_mask = np.transpose(brain_mask, (1, 0, 2)) # change to [x y z]
        brain_mask = brain_mask[:, ::-1, :] # flip y-axis to work properly for ANTs

    return gtv_mask, external_mask, brain_mask
    
# Interpolate ROIs from CT shape to MR shape if necessary. Return important parameters
def roi_interp(base_dir, gtv_mask, external_mask, brain_mask, white_matter_mask, affine):

    # Define folders/paths
    rs_dir = base_dir / "RayStation" # Folder containing RayStation (RS) exports
    rs_ct_dcm_dir = rs_dir / "CT_DICOM" # Folder containg RS CT DICOM exports
    rs_mr_dcm_dir = rs_dir / "MR_DICOM" # Folder containing RS MR DICOM exports
    rs_rois_dir = rs_dir / "ROIs" # Folder containing RS ROIs (in RT struct)
    rs_rois_nii_dir = rs_dir / "ROIs_NIfTI" # Folder containing RS ROIs in NIfTI
    rs_rois_nii_dir.mkdir(parents=True, exist_ok=True) # make folder if it doesnt exist yet
    gtv_mask_nii_path = rs_rois_nii_dir / "gtv_mask.nii.gz" # define file path
    external_mask_nii_path = rs_rois_nii_dir / "external_mask.nii.gz" # define file path
    brain_mask_nii_path = rs_rois_nii_dir / "brain_mask.nii.gz" # define file path

    # First check if interpolation is needed. Flag is true when interpolation is needed
    interp_flag = True if gtv_mask.shape != white_matter_mask.shape else False
    print(f"Interpolation flag: {interp_flag}")

    # Convert CT DICOM to NIfTI
    if interp_flag:
        # Must be converted from DICOM to NIfTI so that ANTs can read the files.
        # ANTs can only read NIfTI

        rs_ct_nii_dir = rs_dir / "CT_NIfTI" # define folder path

        # Check if NIfTI folder has all the required files
        valid_folder = check_nifti_folder(rs_ct_nii_dir, bval_bvec_expected=False)

        if not valid_folder:
            dicom_to_nifti(rs_ct_dcm_dir, rs_ct_nii_dir)

    # Convert MR DICOM to NIfTI
    # Getting affine from MR no matter what. So need to convert MR to NIfTI (should be done already anyways)
    # Must be converted from DICOM to NIfTI so that ANTs can read the files.
    # ANTs can only read NIfTI

    rs_mr_nii_dir = rs_dir / "MR_NIfTI" # define folder path

    # Check if NIfTI folder has all the required files
    valid_folder = check_nifti_folder(rs_mr_nii_dir, bval_bvec_expected=False)

    if not valid_folder:
        dicom_to_nifti(rs_mr_dcm_dir, rs_mr_nii_dir)

    # Get affine from CT NIfTI file
    if interp_flag:
        rs_ct_nii_fname = get_fname(rs_ct_nii_dir) # Acquire file name for ct scan
        rs_ct_nii_fpath = str(rs_ct_nii_dir / (rs_ct_nii_fname + ".nii.gz")) 

        # Extract affine
        _, affine_ct= load_nifti(rs_ct_nii_fpath, return_img = False) # only care about affine here

    # Getting affine from MR no matter what
    rs_mr_nii_fname = get_fname(rs_mr_nii_dir) # Acquire file name for ct scan
    rs_mr_nii_fpath = str(rs_mr_nii_dir / (rs_mr_nii_fname + ".nii.gz")) 

    # Extract affine
    _, affine_mr= load_nifti(rs_mr_nii_fpath, return_img = False) # only care about affine here

    # Make sure affine from diffusion MR same as RayStation MR
    assert np.array_equal(affine_mr, affine), "Affines from raw MR and RayStation MR are not matching."

    # Save ROIs as NIfTI files (for ANTs in next step)
    if interp_flag:
        # Save masks to NIfTI files
        nib.save(nib.Nifti1Image(gtv_mask.astype('uint8'), affine=affine_ct), gtv_mask_nii_path) # use same affine as from CT
        nib.save(nib.Nifti1Image(external_mask.astype('uint8'), affine=affine_ct), external_mask_nii_path) # use same affine as from CT
        nib.save(nib.Nifti1Image(brain_mask.astype('uint8'), affine=affine_ct), brain_mask_nii_path) # use same affine as from CT

    # Create image registration from CT to MR using ANTs
    if interp_flag:
        # Use ANTs to transform masks from CR to MR space

        # First read NIfTI files with ANTs
        ct_ants = ants.image_read(str(rs_ct_nii_fpath))
        mr_ants = ants.image_read(str(rs_mr_nii_fpath)) # MR file exported from RayStation. NOT raw MR diffusion imaging
        gtv_mask_ants_ct = ants.image_read(str(gtv_mask_nii_path))
        external_mask_ants_ct = ants.image_read(str(external_mask_nii_path))
        brain_mask_ants_ct = ants.image_read(str(brain_mask_nii_path))

        # Register CT to MR
        reg = ants.registration(fixed=mr_ants, moving=ct_ants, type_of_transform='Rigid')

        # Apply transform to masks
        gtv_mask_ants_mr = ants.apply_transforms(fixed=mr_ants, moving=gtv_mask_ants_ct, 
                                                transformlist=reg['fwdtransforms'], interpolator='nearestNeighbor')
        external_mask_ants_mr = ants.apply_transforms(fixed=mr_ants, moving=external_mask_ants_ct, 
                                                transformlist=reg['fwdtransforms'], interpolator='nearestNeighbor')
        brain_mask_ants_mr = ants.apply_transforms(fixed=mr_ants, moving=brain_mask_ants_ct, 
                                                transformlist=reg['fwdtransforms'], interpolator='nearestNeighbor')
        
        # Get masks from ants variables
        gtv_mask = gtv_mask_ants_mr.numpy()[::-1,::-1,:] # reverse x and y axes to be aligned with white matter
        external_mask = external_mask_ants_mr.numpy()[::-1,::-1,:] # reverse x and y axes to be aligned with white matter
        brain_mask = brain_mask_ants_mr.numpy()[::-1,::-1,:] # reverse x and y axes to be aligned with white matter

    # Overlap white matter mask with brain mask to make sure all white matter is within the brain
    white_matter_mask = white_matter_mask.astype(bool) & brain_mask.astype(bool)

    # Create mask overlapping WM with GTV
    gtv_wm_mask = gtv_mask.astype(bool) & white_matter_mask.astype(bool)

    # Save ROIs as NIfTI files (for good now)
    if interp_flag:
        # Save masks to NIfTI files
        nib.save(nib.Nifti1Image(gtv_mask.astype('uint8'), affine=affine_mr), gtv_mask_nii_path) # use same affine as from MR
        nib.save(nib.Nifti1Image(external_mask.astype('uint8'), affine=affine_mr), external_mask_nii_path) # use same affine as from MR
        nib.save(nib.Nifti1Image(brain_mask.astype('uint8'), affine=affine_mr), brain_mask_nii_path) # use same affine as from MR

        # Interpolation no longer needed
        interp_flag = False

    return gtv_mask, external_mask, brain_mask, white_matter_mask, gtv_wm_mask 

    
