# Visualization functions

## Import necessary packages
import os
os.environ["http_proxy"] = "http://dahernandez:34732b8f774d6def@ohswg.ottawahospital.on.ca:8080"
os.environ["https_proxy"] = "http://dahernandez:34732b8f774d6def@ohswg.ottawahospital.on.ca:8080"
import nibabel as nib
from dipy.viz import actor, colormap, has_fury, window
import numpy as np

# Function to visualize tracts using fury
def show_tracts(streamlines_wm, streamlines_gtv, gtv_mask, white_matter_mask, gtv_wm_mask, external_mask, affine):
    if has_fury:

        # streamlines_actor_wm = actor.line(
        #     streamlines_wm, colors=colormap.line_colors(streamlines_wm, cmap = "rgb_standard"), opacity=0.25
        # )

        streamlines_actor_gtv = actor.line(
            streamlines_gtv, colors=colormap.line_colors(streamlines_gtv, cmap = "rgb_standard"), opacity=1
        )

        gtv_actor = actor.contour_from_roi(
            gtv_mask, affine=affine, opacity=0.75, color = (1,0,0) # red
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

        # Save still images for this static example. Or for interactivity use
        # window.record(scene=scene, out_path="tractogram_EuDX.png", size=(800, 800))
        # if interactive:
        window.show(scene)

# Function to visualize WMPL map using fury
def show_wmpl(base_dir, external_mask, files):
    if has_fury:

        # Define path
        wmpl_dir_nii = base_dir / "WMPL/NIfTI"
        wmpl_path_nii = wmpl_dir_nii / "WMPL_map.nii.gz"

        # Load WMPL map
        wmpl_img = nib.load(wmpl_path_nii); wmpl_data = wmpl_img.get_fdata(); affine = wmpl_img.affine
        
        # mask where WMPL > 0
        wmpl_mask = wmpl_data > 0

        wmpl_actor = actor.contour_from_roi(
            wmpl_mask, affine=affine, opacity=0.5, color=(0, 1, 0) # green
        ) 

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
            ras_coords, cmap, point_radius=files["MR_Files"][0].SliceThickness, opacity=0.75 # voxels are 1.5 mm (from what ive seen) in x,y,z (isotropic)
        ) 

        # Create actor for external
        external_actor = actor.contour_from_roi(
            external_mask, affine=affine, opacity=0.5, color=(0, 0, 1) # blue
        ) 

        # Create the 3D display.
        scene = window.Scene()
        scene.add(points_actor)
        scene.add(external_actor)

        # Show plot
        # if interactive:
        window.show(scene)
        