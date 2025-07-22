
"""
Adapted script provided from https://doi.org/10.3389/fonc.2019.00810, appendix 3. 
Edits made to update code to function with TOH RayStation API. Original description
provided below remains valid.

GBM dMRI Tractography Script version 2.0.0
Description: Script to expand a GTV volume into an anisotropic CTV using diffusion-weighted MR 
information processed using the path_length function in Diffusion Imaging in Python (DIPY) 
(Kesshi Jordan, UCSF Radiology Pull Request #1114).
Inputs: Minimum path length map (PLmap) produced by DIPY using the GTV as the region of interest 
and a dataset of streamlines modeling white matter tracks of interest (e.g. tractography seeded from GTV)
Output: CTV contours (Uniform and non-uniform) expanded away from the GTV along white matter 
tracks modeled using tractography
Requirements: the planning CT must be named 'CT Planning' & the PLmap 'PLmap'. PLmap and 
CT Planning are co-registered. GTV and Brain defined on CT Planning.
Running the script: define the 'PLmap' as primary and the 'CT Planning' as secondary. Then Run.
Make sure the PLmap and CT Planning are in the same frame of reference.
"""
from connect import *
import math
import numpy as np

# #***********************************
# Main Program
# #***********************************

# Environment setup parameters
db = get_current("PatientDB")
machine_db = get_current("MachineDB")
patient = get_current("Patient")
case = get_current("Case")
examination = get_current("Examination")
structure_set = case.PatientModel.StructureSets[examination.Name]
planning_examination = case.Examinations['CT Planning']
plmap_examination = case.Examinations['PLmap']

# Get name of GTV ROI
roi_names = case.PatientModel.RegionsOfInterest.keys()
gtv_rois = [name for name in roi_names if "GTV" in name]
gtv_roi_name = gtv_rois[0] # Assume length one for gtv rois

# Get registration
# Check if registration from CT Planning to PLmap already made
source_reg = [reg for reg in case.RigidRegistrations if reg.FromExamination.Name == "CT Planning"
                and reg.ToExamination.Name == "PLmap"]
if source_reg:
    # Take first registration in list
    source_reg = source_reg[0]
    if source_reg.Name != "CT Planning to PLmap": # Make sure registration has expected name
         source_reg = [] # Set to empty if not the expected name

