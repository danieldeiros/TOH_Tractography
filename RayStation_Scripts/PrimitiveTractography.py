# Adapting primitive tractography script to RayStation

# Import necessary functions
from Subscripts.Preliminaries import get_base_dir, check_nifti_folder, get_relevant_files, copy_relevant_files 
from Subscripts.Preliminaries import dicom_to_nifti, get_fname, rs_get_paths, rs_get_info
from Subscripts.Tractography_Utils import get_data, get_wm_mask, csa_and_sc, seed_gen, streamline_gen, save_tracts, get_tracts
from Subscripts.RS_ROI_Utils import rs_folders, load_rois, roi_interp, get_white_matter_mask
from Subscripts.WMPL_Utils import get_wmpl, save_wmpl_dicom
from Subscripts.Visualization_Utils import show_tracts, show_wmpl

# Import packages
import zmq
import pickle

# Preliminaries

## Create context
context = zmq.Context()

## Define data port to be used with server for sending data (for fury. like streamlines, masks, and affine)
data_port = "5564"
# ## Define communications port to be used with server for communication purposes (when user has closed Fury window on client side)
# comms_port = "5565"

## Define data socket
data_socket = context.socket(zmq.REQ)
data_socket.connect(f"tcp://localhost:{data_port}")

# ## Define comms socket
# comms_socket = context.socket(zmq.REQ)
# comms_socket.bind(f"tcp://localhost:{comms_port}")

# Create poller to wait for server
poller = zmq.Poller()
poller.register(data_socket, zmq.POLLIN)

## Define patient folder path
print("Defining base folder...")
base_dir = get_base_dir()

## Set interactivity to True or False
interactive = True
print("Interactivity: ", interactive)

## Define NIfTI folder path
nifti_dir = base_dir / "NIfTI"
## Check if NIfTI folder has all the required files
print(f"Checking NIfTI folder {nifti_dir}...")
valid_folder = check_nifti_folder(nifti_dir, bval_bvec_expected=True)

if not valid_folder: ## only proceed if NIfTI folder doesn't already contain necessary files
    # Get diffusion MRIs if any exist
    print("Collecting relevant MRI files...")
    relevant_files = get_relevant_files(base_dir)

    # Copy relevant diffusion MRIs to a new folder
    print("Copying relavant files to a new folder...")
    dicom_dir = copy_relevant_files(base_dir, relevant_files) # return output DICOM folder

    # Convert DICOM files to NIfTI
    print("Converting from DICOM to NIfTI...")
    dicom_to_nifti(dicom_dir, nifti_dir)

## Extract file name
print("Getting file name...")
fname = get_fname(nifti_dir)

# Tractography

## First check if tractography has already been completed
print("Checking for existance of saved tracts...")
streamlines_wm, streamlines_gtv, affine, tracts_flag = get_tracts(base_dir)

## Check if white matter mask exists
print("Checking for saved white matter mask...")
white_matter_mask = get_white_matter_mask(base_dir)

if white_matter_mask.size == 0 or not tracts_flag:
    ## Extract data and perform segmentation
    print("Extracting data and performing segmentation...")
    data_masked, mask, gtab, affine, hardi_img = get_data(nifti_dir, fname)
    print("Data obtained.")

    ## Create white matter mask with DTI
    print("Extracting white matter mask using DTI...")
    white_matter_mask, FA = get_wm_mask(data_masked, gtab)
    print("White matter mask obtained.")

## Obtain ROIs defined on RS
### Check if folders valid. Create them if they are not
print("Checking for RayStation files...")
rs_folders(base_dir)

### Load ROIs
print("Loading ROIs...")
gtv_mask, external_mask, brain_mask = load_rois(base_dir)

### Perform interpolation to match mask shapes. Function will check if this is necessary. Returns required masks
gtv_mask, external_mask, brain_mask, white_matter_mask, gtv_wm_mask = roi_interp(base_dir, gtv_mask, external_mask, 
                                                                                 brain_mask, white_matter_mask, affine)
print("Relevant ROIs succesfully loaded in MR coordinates.")

if not tracts_flag:
    ## Get CSA ODF model and define stopping criterion
    print("Applying CSA ODF model...")
    csa_peaks, stopping_criterion = csa_and_sc(gtab, data_masked, white_matter_mask, FA)
    print("CSA ODF model successfully applied to data.")

    ## Generate seeds 
    print("Generating seeds...")
    seeds_wm, seeds_gtv = seed_gen(gtv_mask, white_matter_mask, affine, seeds_per_voxel=1)
    print("Seeds generated.")

    ## Generate streamlines
    print("Generating streamlines...")
    streamlines_wm, streamlines_gtv = streamline_gen(seeds_wm, seeds_gtv, csa_peaks, stopping_criterion, affine)
    print("Streamlines generated.")

    ## Save tracts
    print("Saving tracts...")
    save_tracts(base_dir, streamlines_wm, hardi_img)
    print("Tracts successfully saved.")

## Show tracts
if interactive:
    # print("Showing tracts...")
    # show_tracts(streamlines_wm, streamlines_gtv, gtv_mask, white_matter_mask, gtv_wm_mask, external_mask, affine, interactive)
    fury_data = { # Define all we need to show on Fury in a dictionary
        "streamlines_wm": streamlines_wm,
        "streamlines_gtv": streamlines_gtv,
        "gtv_mask": gtv_mask,
        "white_matter_mask": white_matter_mask,
        "gtv_wm_mask": gtv_wm_mask,
        "external_mask": external_mask,
        "affine": affine
    }
    print("Showing tracts...")
    data_socket.send(pickle.dumps(fury_data)) # Send data over via socket
    print("Data sent from PrimitiveTractography to server")
    # print("Data sent to server from PrimitiveTractography")
    # comms_socket.send_string("Data sent.") # Sent data
    received_flag = False # set flag to false until we receive confirmation from the server that the client has closed the Fury window

# WMPL

## Create WMPL map
print("Creating WMPL map...")
wmpl = get_wmpl(base_dir)
print("WMPL map successfully created.")

## Save WMPL map as a DICOM
print("Saving WMPL map as a DICOM...")
files = save_wmpl_dicom(base_dir, wmpl) # return MR files used to save PL map
print("WMPL map saved as DICOM successfully")

## Show WMPL map
if interactive:
    # Wait till we receive confirmation from client that the Fury window has been closed
    while not received_flag:
        if dict(poller.poll(timeout=3000)):
            message = data_socket.recv_string() # receive string
            if message == "Data received. Fury window closed":
                received_flag = True
                break

    print("Showing WMPL map...")
    # show_wmpl(base_dir, external_mask, files, interactive)

    fury_data = { # Define all we need to show on Fury in a dictionary
        "base_dir": base_dir,
        "external_mask": external_mask,
        "files": files
    }

    data_socket.send(pickle.dumps(fury_data)) # Send data over via socket
    print("Data sent from PrimitiveTractography to server")
    # comms_socket.send_string("Data sent.") # Sent data
    received_flag = False # set flag to false until we receive confirmation from the server that the client has closed the Fury window

    # Wait till we receive confirmation from client that the Fury window has been closed
    while not received_flag:
        if dict(poller.poll(timeout=3000)):
            message = data_socket.recv_string() # receive string
            if message == "Data received. Fury window closed":
                received_flag = True
                break

print("Program successfully completed.")
