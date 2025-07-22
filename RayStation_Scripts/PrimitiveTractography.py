# Adapting primitive tractography script to RayStation

# Import necessary functions
from Subscripts.Preliminaries import get_base_dir, check_nifti_folder, get_relevant_files, copy_relevant_files 
from Subscripts.Preliminaries import dicom_to_nifti, get_fname, rs_get_paths, rs_get_info
from Subscripts.Tractography_Utils import get_data, get_wm_mask, csa_and_sc, seed_gen, streamline_gen, save_tracts
from Subscripts.RS_ROI_Utils import rs_folders, load_rois, roi_interp
from Subscripts.WMPL_Utils import get_wmpl, save_wmpl_dicom
from Subscripts.Visualization_Utils import show_tracts, show_wmpl

# Preliminaries

## Define patient folder path
base_dir = get_base_dir()

## Set interactivity to True or False
interactive = True

## Define NIfTI folder path
nifti_dir = base_dir / "NIfTI"
## Check if NIfTI folder has all the required files
valid_folder = check_nifti_folder(nifti_dir, bval_bvec_expected=True)


if not valid_folder: ## only proceed if NIfTI folder doesn't already contain necessary files
    # Get diffusion MRIs if any exist
    relevant_files = get_relevant_files(base_dir)

    # Copy relevant diffusion MRIs to a new folder
    dicom_dir = copy_relevant_files(base_dir, relevant_files) # return output DICOM folder

    # Convert DICOM files to NIfTI
    dicom_to_nifti(dicom_dir, nifti_dir)

## Extract file name
fname = get_fname(nifti_dir)

# Tractography

## Extract data and perform segmentation
data_masked, mask, gtab, affine, hardi_img = get_data(nifti_dir, fname)

## Create white matter mask with DTI
white_matter_mask, FA = get_wm_mask(data_masked, gtab)

## Obtain ROIs defined on RS
### Check if folders valid. Create them if they are not
valid_folders = rs_folders(base_dir) # Return flag indicating if folders are valid

### Load ROIs
gtv_mask, external_mask, brain_mask = load_rois(base_dir, valid_folders)

### Perform interpolation to match mask shapes. Function will check if this is necessary. Returns required masks
gtv_mask, external_mask, brain_mask, white_matter_mask, gtv_wm_mask = roi_interp(base_dir, gtv_mask, external_mask, 
                                                                                 brain_mask, white_matter_mask, affine)

## Get CSA ODF model and define stopping criterion
csa_peaks, stopping_criterion = csa_and_sc(gtab, data_masked, white_matter_mask, FA)

## Generate seeds 
seeds_wm, seeds_gtv = seed_gen(gtv_mask, white_matter_mask, affine, seeds_per_voxel=1)

## Generate streamlines
streamlines_wm, streamlines_gtv = streamline_gen(seeds_wm, seeds_gtv, csa_peaks, stopping_criterion, affine)

## Show tracts
show_tracts(streamlines_wm, streamlines_gtv, gtv_mask, white_matter_mask, gtv_wm_mask, external_mask, affine, interactive)

## Save tracts
save_tracts(base_dir, streamlines_wm, hardi_img)

# WMPL

## Create WMPL map
wmpl = get_wmpl(base_dir)

## Save WMPL map as a DICOM
files = save_wmpl_dicom(base_dir, wmpl) # return MR files used to save PL map

## Show WMPL map
show_wmpl(base_dir, external_mask, files, interactive)
