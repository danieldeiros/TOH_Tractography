# WMPL functions

## Import necessary packages
import os
os.environ["http_proxy"] = "http://dahernandez:34732b8f774d6def@ohswg.ottawahospital.on.ca:8080"
os.environ["https_proxy"] = "http://dahernandez:34732b8f774d6def@ohswg.ottawahospital.on.ca:8080"
import pydicom
import nibabel as nib
from dipy.io.image import save_nifti
from dipy.tracking.utils import path_length
import numpy as np

# Import necessary functions
from Subscripts.Preliminaries import rs_get_info

# Function to create WMPL
def get_wmpl(base_dir):

    # Define where WMPL is saved
    wmpl_dir_nii = base_dir / "WMPL/NIfTI"
    wmpl_dir_nii.mkdir(parents=True, exist_ok=True) # make folder if it doesnt exist yet
    wmpl_path_nii = wmpl_dir_nii / "WMPL_map.nii.gz"

    if wmpl_path_nii.is_file():
        print("Found saved WMPL map. Loading WMPL map...")
        # Load WMPL map
        wmpl_img = nib.load(wmpl_path_nii); wmpl_data = wmpl_img.get_fdata(); affine = wmpl_img.affine
        wmpl = wmpl_data
        print("WMPL map succesfully loaded.")

    else:
        print("Creating WMPL map...")
        # Define folders and paths
        trk_dir = base_dir / "Tracts"
        trk_path = trk_dir / "tractogram_EuDX.trk"
        rs_dir = base_dir / "RayStation" # Folder containing RayStation (RS) exports
        rs_rois_nii_dir = rs_dir / "ROIs_NIfTI" # Folder containing RS ROIs in NIfTI
        gtv_mask_nii_path = rs_rois_nii_dir / "gtv_mask.nii.gz" # define file path

        # load the streamlines from the trk file
        trk = nib.streamlines.load(trk_path) # load trk file
        streamlines = trk.streamlines; hdr = trk.header; trk_aff = trk.affine # streamlines, header info and affine

        # Load the GTV from the NIfTI file
        gtv_img = nib.load(gtv_mask_nii_path)
        gtv_mask = gtv_img.get_fdata()
        gtv_aff = gtv_img.affine

        # Compute (minimum) path length per voxel # calculate the WMPL
        wmpl = path_length(streamlines, trk_aff, gtv_mask) # fill_value = 0 or -1? paper leaves blank

        # save the WMPL as a NIfTI
        save_nifti(wmpl_path_nii, wmpl, trk_aff)

        print("WMPL map successfully created.")

    return wmpl

# Function to save WMPL map as DICOM
def save_wmpl_dicom(base_dir, wmpl):
    # Load in MR data used to make tracks
    # This dats should be same size (as in (x,y,z)) as the white matter mask
    # For example, (256,256,70) for both

    # Define folders/paths
    rs_dir = base_dir / "RayStation" # Folder containing RayStation (RS) exports
    rs_mr_dcm_dir = rs_dir / "MR_DICOM" # Folder containing RS MR DICOM exports

    files, _ = rs_get_info(rs_mr_dcm_dir)
    # slice_thickness = files["MR_Files"][0].SliceThickness # take slice thickness from first MR file

    # Load in MR data
    Sorted_MR_Files = sorted(files["MR_Files"], key=lambda file: float(file.ImagePositionPatient[2])) # sort files by z-axis. increasing towards the head
    # anatomical orientation type (0010,2210) absent so z-axis is increasing towards the head of the patient

    # Define where to save WMPL
    wmpl_dir_dcm = base_dir / "WMPL/DICOM"
    wmpl_dir_dcm.mkdir(parents=True, exist_ok=True) # make folder if it doesnt exist yet

    # create new series UID and new study UID
    new_series_uid = pydicom.uid.generate_uid()
    new_study_uid = pydicom.uid.generate_uid()

    for i in range(wmpl.shape[2]):  # For each slice
        # ensure overlays properly with RayStation. Basically undoing what I did with ROIs.
        slice_data = wmpl[::-1,:,i].astype(np.uint16).T  

        # Get appropriate reference DICOM file
        ref_dcm = Sorted_MR_Files[i]
        dcm = ref_dcm.copy()

        # Modify instance-specific metadata
        dcm.InstanceNumber = i + 1
        dcm.SeriesInstanceUID = new_series_uid
        dcm.StudyInstanceUID = new_study_uid
        dcm.SOPInstanceUID = pydicom.uid.generate_uid()
        dcm.PixelData = slice_data.tobytes()
        dcm.Rows, dcm.Columns = slice_data.shape
        dcm.SeriesDescription = "White matter path length map"
        dcm.ProtocolName = "N/A"
        dcm.Modality = "MR"

        dcm.save_as(wmpl_dir_dcm / f"WMPL_slice_{i+1:03d}.dcm")
