# RayStation tools

# Imports
import numpy as np
import shutil
from pathlib import Path

# Import necessary functions
from Subscripts.Preliminaries import rs_get_paths, dicom_to_nifti, check_nifti_folder, get_fname

# Obtain image registration from CT to MR
def get_img_registration(case, mr_exam_name, pl_map=False):

    # Skip if we already know we have a PL Map
    if not pl_map:
        # Check if we have a PL Map
        pl_map = check_pl_map(case)

    # Get registration
    source_reg = [] # set to empty first
    if pl_map:
        # Check if registration from CT Planning to PL Map already made
        source_reg = [reg for reg in case.RigidRegistrations if reg.FromExamination.Name == "CT Planning"
                        and reg.ToExamination.Name == "PL Map"]
        if source_reg:
            # Take first registration in list
            source_reg = source_reg[0]
            trans_matrix = source_reg.RigidTransformationMatrix # assign transformation matrix
            if source_reg.Name != "Image registration CT Planning - PL Map": # Make sure registration has expected name
                source_reg = [] # Set to empty if not the expected name
            else:
                print("Image registration CT Planning - PL Map succesfully acquired.")

    if not source_reg:
        # Try to get proper registration from CT to MR
        source_reg = [reg for reg in case.RigidRegistrations if reg.FromExamination.Name == "CT Planning"
                    and reg.ToExamination.Name == mr_exam_name] # Get registration from MR exam name
        if source_reg:
            # Take first registration (should only be one) if found registration from CT to MR
            # We assume all MRs have the same affine
            source_reg = source_reg[0]
            # Get transformation matrix
            trans_matrix = source_reg.RigidTransformationMatrix
        else:
            # Try to find registration from MR to CT now
            source_reg = [reg for reg in case.RigidRegistrations 
                        if reg.FromExamination.Name == mr_exam_name # Get registration from MR exam name
                        and reg.ToExamination.Name == "CT Planning"]
            if source_reg:
                # Take first registration if found registration from MR to CT
                source_reg = source_reg[0]
                # Get transformation matrix
                # Reshape to 4x4 matrix, get inverse matrix, then convert back to dictionary of 16 elements
                print(source_reg.RigidTransformationMatrix)
                trans_matrix = (np.linalg.inv(np.array(source_reg.RigidTransformationMatrix).reshape(4, 4)))
                trans_matrix = {'M11': trans_matrix[0,0], 'M12': trans_matrix[0,1], 'M13': trans_matrix[0,2], 'M14': trans_matrix[0,3],
                                'M21': trans_matrix[1,0], 'M22': trans_matrix[1,1], 'M23': trans_matrix[1,2], 'M24': trans_matrix[1,3],
                                'M31': trans_matrix[2,0], 'M32': trans_matrix[2,1], 'M33': trans_matrix[2,2], 'M34': trans_matrix[2,3],
                                'M41': trans_matrix[3,0], 'M42': trans_matrix[3,1], 'M43': trans_matrix[3,2], 'M44': trans_matrix[3,3]}
                
                # Create new image registration with this inversed transformation matrix
                case.CreateNamedIdentityImageRegistration(
                FromExaminationName = source_reg.ToExamination.Name, # Should be CT Planning
                ToExaminationName = source_reg.FromExamination.Name,
                RegistrationName = f"Image registration {source_reg.ToExamination.Name} - {source_reg.FromExamination.Name}",
                Description = ""
                )

                # Assign transformation matrix to new image registration
                case.RigidRegistrations[len(case.RigidRegistrations)-1].SetImageRegistrationMatrix(TransformationMatrix = trans_matrix)

            else: 
                raise ValueError("No valid image registrations found.")

        if pl_map:
            # Create new image registration
            case.CreateNamedIdentityImageRegistration(
                FromExaminationName = "CT Planning",
                ToExaminationName = "PL Map",
                RegistrationName = "Image registration CT Planning - PL Map",
                Description = ""
            )
            
            if not isinstance(trans_matrix, dict):
                trans_matrix = trans_matrix.reshape(4, 4)
                trans_matrix = {'M11': trans_matrix[0,0], 'M12': trans_matrix[0,1], 'M13': trans_matrix[0,2], 'M14': trans_matrix[0,3],
                                'M21': trans_matrix[1,0], 'M22': trans_matrix[1,1], 'M23': trans_matrix[1,2], 'M24': trans_matrix[1,3],
                                'M31': trans_matrix[2,0], 'M32': trans_matrix[2,1], 'M33': trans_matrix[2,2], 'M34': trans_matrix[2,3],
                                'M41': trans_matrix[3,0], 'M42': trans_matrix[3,1], 'M43': trans_matrix[3,2], 'M44': trans_matrix[3,3]}
                
            # Assign transformation matrix to new image registration
            case.RigidRegistrations[len(case.RigidRegistrations)-1].SetImageRegistrationMatrix(TransformationMatrix = trans_matrix)

            print("Image registration CT Planning - PL Map succesfully created.")
        
    return case

