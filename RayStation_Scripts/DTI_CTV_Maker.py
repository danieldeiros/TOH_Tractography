
"""
Adapted script provided from https://doi.org/10.3389/fonc.2019.00810, appendix 3. 
Edits made to update code to function with TOH RayStation API. Original description
provided below remains valid.

GBM dMRI Tractography Script version 2.0.0
Description: Script to expand a GTV volume into an anisotropic CTV using diffusion-weighted MR 
information processed using the path_length function in Diffusion Imaging in Python (DIPY) 
(Kesshi Jordan, UCSF Radiology Pull Request #1114).
Inputs: Minimum path length map (PL map) produced by DIPY using the GTV as the region of interest 
and a dataset of streamlines modeling white matter tracks of interest (e.g. tractography seeded from GTV)
Output: CTV contours (Uniform and non-uniform) expanded away from the GTV along white matter 
tracks modeled using tractography
Requirements: the planning CT must be named 'CT Planning' & the PL map 'PL Map'. PL map and 
CT Planning are co-registered. GTV and Brain defined on CT Planning.
Running the script: define the 'PL Map' as primary and the 'CT Planning' as secondary. Then Run.
Make sure the PL Map and CT Planning are in the same frame of reference.
"""
# Import packages
from connect import *
import math
import numpy as np

# Import functions
from Subscripts.RS_Utils import check_description, get_img_registration

# #***********************************
# Main Program
# #***********************************

def dti_ctv_maker(db, machine_db, patient, case, examination, structure_set, planning_examination, plmap_examination):

        # Get name of GTV ROI
        roi_names = case.PatientModel.RegionsOfInterest.keys()
        gtv_rois = [name for name in roi_names if "GTV" in name]
        gtv_roi_name = gtv_rois[0] # Assume length one for gtv rois. i.e. assuming only one GTV ROI

        # Check for MRIs
        mr_exam_names = [] # set list empty for now
        for exam in case.Examinations:
                if "MR" in exam.Name:
                        mr_exam_names.append(exam.Name) # add mr name to list

        # Get MR exam name with FA in the description
        mr_exam_name = check_description(case, mr_exam_names)

        # Get registration
        case = get_img_registration(case, mr_exam_name, pl_map=True)

        case.PatientModel.CopyRoiGeometries(SourceExamination=case.Examinations['CT Planning'],
                                        TargetExaminationNames=["PL Map"], RoiNames=[gtv_roi_name],
                                        ImageRegistrationNames=["Image registration CT Planning - PL Map"],
                                        TargetExaminationNamesToSkipAddedReg=[])
        case.PatientModel.CopyRoiGeometries(SourceExamination=case.Examinations['CT Planning'], 
                                        TargetExaminationNames=["PL Map"], RoiNames=["Brain"],
                                        ImageRegistrationNames=["Image registration CT Planning - PL Map"],
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

        with CompositeAction('Gray level threshold on PL Map image'):
        
                # MyThreshold = -1024

                MyThreshold = examination.Series[0].ImageStack.MinStoredValue # -1024 for CT. 0 for MR
                MaxNumPts = 2500 # Max number of points for simplifying contours # Originally 2000 in paper
                AreaThreshold = 1 # Minimum area threshold for simplifying contours # Originally 1 in paper

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

                case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                                TargetExaminationNames=["CT Planning"], RoiNames=["PLmap_5mm"],
                                                ImageRegistrationNames=["Image registration CT Planning - PL Map"],
                                                TargetExaminationNamesToSkipAddedReg=[])
                case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                                TargetExaminationNames=["CT Planning"], RoiNames=["PLmap_1cm"],
                                                ImageRegistrationNames=["Image registration CT Planning - PL Map"],
                                                TargetExaminationNamesToSkipAddedReg=[])
                case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                                TargetExaminationNames=["CT Planning"], RoiNames=["PLmap_2cm"],
                                                ImageRegistrationNames=["Image registration CT Planning - PL Map"],
                                                TargetExaminationNamesToSkipAddedReg=[])
                case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                                TargetExaminationNames=["CT Planning"], RoiNames=["PLmap_3cm"],
                                                ImageRegistrationNames=["Image registration CT Planning - PL Map"],
                                                TargetExaminationNamesToSkipAddedReg=[])
                case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                                TargetExaminationNames=["CT Planning"], RoiNames=["PLmap_4cm"],
                                                ImageRegistrationNames=["Image registration CT Planning - PL Map"],
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

        with CompositeAction('ROI Algebra (CTV_Final, Image set: PL Map)'):

                expandingVar = 0.5 # instead of writing 0.5 (their original value) for every single direction, can easily change now

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
                                        ImageRegistrationNames=["Image registration CT Planning - PL Map"],
                                        TargetExaminationNamesToSkipAddedReg=[])
        case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                        TargetExaminationNames=["CT Planning"], RoiNames=["CTV_DTI_1cm"],
                                        ImageRegistrationNames=["Image registration CT Planning - PL Map"],
                                        TargetExaminationNamesToSkipAddedReg=[])
        case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                        TargetExaminationNames=["CT Planning"], RoiNames=["CTV_DTI_2cm"],
                                        ImageRegistrationNames=["Image registration CT Planning - PL Map"],
                                        TargetExaminationNamesToSkipAddedReg=[])
        case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                        TargetExaminationNames=["CT Planning"], RoiNames=["CTV_DTI_3cm"],
                                        ImageRegistrationNames=["Image registration CT Planning - PL Map"],
                                        TargetExaminationNamesToSkipAddedReg=[])
        case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                        TargetExaminationNames=["CT Planning"], RoiNames=["CTV_DTI_4cm"],
                                        ImageRegistrationNames=["Image registration CT Planning - PL Map"],
                                        TargetExaminationNamesToSkipAddedReg=[])
        case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                        TargetExaminationNames=["CT Planning"], RoiNames=["CTV_UniformExp_5mm"],
                                        ImageRegistrationNames=["Image registration CT Planning - PL Map"],
                                        TargetExaminationNamesToSkipAddedReg=[])
        case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                        TargetExaminationNames=["CT Planning"], RoiNames=["CTV_UniformExp_1cm"],
                                        ImageRegistrationNames=["Image registration CT Planning - PL Map"],
                                        TargetExaminationNamesToSkipAddedReg=[])
        case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                        TargetExaminationNames=["CT Planning"], RoiNames=["CTV_UniformExp_2cm"],
                                        ImageRegistrationNames=["Image registration CT Planning - PL Map"],
                                        TargetExaminationNamesToSkipAddedReg=[])
        case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                        TargetExaminationNames=["CT Planning"], RoiNames=["CTV_UniformExp_3cm"],
                                        ImageRegistrationNames=["Image registration CT Planning - PL Map"],
                                        TargetExaminationNamesToSkipAddedReg=[])
        case.PatientModel.CopyRoiGeometries(SourceExamination=examination, 
                                        TargetExaminationNames=["CT Planning"], RoiNames=["CTV_UniformExp_4cm"],
                                        ImageRegistrationNames=["Image registration CT Planning - PL Map"],
                                        TargetExaminationNamesToSkipAddedReg=[])

        # Save
        patient.Save()