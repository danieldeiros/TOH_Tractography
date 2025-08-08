# Visualization functions

## Import necessary packages
import os
os.environ["http_proxy"] = "http://dahernandez:34732b8f774d6def@ohswg.ottawahospital.on.ca:8080"
os.environ["https_proxy"] = "http://dahernandez:34732b8f774d6def@ohswg.ottawahospital.on.ca:8080"
import nibabel as nib
from dipy.viz import actor, colormap, has_fury, window
import numpy as np

# Import necessary functions
from Subscripts.Preliminaries import rs_get_info

# Function to visualize tracts using fury
def show_tracts(base_dir):
    if has_fury:

        # Define paths for tracts stuff
        trk_dir = base_dir / "Tracts"
        trk_path = trk_dir / "tractogram_EuDX.trk"
        trk_path_gtv = trk_dir / "tractogram_GTV_EuDX.trk"

        # Load the streamlines from the trk file
        trk = nib.streamlines.load(trk_path) # load trk file
        streamlines_wm = trk.streamlines; trk_aff = trk.affine # streamlines and affine

        trk_gtv = nib.streamlines.load(trk_path_gtv) # load trk file
        streamlines_gtv = trk_gtv.streamlines; trk_gtv_aff = trk_gtv.affine # streamlines and affine

        # Check that both affines are equal
        assert np.array_equal(trk_aff, trk_gtv_aff), "Affines from white matter tracts and GTV tracts are not matching."

        # Set affine matrix
        affine = trk_aff

        # Define folders/paths
        rs_dir = base_dir / "RayStation" # Folder containing RayStation (RS) exports
        rs_rois_nii_dir = rs_dir / "ROIs_NIfTI" # Folder containing RS ROIs in NIfTI
        gtv_mask_nii_path = rs_rois_nii_dir / "gtv_mask.nii.gz" # define file path
        external_mask_nii_path = rs_rois_nii_dir / "external_mask.nii.gz" # define file path
        brain_mask_nii_path = rs_rois_nii_dir / "brain_mask.nii.gz" # define file path

        # Get masks from pre-defined files
        gtv_mask_nii = nib.load(gtv_mask_nii_path); gtv_mask = gtv_mask_nii.get_fdata()
        external_mask_nii = nib.load(external_mask_nii_path); external_mask = external_mask_nii.get_fdata()
        brain_mask_nii = nib.load(brain_mask_nii_path); brain_mask = brain_mask_nii.get_fdata()

        # streamlines_actor_wm = actor.line(
        #     streamlines_wm, colors=colormap.line_colors(streamlines_wm, cmap = "rgb_standard"), opacity=0.25
        # )

        streamlines_actor_gtv = actor.line(
            streamlines_gtv, colors=colormap.line_colors(streamlines_gtv, cmap = "rgb_standard"), opacity=1
        )

        gtv_actor = actor.contour_from_roi(
            gtv_mask, affine=affine, opacity=0.95, color = (1,0,0) # red
        )

        # wm_actor = actor.contour_from_roi(
        #     white_matter_mask, affine=affine, opacity=0.25, color=(1,1,1) # white
        # )

        # gtv_wm_actor = actor.contour_from_roi(
        #     gtv_wm_mask, affine=affine, opacity=0.25, color=(0, 1, 0) # green
        # ) 

        external_actor = actor.contour_from_roi(
            external_mask, affine=affine, opacity=0.5, color=(0.676, 0.844, 0.898) # light blue
        ) 

        # brain_actor = actor.contour_from_roi(
        #     brain_mask, affine=affine, opacity=0.5, color=(1, 0.753, 0.796) # pink
        # ) 

        # Create the 3D display.
        scene = window.Scene()
        # scene.add(streamlines_actor_wm)
        scene.add(streamlines_actor_gtv)
        scene.add(gtv_actor)
        # scene.add(wm_actor)
        # scene.add(gtv_wm_actor)
        scene.add(external_actor)
        # scene.add(brain_actor)

        # Define colours to show
        colours = {
            'GTV' : (1,0.1,0.1), # red
            'External' : (0.676, 0.844, 0.898) # light blue
        }

        # Add custom legend (text + coloured squares)
        legend_pos = np.array([150, 30, 0])
        spacing = 20

        for i, (label, colour) in enumerate(colours.items()):
            # Add a small square actor as color indicator
            square_actor = actor.sphere(centers=np.array([legend_pos + [0, -i*spacing, -i*spacing]]),
                                        colors=np.array([colour]),
                                        radii=10)
            scene.add(square_actor)
            
            # Add the label as text next to it
            # direction=None makes label follow camera
            text_actor = actor.vector_text(text=label, pos=legend_pos + [100, -i*spacing, -i*spacing], scale=(20,20,20), direction=None, align_center=False, extrusion=10)
            scene.add(text_actor)

        # Add informational text
        info_text = "In tractography, the direction of streamlines is labelled by red, green, and blue, where..." \
                    "\nRed indicates directions in the X axis: right to left or left to right." \
                    "\nGreen indicates directions in the Y axis: posterior to anterior or from anterior to posterior." \
                    "\nBlue indicates directions in the Z axis: inferior to superior or vice versa."
        info_actor = actor.vector_text(text=info_text, pos=legend_pos + [100,-100,-100], scale=(5,5,5), direction=None, align_center=False, extrusion=10)
        scene.add(info_actor)

        # Save still images for this static example. Or for interactivity use
        # window.record(scene=scene, out_path="tractogram_EuDX.png", size=(800, 800))
        # if interactive:
        window.show(scene)