# Copy ROIs from CT to MR
def copy_roi_geometries(case, mr_exam_name):

    # Get name of GTV ROI
    roi_names = case.PatientModel.RegionsOfInterest.keys()
    gtv_rois = [name for name in roi_names if "GTV" in name]
    gtv_roi_name = gtv_rois[0] # Assume length one for gtv rois. i.e. assuming only one GTV ROI

    source_reg = [] # set to empty first
    # Check if registration from CT Planning to some MRI has already been made
    while not source_reg:
        source_reg = [reg for reg in case.RigidRegistrations if reg.FromExamination.Name == "CT Planning"
                        and reg.ToExamination.Name == mr_exam_name]
        if not source_reg:
            case = get_img_registration(case, mr_exam_name) # call function if no image registration found

    source_reg = source_reg[0] # Take first element (should have length 1)

    # Copy ROI geometries to MR scan
    case.PatientModel.CopyRoiGeometries(SourceExamination=case.Examinations['CT Planning'],
                                    TargetExaminationNames=[f"{source_reg.ToExamination.Name}"], RoiNames=[gtv_roi_name, "Brain", "External"],
                                    ImageRegistrationNames=[f"Image registration CT Planning - {source_reg.ToExamination.Name}"],
                                    TargetExaminationNamesToSkipAddedReg=[])
    
    return case
    
# Export CT, MR, and RT Struct from MR
def export_rs_stuff(patient, case, base_dir):

    # Check for MRIs
    mr_exam_names = [] # set list empty for now
    for exam in case.Examinations:
        if "MR" in exam.Name:
            mr_exam_names.append(exam.Name) # add mr name to list

    # Check if we already have a CT Planning examination and rename CT scan to CT Planning if not
    case = check_ct_planning(case)

    # Get MR exam name with FA in the description
    mr_exam_name = check_description(case, mr_exam_names)

    # Copy ROIs from CT Planning to MR exam if necessary
    case = copy_roi_geometries(case, mr_exam_name)

    # Define folders/paths
    rs_dir = base_dir / "RayStation" # Folder containing RayStation (RS) exports
    rs_dir.mkdir(parents=True, exist_ok=True) # make folder if it doesn't exist

    # Save before we export (required)
    patient.Save()

    try:
        # Export the CT Planning
        case.ScriptableDicomExport(
            ExportFolderPath = str(rs_dir),
            Examinations = ["CT Planning", str(mr_exam_name)],
            RtStructureSetsForExaminations = [str(mr_exam_name)],
            IgnorePreConditionWarnings = True
        )
    except Exception as e:
        import traceback
        print("Export failed:")
        traceback.print_exc()

# Check if FA exists in MR exam name
def check_description(case, mr_exam_names):
    # Loop through all mr exam names
    for i in range(0,len(mr_exam_names)):
        # Take MR exam name
        mr_exam_name = mr_exam_names[i]
        for exam in case.Examinations:
            if exam.Name == mr_exam_name:
                # Check if description of examination has FA
                data = exam.GetAcquisitionDataFromDicom()
                if 'FA' in data['SeriesModule']['SeriesDescription']:
                    # Return once we find MR exam with FA in description
                    return mr_exam_name

