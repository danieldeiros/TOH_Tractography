# Tractography functions

## Import necessary packages
import os
os.environ["http_proxy"] = "http://dahernandez:34732b8f774d6def@ohswg.ottawahospital.on.ca:8080"
os.environ["https_proxy"] = "http://dahernandez:34732b8f774d6def@ohswg.ottawahospital.on.ca:8080"
import nibabel as nib
from dipy.io import read_bvals_bvecs
from dipy.core.gradients import gradient_table
from dipy.io.image import load_nifti
from dipy.reconst.shm import CsaOdfModel
from dipy.direction import peaks_from_model
from dipy.data import default_sphere
from dipy.segment.mask import median_otsu
from dipy.tracking.stopping_criterion import ThresholdStoppingCriterion
from dipy.reconst.dti import TensorModel
from dipy.tracking.utils import random_seeds_from_mask
from dipy.tracking.streamline import Streamlines
from dipy.tracking.tracker import eudx_tracking # only available in recent DiPy
# from dipy.tracking.local_tracking import LocalTracking # Use LocalTracking to replace eudx_tracking in older DiPy
from dipy.io.stateful_tractogram import Space, StatefulTractogram
from dipy.io.streamline import save_trk
import numpy as np

# Import necessary functions
# from Subscripts.Preliminaries import load_nifti

# Create necessary functions

# Function to extract data and perform segmentation
def get_data(nifti_dir, fname):
        # Define file names
    nifti_file = str(nifti_dir / (fname + ".nii.gz"))
    bval_file  = str(nifti_dir / (fname + ".bval"))
    bvec_file  = str(nifti_dir / (fname + ".bvec"))

    # Extract data
    data, affine, hardi_img = load_nifti(nifti_file, return_img = True)
    bvals, bvecs = read_bvals_bvecs(bval_file, bvec_file)

    # Make gradient table
    gtab = gradient_table(bvals, bvecs = bvecs)

    # Make brain mask
    data_masked, mask = median_otsu(data, vol_idx=range(data.shape[3]), numpass=1)

    return data_masked, mask, gtab, affine, hardi_img

# Function to create white matter mask with DTI
def get_wm_mask(data_masked, gtab):
    # Fit the diffusion tensor model
    tensor_model = TensorModel(gtab)
    tensor_fit = tensor_model.fit(data_masked)

    # Get FA map
    FA = tensor_fit.fa

    # Generate white matter mask using FA threshold
    # Typical FA threshold for white matter is between 0.2 - 0.3. Can use 0.25
    white_matter_mask = (FA > 0.15).astype(np.uint8) # paper uses 0.15
    white_matter_mask[:,:,:]=white_matter_mask[::-1,::-1,:] # reverse order in x and y directions to visualize like in RayStation

    return white_matter_mask, FA

# Function using CSA ODF model and defining stopping criterion
def csa_and_sc(gtab, data_masked, white_matter_mask, FA):
    # Using CSA (Constant Solid Angle) model then peaks_from_model
    # csa_model = CsaOdfModel(gtab, sh_order_max=4)
    csa_model = CsaOdfModel(gtab, sh_order=4)
    csa_peaks = peaks_from_model(
        csa_model, data_masked, default_sphere, relative_peak_threshold=0.5, min_separation_angle=15, mask=white_matter_mask
    ) # or relative_peak_threshold=0.8, min_seperation_angle=45 (from introduction to basic tracking tutorial)
    # from paper: relative_peak_threshold=0.5, min_separation_angle=15

    # Define stopping criterion
    stopping_criterion = ThresholdStoppingCriterion(FA, 0.15) 
    # or csa_peaks.gfa, 0.25 (from introduction to basic tracking tutorial). paper uses FA, 0.15

    return csa_peaks, stopping_criterion