if not source_reg:
    # Try to get proper registration from CT to MR
    source_reg = [reg for reg in case.RigidRegistrations if reg.FromExamination.Name == "CT Planning"
                and reg.ToExamination.Name == "MR 1"]
    if source_reg:
        # Take first registration if found registration from CT to MR
        source_reg = source_reg[0]
        # Get transformation matrix
        trans_matrix = source_reg.RigidTransformationMatrix
    else:
        # Try to find registration from MR to CT now
        source_reg = [reg for reg in case.RigidRegistrations 
                    if reg.FromExamination.Name == "MR 1"
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
            print(trans_matrix)
        else: 
            raise ValueError("No valid image registrations found.")

    case.CreateNamedIdentityImageRegistration(
        FromExaminationName = "CT Planning",
        ToExaminationName = "PLmap",
        RegistrationName = "CT Planning to PLmap",
        Description = ""
    )

    case.RigidRegistrations[len(case.RigidRegistrations)-1].SetImageRegistrationMatrix(
                                                            TransformationMatrix = trans_matrix)

case.PatientModel.CopyRoiGeometries(SourceExamination=case.Examinations['CT Planning'],
                                    TargetExaminationNames=["PLmap"], RoiNames=[gtv_roi_name],
                                    ImageRegistrationNames=["CT Planning to PLmap"],
                                    TargetExaminationNamesToSkipAddedReg=[])
case.PatientModel.CopyRoiGeometries(SourceExamination=case.Examinations['CT Planning'], 
                                    TargetExaminationNames=["PLmap"], RoiNames=["Brain"],
                                    ImageRegistrationNames=["CT Planning to PLmap"],
                                    TargetExaminationNamesToSkipAddedReg=[])
try:
    case.PatientModel.RegionsOfInterest['PLmap_5mm'].DeleteRoi()
    case.PatientModel.RegionsOfInterest['PLmap_1cm'].DeleteRoi()
    case.PatientModel.RegionsOfInterest['PLmap_2cm'].DeleteRoi()
    case.PatientModel.RegionsOfInterest['PLmap_3cm'].DeleteRoi()
    case.PatientModel.RegionsOfInterest['PLmap_4cm'].DeleteRoi()
    case.PatientModel.RegionsOfInterest['CTV_DTI_5mm'].DeleteRoi()
    case.PatientModel.RegionsOfInterest['CTV_DTI_1cm'].DeleteRoi()
    case.PatientModel.RegionsOfInterest['CTV_DTI_2cm'].DeleteRoi()
    case.PatientModel.RegionsOfInterest['CTV_DTI_3cm'].DeleteRoi()
    case.PatientModel.RegionsOfInterest['CTV_DTI_4cm'].DeleteRoi()
    case.PatientModel.RegionsOfInterest['CTV_UniformExp_5mm'].DeleteRoi()
    case.PatientModel.RegionsOfInterest['CTV_UniformExp_1cm'].DeleteRoi()
    case.PatientModel.RegionsOfInterest['CTV_UniformExp_2cm'].DeleteRoi()
    case.PatientModel.RegionsOfInterest['CTV_UniformExp_3cm'].DeleteRoi()
    case.PatientModel.RegionsOfInterest['CTV_UniformExp_4cm'].DeleteRoi()
except:
    pass

with CompositeAction('Gray level threshold on PLmap image'):
    
        # MyThreshold = -1024

        MyThreshold = examination.Series[0].ImageStack.MinStoredValue # -1024 for CT. 0 for MR
        MaxNumPts = 5000 # Max number of points for simplifying contours
        AreaThreshold = 0.25 # Minimum area threshold for simplifying contours

        retval_0 = case.PatientModel.CreateRoi(Name="PLmap_5mm", Color="White", Type="Undefined", # changing from Type="Organ" to "Undefined"
                                                TissueName=None, RoiMaterial=None)
        retval_0.GrayLevelThreshold(Examination=examination, LowThreshold=MyThreshold, # originally LowThreshold=MyThreshold+2
                                HighThreshold=MyThreshold+5, PetUnit="", BoundingBox=None)

        retval_0 = case.PatientModel.CreateRoi(Name="PLmap_1cm", Color="Yellow", Type="Undefined", # changing from Type="Organ" to "Undefined"
                                                TissueName=None, RoiMaterial=None)
        retval_0.GrayLevelThreshold(Examination=examination, LowThreshold=MyThreshold+5, 
                                HighThreshold=MyThreshold+10, PetUnit="", BoundingBox=None)

        retval_0 = case.PatientModel.CreateRoi(Name="PLmap_2cm", Color="Orange", Type="Undefined", # changing from Type="Organ" to "Undefined"
                                                TissueName=None, RoiMaterial=None)
        retval_0.GrayLevelThreshold(Examination=examination, LowThreshold=MyThreshold+5, 
                                HighThreshold=MyThreshold+20, PetUnit="", BoundingBox=None)

        retval_0 = case.PatientModel.CreateRoi(Name="PLmap_3cm", Color="Red", Type="Undefined", # changing from Type="Organ" to "Undefined"
        TissueName=None, RoiMaterial=None)
        retval_0.GrayLevelThreshold(Examination=examination, LowThreshold=MyThreshold+5, 
                                HighThreshold=MyThreshold+30, PetUnit="", BoundingBox=None)

        retval_0 = case.PatientModel.CreateRoi(Name="PLmap_4cm", Color="Purple", Type="Undefined", # changing from Type="Organ" to "Undefined" 
                                        TissueName=None, RoiMaterial=None)
        retval_0.GrayLevelThreshold(Examination=examination, LowThreshold=MyThreshold+5, 
                                HighThreshold=MyThreshold+40, PetUnit="", BoundingBox=None)


        # for roi in case.PatientModel.RegionsOfInterest:
        #         print(roi.Name)

        # for roi in case.PatientModel.RegionsOfInterest:
        #         try:
        #                 # Attempt to access the contours safely
        #                 contours = roi.Contour.ContourGeometries
        #                 if len(contours) > 0:
        #                         print(f"{roi.Name} has contours")
        #                 else:   
        #                         print(f"{roi.Name} has no contours")
        #         except:
        #                 print(f"{roi.Name} is empty or contour access failed")

        case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                        TargetExaminationNames=["CT Planning"], RoiNames=["PLmap_5mm"],
                                        ImageRegistrationNames=["CT Planning to PLmap"],
                                        TargetExaminationNamesToSkipAddedReg=[])
        case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                        TargetExaminationNames=["CT Planning"], RoiNames=["PLmap_1cm"],
                                        ImageRegistrationNames=["CT Planning to PLmap"],
                                        TargetExaminationNamesToSkipAddedReg=[])
        case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                        TargetExaminationNames=["CT Planning"], RoiNames=["PLmap_2cm"],
                                        ImageRegistrationNames=["CT Planning to PLmap"],
                                        TargetExaminationNamesToSkipAddedReg=[])
        case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                        TargetExaminationNames=["CT Planning"], RoiNames=["PLmap_3cm"],
                                        ImageRegistrationNames=["CT Planning to PLmap"],
                                        TargetExaminationNamesToSkipAddedReg=[])
        case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                        TargetExaminationNames=["CT Planning"], RoiNames=["PLmap_4cm"],
                                        ImageRegistrationNames=["CT Planning to PLmap"],
                                        TargetExaminationNamesToSkipAddedReg=[])

        case.PatientModel.StructureSets['CT Planning'].SimplifyContours(RoiNames=["PLmap_5mm"],
                RemoveHoles3D=True, RemoveSmallContours=True, AreaThreshold=AreaThreshold, 
                ReduceMaxNumberOfPointsInContours=True, MaxNumberOfPoints=MaxNumPts, CreateCopyOfRoi=False)
        case.PatientModel.StructureSets['CT Planning'].SimplifyContours(RoiNames=["PLmap_1cm"], 
                RemoveHoles3D=True, RemoveSmallContours=True, AreaThreshold=AreaThreshold, 
                ReduceMaxNumberOfPointsInContours=True, MaxNumberOfPoints=MaxNumPts, CreateCopyOfRoi=False)
        case.PatientModel.StructureSets['CT Planning'].SimplifyContours(RoiNames=["PLmap_2cm"],
                RemoveHoles3D=True, RemoveSmallContours=True, AreaThreshold=AreaThreshold, 
                ReduceMaxNumberOfPointsInContours=True, MaxNumberOfPoints=MaxNumPts, CreateCopyOfRoi=False)
        case.PatientModel.StructureSets['CT Planning'].SimplifyContours(RoiNames=["PLmap_3cm"],
                RemoveHoles3D=True, RemoveSmallContours=True, AreaThreshold=AreaThreshold, 
                ReduceMaxNumberOfPointsInContours=True, MaxNumberOfPoints=MaxNumPts, CreateCopyOfRoi=False)
        case.PatientModel.StructureSets['CT Planning'].SimplifyContours(RoiNames=["PLmap_4cm"],
                RemoveHoles3D=True, RemoveSmallContours=True, AreaThreshold=AreaThreshold, 
                ReduceMaxNumberOfPointsInContours=True, MaxNumberOfPoints=MaxNumPts, CreateCopyOfRoi=False)

        # CompositeAction ends