# Check if base director already has necessary files
def check_rois(base_dir):

    # Define Paths
    rs_dir = base_dir / "RayStation" # Folder containing RayStation (RS) exports
    rs_dir.mkdir(parents=True, exist_ok=True) # make folder if it doesn't exist
    rs_ct_dcm_dir = rs_dir / "CT_DICOM" # Folder containg RS CT DICOM exports
    rs_mr_dcm_dir = rs_dir / "MR_DICOM" # Folder containing RS MR DICOM exports
    rs_rois_dir = rs_dir / "ROIs" # Folder containing RS ROIs (in RT struct)

    # Flags to indicate whether folders contain necessary files
    rs_ct_dcm_flag = False
    rs_mr_dcm_flag = False
    rs_rois_flag = False

    # Check if folders exist, if they do, check if they contain the appropriate file type
    # Delete files in folders if they don't contain what we want, to prepare for the movement of files into the proper folders
    if rs_ct_dcm_dir.is_dir():
        print("Checking for files from CT DICOM folder...")
        file_paths = rs_get_paths(rs_ct_dcm_dir)
        rs_ct_dcm_flag = True if file_paths["CT_File_Paths"] else False
        if not rs_ct_dcm_flag:
            shutil.rmtree(rs_ct_dcm_dir)
        
    if rs_mr_dcm_dir.is_dir():
        print("Checking for files from MRI DICOM folder...")
        file_paths = rs_get_paths(rs_mr_dcm_dir)
        rs_mr_dcm_flag = True if file_paths["MR_File_Paths"] else False
        if not rs_mr_dcm_flag:
            shutil.rmtree(rs_mr_dcm_dir)

    if rs_rois_dir.is_dir():
        print("Checking for files from ROI folder...")
        file_paths = rs_get_paths(rs_rois_dir)
        rs_rois_flag = True if file_paths["RS_File_Paths"] else False
        if not rs_rois_flag:
            shutil.rmtree(rs_rois_dir)

    # Move files into their appropriate folders if necessary
    if rs_ct_dcm_flag and rs_mr_dcm_flag and rs_rois_flag: # Continue if all folders valid
        print("Folders located and validated.")
        rois_flag = True
        return rois_flag
    else: # Create folders for missing file types
        file_paths = rs_get_paths(rs_dir) # Get all file paths from original RayStation folder

        if not file_paths["CT_File_Paths"] and not file_paths["MR_File_Paths"] and not file_paths["RS_File_Paths"]:
            print(f"Missing required RayStation files in {rs_dir}. Working to export them...")
            rois_flag = False
            return rois_flag
        
        if not rs_ct_dcm_flag:
            rs_ct_dcm_dir.mkdir(parents=True, exist_ok=True) # make folder if it doesn't exist
            for file in file_paths["CT_File_Paths"]: # Get all files and move to new folder
                # Move file to new folder
                shutil.move(str(file), str(rs_ct_dcm_dir))
            rs_ct_dcm_flag = True # Set flag to true when process complete

        if not rs_mr_dcm_flag:
            rs_mr_dcm_dir.mkdir(parents=True, exist_ok=True) # make folder if it doesn't exist
            for file in file_paths["MR_File_Paths"]: # Get all files and move to new folder
                # Move file to new folder
                shutil.move(str(file), str(rs_mr_dcm_dir))
            rs_mr_dcm_flag = True # Set flag to true when process complete

        if not rs_rois_flag:
            rs_rois_dir.mkdir(parents=True, exist_ok=True) # make folder if it doesn't exist
            for file in file_paths["RS_File_Paths"]: # Get all files and move to new folder
                # Move file to new folder
                shutil.move(str(file), str(rs_rois_dir))
            rs_rois_flag = True # Set flag to true when process complete

        if rs_ct_dcm_flag and rs_mr_dcm_flag and rs_rois_flag: # Continue if all folders valid
            print("Located files and created necessary folders successfully.")
            rois_flag = True
            return rois_flag

# Check if we have a PL Map
def check_pl_map(case):

    # Check if we have a PL Map
    pl_map = False # set flag to false first
    for exam in case.Examinations:
        if exam.Name == "PL Map":
            print("PL Map already created.")
            pl_map = True # set flag to true

    return pl_map

# Check if we have CT Planning
def check_ct_planning(case):
    # Check if we already have a CT Planning exam
    ct_planning = False # set flag to false first
    for exam in case.Examinations:
        if "CT" in exam.Name:
            if exam.Name == "CT Planning":
                ct_planning = True # set flag to true

    # Rename first CT scan to CT Planning
    while not ct_planning:
        for exam in case.Examinations:
            if "CT" in exam.Name:
                print(f"Renamed '{exam.Name} to 'CT Planning'")
                exam.Name = "CT Planning"
                ct_planning = True
                break
        
        if not ct_planning:
            # Raise error if no CT scan found
            raise ValueError("No CT scan found.")
        
    return case
    