# Generate seeds
def seed_gen(gtv_mask, white_matter_mask, affine, seeds_per_voxel):
    # Generating seeds

    # Generating seeds on white matter
    seeds_wm = random_seeds_from_mask(white_matter_mask, affine, seeds_count=seeds_per_voxel, seed_count_per_voxel=True)
    # paper seeds all white matter voxels. not just the ones which coincide with the GTV (ROI)
    # so can use white_matter_mask or roi_wm_mask

    # Generating seeds on GTV
    seeds_gtv = random_seeds_from_mask(gtv_mask, affine, seeds_count=seeds_per_voxel, seed_count_per_voxel=True)

    return seeds_wm, seeds_gtv

# Generate streamliens
def streamline_gen(seeds_wm, seeds_gtv, csa_peaks, stopping_criterion, affine):
    # Using EuDX tracking for now. 

    # Creating streamlines from all white matter and from GTV. First white matter.
    # Initialization of eudx_tracking. The computation happens in the next step.
    # eudx_tracking replaced with LocalTracking for older versions of DiPy
    # Stuff has to be reordered! Also max_angle doesn't exist in LocalTracking
    streamlines_generator_wm = eudx_tracking(
        seeds_wm, stopping_criterion, affine, step_size=0.5, pam=csa_peaks, max_angle=60 # paper uses max_angle of 60
    )
    # streamlines_generator_wm = LocalTracking(
    #     csa_peaks, stopping_criterion, seeds_wm, affine, step_size=0.5
    #     )
    
    # Generate streamlines object
    streamlines_wm = Streamlines(streamlines_generator_wm)

    # Now creating streamlines from GTV
    streamlines_generator_gtv = eudx_tracking(
        seeds_gtv, stopping_criterion, affine, step_size=0.5, pam=csa_peaks, max_angle=60 # paper uses max_angle of 60
    )
    # streamlines_generator_gtv = LocalTracking(
    #     csa_peaks, stopping_criterion, seeds_gtv, affine, step_size=0.5
    # )

    # Generate streamlines object
    streamlines_gtv = Streamlines(streamlines_generator_gtv)

    # colors: red--> left to right, green--> front (anterior) to back (posterior), blue--> top to bottom
    # # Streamlines with x and y flipped for colors
    # streamlines_flipped = streamlines.copy()
    # streamlines_flipped[:][:, 0:2] = streamlines_flipped[:][:, 1::-1]

    return streamlines_wm, streamlines_gtv

def save_tracts(base_dir, streamlines_wm, hardi_img):
    # Define/create folder and path
    trk_dir = base_dir / "Tracts"
    trk_dir.mkdir(parents=True, exist_ok=True) # make folder if it doesnt exist yet
    trk_path = trk_dir / "tractogram_EuDX.trk"

    # Define tractogram and save
    sft = StatefulTractogram(streamlines_wm, hardi_img, Space.RASMM)
    save_trk(sft, str(trk_path), streamlines_wm)

def get_tracts(base_dir):
    # Define paths
    trk_dir = base_dir / "Tracts"
    # trk_dir.mkdir(parents=True, exist_ok=True) # make folder if it doesnt exist yet
    trk_path = trk_dir / "tractogram_EuDX.trk"
    trk_path_gtv = trk_dir / "tractogram_GTV_EuDX.trk"

    if trk_path.is_file() and trk_path_gtv.is_file():
        # Load the streamlines from the trk file
        trk = nib.streamlines.load(trk_path) # load trk file
        streamlines_wm = trk.streamlines; trk_aff = trk.affine # streamlines and affine

        trk_gtv = nib.streamlines.load(trk_path_gtv) # load trk file
        streamlines_gtv = trk_gtv.streamlines; trk_gtv_aff = trk_gtv.affine # streamlines and affine

        # Check that both affines are equal
        assert np.array_equal(trk_aff, trk_gtv_aff), "Affines from white matter tracts and GTV tracts are not matching."

        # Set affine matrix
        affine = trk_aff
        
        tracts_flag = True # Set flag to indicate tracts exist

        print("[OK] Tracts located and loaded.")
        return streamlines_wm, streamlines_gtv, affine, tracts_flag
    else:
        # Set variables as empty
        streamlines_wm = []; streamlines_gtv = []; affine = []

        # Set flag to false
        tracts_flag = False

        print("[WARNING] Tracts not found.")
        return streamlines_wm, streamlines_gtv, affine, tracts_flag