with CompositeAction('ROI Algebra (CTV_Final, Image set: PLmap)'):

        expandingVar = 0.25 # instead of writing 0.5 (their original value) for every single direction, can easily change now

        retval_0 = case.PatientModel.CreateRoi(Name="CTV_DTI_5mm", Color="Magenta", Type="Ctv", 
                                                TissueName=None, RoiMaterial=None)
        retval_0.SetAlgebraExpression(ExpressionA={ 'Operation': "Union", 'SourceRoiNames':[gtv_roi_name], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 
                                'Posterior': 0, 'Right': 0, 'Left': 0 } }, 
                                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': ["PLmap_5mm"], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 
                                'Posterior': 0, 'Right': 0, 'Left': 0 } },ResultOperation="Union", 
                ResultMarginSettings={'Type': "Expand", 'Superior': expandingVar, 'Inferior': expandingVar,
                                      'Anterior': expandingVar, 'Posterior': expandingVar, 
                                      'Right': expandingVar, 'Left': expandingVar })
        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")
        retval_0.CreateAlgebraGeometry(Examination=examination, Algorithm="Auto", 
                ExpressionA={ 'Operation': "Union", 'SourceRoiNames': ["CTV_DTI_5mm"], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0,'Left': 0 } },
                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': ["Brain"], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="Intersection", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 })

        retval_0 = case.PatientModel.CreateRoi(Name="CTV_DTI_1cm", Color="Magenta", Type="Ctv", 
                                                TissueName=None, RoiMaterial=None)
        retval_0.SetAlgebraExpression(ExpressionA={ 'Operation': "Union", 'SourceRoiNames':[gtv_roi_name], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 
                                'Posterior': 0, 'Right': 0, 'Left': 0 } }, 
                                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': ["PLmap_1cm"], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 
                                'Posterior': 0, 'Right': 0, 'Left': 0 } },ResultOperation="Union", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': expandingVar, 'Inferior': expandingVar,
                                        'Anterior': expandingVar,  'Posterior': expandingVar, 'Right': expandingVar, 'Left': expandingVar })
        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")
        retval_0.CreateAlgebraGeometry(Examination=examination, Algorithm="Auto", 
                ExpressionA={ 'Operation': "Union", 'SourceRoiNames': ["CTV_DTI_1cm"], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0,'Left': 0 } }, 
                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': ["Brain"], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="Intersection", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 })

        retval_0 = case.PatientModel.CreateRoi(Name="CTV_DTI_2cm", Color="Magenta", Type="Ctv", 
                                                TissueName=None, RoiMaterial=None)
        retval_0.SetAlgebraExpression(ExpressionA={ 'Operation': "Union", 'SourceRoiNames':[gtv_roi_name], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 
                                'Posterior': 0, 'Right': 0, 'Left': 0 } }, 
                                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': ["PLmap_2cm"], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 
                                'Posterior': 0, 'Right': 0, 'Left': 0 } }, ResultOperation="Union", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': expandingVar,'Inferior': expandingVar,
                                        'Anterior': expandingVar, 'Posterior': expandingVar, 'Right': expandingVar, 'Left': expandingVar })
        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")
        retval_0.CreateAlgebraGeometry(Examination=examination, Algorithm="Auto", 
                ExpressionA={ 'Operation': "Union", 'SourceRoiNames': ["CTV_DTI_2cm"], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0,
                                'Right': 0,'Left': 0 } }, 
                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': ["Brain"], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="Intersection", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                        'Right': 0, 'Left': 0 })

        retval_0 = case.PatientModel.CreateRoi(Name="CTV_DTI_3cm", Color="Magenta", Type="Ctv", 
                                                TissueName=None, RoiMaterial=None)
        retval_0.SetAlgebraExpression(ExpressionA={ 'Operation': "Union", 'SourceRoiNames':[gtv_roi_name], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, 
                                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': ["PLmap_3cm"], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="Union", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': expandingVar, 'Inferior': expandingVar,
                                        'Anterior': expandingVar,'Posterior': expandingVar, 'Right': expandingVar, 'Left': expandingVar })
        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")
        retval_0.CreateAlgebraGeometry(Examination=examination, Algorithm="Auto", 
                ExpressionA={ 'Operation': "Union", 'SourceRoiNames': ["CTV_DTI_3cm"], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0,'Left': 0 } }, 
                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': ["Brain"], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="Intersection", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                        'Right': 0, 'Left': 0 })

        retval_0 = case.PatientModel.CreateRoi(Name="CTV_DTI_4cm", Color="Magenta", Type="Ctv",
                                                TissueName=None, RoiMaterial=None)
        retval_0.SetAlgebraExpression(ExpressionA={ 'Operation': "Union", 'SourceRoiNames':[gtv_roi_name], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, 
                                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': ["PLmap_4cm"], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="Union", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': expandingVar, 'Inferior': expandingVar,
                                        'Anterior': expandingVar, 'Posterior': expandingVar, 'Right': expandingVar,'Left': expandingVar })
        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")
        retval_0.CreateAlgebraGeometry(Examination=examination, Algorithm="Auto", 
                ExpressionA={ 'Operation': "Union", 'SourceRoiNames': ["CTV_DTI_4cm"], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0,'Left': 0 } }, 
                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': ["Brain"], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="Intersection", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                        'Right': 0, 'Left': 0 })

        retval_0 = case.PatientModel.CreateRoi(Name="CTV_UniformExp_5mm", Color="Blue", Type="Ctv", 
                                                TissueName=None, RoiMaterial=None)
        retval_0.SetAlgebraExpression(ExpressionA={ 'Operation': "Union", 'SourceRoiNames':[gtv_roi_name], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0.5, 'Inferior': 0.5, 'Anterior': 0.5, 'Posterior': 0.5, 
                                'Right': 0.5, 'Left': 0.5 } }, 
                                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': [], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0,'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="None", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 
                                        'Anterior': 0,'Posterior': 0, 'Right': 0, 'Left': 0 })
        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")
        retval_0.CreateAlgebraGeometry(Examination=examination, Algorithm="Auto", 
                ExpressionA={ 'Operation': "Union", 'SourceRoiNames': ["CTV_UniformExp_5mm"], 
                'MarginSettings':{ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, 
                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': ["Brain"],
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="Intersection", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                        'Right': 0, 'Left': 0 })

        retval_0 = case.PatientModel.CreateRoi(Name="CTV_UniformExp_1cm", Color="Blue", Type="Ctv", 
                                                TissueName=None, RoiMaterial=None)
        retval_0.SetAlgebraExpression(ExpressionA={ 'Operation': "Union", 'SourceRoiNames':[gtv_roi_name], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 1, 'Inferior': 1, 'Anterior': 1, 'Posterior': 1, 
                                'Right': 1, 'Left': 1 } }, 
                                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': [], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior':0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="None", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': 0,'Inferior': 0, 
                                        'Anterior': 0,'Posterior': 0, 'Right': 0,'Left': 0 })
        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")
        retval_0.CreateAlgebraGeometry(Examination=examination, Algorithm="Auto", 
                ExpressionA={ 'Operation': "Union", 'SourceRoiNames': ["CTV_UniformExp_1cm"], 
                'MarginSettings':{ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, 
                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': ["Brain"],
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="Intersection", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                        'Right': 0, 'Left': 0 })

        retval_0 = case.PatientModel.CreateRoi(Name="CTV_UniformExp_2cm", Color="Blue", Type="Ctv", 
                                                TissueName=None, RoiMaterial=None)
        retval_0.SetAlgebraExpression(ExpressionA={ 'Operation': "Union", 'SourceRoiNames':[gtv_roi_name], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 2, 'Inferior': 2, 'Anterior': 2, 'Posterior': 2, 
                                'Right': 2, 'Left': 2 } }, 
                                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': [], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior':0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="None", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 
                                        'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0 })
        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")
        retval_0.CreateAlgebraGeometry(Examination=examination, Algorithm="Auto", 
                ExpressionA={ 'Operation': "Union", 'SourceRoiNames': ["CTV_UniformExp_2cm"], 
                'MarginSettings':{ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, 
                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': ["Brain"],
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="Intersection", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                        'Right': 0, 'Left': 0 })

        retval_0 = case.PatientModel.CreateRoi(Name="CTV_UniformExp_3cm", Color="Blue", Type="Ctv", 
                                                TissueName=None, RoiMaterial=None)
        retval_0.SetAlgebraExpression(ExpressionA={ 'Operation': "Union", 'SourceRoiNames':[gtv_roi_name], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 3, 'Inferior': 3, 'Anterior': 3, 'Posterior': 3, 
                                'Right': 3, 'Left': 3 } }, 
                                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': [], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior':0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="None",
                ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 
                                        'Posterior': 0, 'Right': 0, 'Left': 0 })
        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")
        retval_0.CreateAlgebraGeometry(Examination=examination, Algorithm="Auto", 
                ExpressionA={ 'Operation': "Union", 'SourceRoiNames': ["CTV_UniformExp_3cm"], 
                'MarginSettings':{ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, 
                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': ["Brain"],
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="Intersection", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                        'Right': 0, 'Left': 0 })

        retval_0 = case.PatientModel.CreateRoi(Name="CTV_UniformExp_4cm", Color="Blue", Type="Ctv", 
                                                TissueName=None, RoiMaterial=None)
        retval_0.SetAlgebraExpression(ExpressionA={ 'Operation': "Union", 'SourceRoiNames':[gtv_roi_name], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 4, 'Inferior': 4, 'Anterior': 4, 'Posterior': 4, 
                                'Right': 4, 'Left': 4 } }, 
                                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': [], 
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior':0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="None", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 
                                        'Posterior': 0, 'Right': 0, 'Left': 0 })
        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")
        retval_0.CreateAlgebraGeometry(Examination=examination, Algorithm="Auto", 
                ExpressionA={ 'Operation': "Union", 'SourceRoiNames': ["CTV_UniformExp_4cm"], 
                'MarginSettings':{ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, 
                ExpressionB={ 'Operation': "Union", 'SourceRoiNames': ["Brain"],
                'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                'Right': 0, 'Left': 0 } }, ResultOperation="Intersection", 
                ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 
                                        'Right': 0, 'Left': 0 })

        # CompositeAction ends

case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                    TargetExaminationNames=["CT Planning"], RoiNames=["CTV_DTI_5mm"],
                                    ImageRegistrationNames=["CT Planning to PLmap"],
                                    TargetExaminationNamesToSkipAddedReg=[])
case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                    TargetExaminationNames=["CT Planning"], RoiNames=["CTV_DTI_1cm"],
                                    ImageRegistrationNames=["CT Planning to PLmap"],
                                    TargetExaminationNamesToSkipAddedReg=[])