# Function to visualize WMPL map using fury
def show_wmpl(base_dir):
    if has_fury:

        # Define path
        wmpl_dir_nii = base_dir / "WMPL/NIfTI"
        wmpl_path_nii = wmpl_dir_nii / "WMPL_map.nii.gz"
        rs_dir = base_dir / "RayStation" # Folder containing RayStation (RS) exports
        rs_rois_nii_dir = rs_dir / "ROIs_NIfTI" # Folder containing RS ROIs in NIfTI
        gtv_mask_nii_path = rs_rois_nii_dir / "gtv_mask.nii.gz" # define file path
        external_mask_nii_path = rs_rois_nii_dir / "external_mask.nii.gz" # define file path

        # Get masks from pre-defined files
        gtv_mask_nii = nib.load(gtv_mask_nii_path); gtv_mask = gtv_mask_nii.get_fdata()
        external_mask_nii = nib.load(external_mask_nii_path); external_mask = external_mask_nii.get_fdata()

        # Define folders/paths
        rs_dir = base_dir / "RayStation" # Folder containing RayStation (RS) exports
        rs_mr_dcm_dir = rs_dir / "MR_DICOM" # Folder containing RS MR DICOM exports

        files, _ = rs_get_info(rs_mr_dcm_dir, prints=False)
        slice_thickness = files["MR_Files"][0].SliceThickness # take slice thickness from first MR file

        # Load WMPL map
        wmpl_img = nib.load(wmpl_path_nii); wmpl_data = wmpl_img.get_fdata(); affine = wmpl_img.affine
        
        # mask where WMPL > 0
        wmpl_mask = wmpl_data > 0

        # wmpl_actor = actor.contour_from_roi(
        #     wmpl_mask, affine=affine, opacity=0.5, color=(0, 1, 0) # green
        # ) 

        # Extract voxel coordinates where WMPL > 0
        voxel_coords = np.array(np.nonzero(wmpl_mask)).T # shape (N,3)

        # Get corresponding WMPL values at these voxels
        values = wmpl_data[wmpl_mask]

        # Map voxel coords to real world coordinates (RASMM)
        ras_coords = nib.affines.apply_affine(wmpl_img.affine, voxel_coords) # affine from wmpl should be same as affines from before

        # Create a colormap for WMPL values
        cmap = colormap.create_colormap(values, name='hot')

        # Create a point cloud actor with colors
        points_actor = actor.point(
            ras_coords, cmap, point_radius=slice_thickness, opacity=0.75 # voxels are 1.5 mm (from what ive seen) in x,y,z (isotropic)
        ) 

        # Create actor for external
        external_actor = actor.contour_from_roi(
            external_mask, affine=affine, opacity=0.5, color=(0, 0, 1) # blue
        ) 

        # Create actor for GTV
        gtv_actor = actor.contour_from_roi(
            gtv_mask, affine=affine, opacity=0.95, color = (0,0,0) # black
        )

        # Create the 3D display.
        scene = window.Scene()
        scene.add(points_actor)
        scene.add(external_actor)
        scene.add(gtv_actor)

        # Show plot
        # if interactive:
        window.show(scene)
        