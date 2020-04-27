import ifcopenshell as ifc
import pprint as pp
import pandas as pd
import numpy as np
import os
import pathlib
import datachecks

pd.set_option("display.max_rows", None, "display.max_columns", None, "display.max_colwidth", -1, "display.width", None)
IFC_dir = 'C:/Users/ArjanPeeters/PycharmProjects/IfcDashBoard/TestModel DataSetSchependomlaan'
single_ifc = "C:/Users/ArjanPeeters/PycharmProjects/IfcDashBoard/592-02_Onthardingsgebouw.ifc"
props_to_check = ['LoadBearing', 'FireRating', 'IsExternal', 'AcousticRating', 'Phase']
exlude_element_list = ['IfcProject']

ifc_files = []
for root, dirs, files in os.walk(IFC_dir):  # get all IFC files in directory
    for file in files:
        if file.lower().endswith(".ifc"):
            found_file = os.path.join(root.replace('/', '\\'), file)
            print(found_file)
            ifc_files.append(found_file)
print(ifc_files)

ProjectGlobalIds = []
ifc_projects_df = pd.DataFrame()
ifc_buildingstoreys_df = pd.DataFrame()
ifc_elements_df = pd.DataFrame()
for file in ifc_files:
    try:
        ifc_file = ifc.open(file)
    except OSError:
        print(file)

    project = ifc_file.by_type('IfcProject')[0]
    if project.GlobalId in ProjectGlobalIds:
        print('File al gedaan:', project.GlobalId, project.Name)
        continue
    ProjectGlobalIds.append(project.GlobalId)
    print(project.GlobalId, project.Name)

    project_info = {
        'ProjectGlobalId': project.GlobalId,
        'ProjectName': project.Name,
        'FileName': os.path.basename(file),
        'ProjectApplicationName': project.OwnerHistory.OwningApplication.ApplicationFullName,
        'ProjectOrganizationName': project.OwnerHistory.OwningUser.TheOrganization.Name
    }

    project_info_df = pd.Series(project_info)  # turn dict into DataFrame Series
    ifc_projects_df = ifc_projects_df.append(project_info_df, ignore_index=True)  # add to DataFrame

    # get all the stories!
    building_stories = ifc_file.by_type('IfcBuildingStorey')
    for storey in building_stories:
        storey_info = {
            'ProjectGlobalId': project.GlobalId,
            'ProjectName': project.Name,
            'StoreyGlobalId': storey.GlobalId,
            'StoreyName': storey.Name,
            'StoreyElevation': storey.Elevation
            }
        ifc_buildingstoreys_df = ifc_buildingstoreys_df.append(pd.Series(storey_info), ignore_index=True)

    all_elements = ifc_file.by_type('IfcProduct')
    for element in all_elements:
        if element not in exlude_element_list:
            PropertySets = {}
            for check in props_to_check:  # prepare a property dict with None elements
                PropertySets['ElementProperty' + check] = None
            for definition in element.IsDefinedBy:
                if definition.is_a('IfcRelDefinesByProperties'):
                    if definition.RelatingPropertyDefinition.is_a('IfcPropertySet'):
                        if definition.RelatingPropertyDefinition.Name.lower().endswith("common"):
                            # check for properties in the Common PSets
                            for prop in definition.RelatingPropertyDefinition.HasProperties:
                                if prop.Name in props_to_check:
                                    PropertySets['ElementProperty' + prop.Name] = prop.NominalValue[0]
                        if 'phas' in definition.RelatingPropertyDefinition.Name.lower():
                            # check for phasing PSets
                            PS = PropertySets['ElementPropertyPhase']
                            PropertySets['ElementPropertyPhase'] = '{Previous}{PName}:{PValue}'.format(
                                Previous=PS + "," if PS is not None else "",
                                PName=definition.RelatingPropertyDefinition.Name,
                                PValue=definition.RelatingPropertyDefinition.HasProperties[0].NominalValue[0]
                            )

            # get classification associated with elements.
            class_dict = {
                'ClassificationName': None,
                'ClassificationItemReference': None,
                'ClassificationItemDescription': None,
                'ClassificationAssessment': 'Niet gecodeerd'
            }  # start a dict with everything None
            material_list = None  # because an element might have more materials it can be a list

            # Loop for getting associatetions for element
            # Classifications and Materials
            for has_associations in element.HasAssociations:
                if has_associations.is_a('IfcRelAssociatesClassification'):
                    if has_associations.RelatingClassification.Name is not None:
                        class_dict = {
                            'ClassificationName': has_associations.Name,
                            'ClassificationItemReference': str(has_associations.RelatingClassification.ItemReference),
                            'ClassificationItemDescription': str(has_associations.RelatingClassification.Name),
                            'ClassificationAssessment': datachecks.rate_classification(
                                str(has_associations.RelatingClassification.ItemReference))
                        }
                elif has_associations.is_a('IfcRelAssociatesMaterial'):
                    if has_associations.RelatingMaterial.is_a('IfcMaterial'):
                        material_list = has_associations.RelatingMaterial.Name
                    if has_associations.RelatingMaterial.is_a('IfcMaterialList'):
                        material_list = []
                        for materials in has_associations.RelatingMaterial.Materials:
                            material_list.append(materials.Name)
                    if has_associations.RelatingMaterial.is_a('IfcMaterialLayerSetUsage'):
                        material_list = []
                        for materials in has_associations.RelatingMaterial.ForLayerSet.MaterialLayers:
                            material_list.append(materials.Material.Name)

            if isinstance(material_list, list) and len(material_list) == 1:  # if only one item in list, discard list
                material_list = material_list[0]

            # Make Dict with info about the element
            element_right_info = {
                'ProjectGlobalId': project.GlobalId,
                'ProjectName': project.Name,
                'ElementGlobalId': element.GlobalId,
                'ElementName': element.Name,
                'ElementType': element.ObjectType, 'Type': element.is_a(),
                'ElementMaterialName': material_list
                }
            element_right_info.update(class_dict)  # append classification dict
            element_right_info.update(PropertySets)  # append propertysets dict
            element_right_info_df = pd.Series(element_right_info)  # turn dict into DataFrame Series
            # append this row to the DataFrame
            ifc_elements_df = ifc_elements_df.append(element_right_info_df, ignore_index=True)

# Setting indexes for the DataFrames
ifc_projects_df.set_index('ProjectGlobalId', inplace=True)
ifc_elements_df.set_index('ElementGlobalId', inplace=True)
ifc_buildingstoreys_df.set_index('StoreyGlobalId', inplace=True)

# print statements for viewing the data
print(ifc_elements_df)
print(ifc_elements_df.shape)
print(ifc_projects_df)
print(ifc_projects_df.shape)
print(ifc_buildingstoreys_df)
print(ifc_buildingstoreys_df.shape)
print(ifc_elements_df.ProjectName.value_counts())
print(ifc_elements_df.Type.value_counts())
print(ifc_elements_df.ClassificationName.value_counts())
print(ifc_elements_df.ClassificationItemReference.value_counts())

# write everything to excel.
writer = pd.ExcelWriter('test_export.xlsx', engine='xlsxwriter')
ifc_projects_df.to_excel(writer, 'projects')
ifc_elements_df.to_excel(writer, 'elements')
ifc_buildingstoreys_df.to_excel(writer, 'buildingstoreys')
writer.save()

print('____COMPLETE____')