case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                    TargetExaminationNames=["CT Planning"], RoiNames=["CTV_DTI_2cm"],
                                    ImageRegistrationNames=["CT Planning to PLmap"],
                                    TargetExaminationNamesToSkipAddedReg=[])
case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                    TargetExaminationNames=["CT Planning"], RoiNames=["CTV_DTI_3cm"],
                                    ImageRegistrationNames=["CT Planning to PLmap"],
                                    TargetExaminationNamesToSkipAddedReg=[])
case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                    TargetExaminationNames=["CT Planning"], RoiNames=["CTV_DTI_4cm"],
                                    ImageRegistrationNames=["CT Planning to PLmap"],
                                    TargetExaminationNamesToSkipAddedReg=[])
case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                    TargetExaminationNames=["CT Planning"], RoiNames=["CTV_UniformExp_5mm"],
                                    ImageRegistrationNames=["CT Planning to PLmap"],
                                    TargetExaminationNamesToSkipAddedReg=[])
case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                    TargetExaminationNames=["CT Planning"], RoiNames=["CTV_UniformExp_1cm"],
                                    ImageRegistrationNames=["CT Planning to PLmap"],
                                    TargetExaminationNamesToSkipAddedReg=[])
case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                    TargetExaminationNames=["CT Planning"], RoiNames=["CTV_UniformExp_2cm"],
                                    ImageRegistrationNames=["CT Planning to PLmap"],
                                    TargetExaminationNamesToSkipAddedReg=[])
case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                    TargetExaminationNames=["CT Planning"], RoiNames=["CTV_UniformExp_3cm"],
                                    ImageRegistrationNames=["CT Planning to PLmap"],
                                    TargetExaminationNamesToSkipAddedReg=[])
case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                    TargetExaminationNames=["CT Planning"], RoiNames=["CTV_UniformExp_4cm"],
                                    ImageRegistrationNames=["CT Planning to PLmap"],
                                    TargetExaminationNamesToSkipAddedReg=[])