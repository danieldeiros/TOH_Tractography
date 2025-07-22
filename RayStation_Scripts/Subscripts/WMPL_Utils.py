# WMPL functions

## Import necessary packages
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
# from dipy.tracking.tracker import eudx_tracking # only available in recent DiPy
from dipy.tracking.local_tracking import LocalTracking
from dipy.io.stateful_tractogram import Space, StatefulTractogram
from dipy.io.streamline import save_trk
from rt_utils import RTStructBuilder
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
import shutil
import re
import ants

# Import necessary functions
from Subscripts.Preliminaries import rs_get_info

# Function to create WMPL
def get_wmpl(base_dir):

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

    # Define where to save WMPL
    wmpl_dir_nii = base_dir / "WMPL/NIfTI"
    wmpl_dir_nii.mkdir(parents=True, exist_ok=True) # make folder if it doesnt exist yet
    wmpl_path_nii = wmpl_dir_nii / "WMPL_map.nii.gz"

    # save the WMPL as a NIfTI
    save_nifti(wmpl_path_nii, wmpl, trk_aff)

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

    # Load in MR data
    Sorted_MR_Files = sorted(files["MR_Files"], key=lambda file: float(file.ImagePositionPatient[2])) # sort files by z-axis. increasing towards the head
    # anatomical orientation type (0010,2210) absent so z-axis is increasing towards the head of the patient

    # Define where to save WMPL
    wmpl_dir_dcm = base_dir / "WMPL/DICOM"
    wmpl_dir_dcm.mkdir(parents=True, exist_ok=True) # make folder if it doesnt exist yet

    # create new series UID
    new_series_uid = pydicom.uid.generate_uid()

    for i in range(wmpl.shape[2]):  # For each slice
        # ensure overlays properly with RayStation. Basically undoing what I did with ROIs.
        slice_data = wmpl[::-1,:,i].astype(np.uint16).T  

        # Get appropriate reference DICOM file
        ref_dcm = Sorted_MR_Files[i]
        dcm = ref_dcm.copy()

        # Modify instance-specific metadata
        dcm.InstanceNumber = i + 1
        dcm.SeriesInstanceUID = new_series_uid
        dcm.SOPInstanceUID = pydicom.uid.generate_uid()
        dcm.PixelData = slice_data.tobytes()
        dcm.Rows, dcm.Columns = slice_data.shape

        dcm.save_as(wmpl_dir_dcm / f"WMPL_slice_{i+1:03d}.dcm")

    return files
