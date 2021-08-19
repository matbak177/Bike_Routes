import arcpy
import os

#define a workspace folder
folder=r"C:\Users\mateusz.bak\Desktop\ost"#change path
nazwa="rower"

#create geodatabase
if arcpy.Exists(os.path.join(folder,nazwa)+".gdb"):
    arcpy.Delete_management(os.path.join(folder,nazwa)+".gdb")
    arcpy.CreateFileGDB_management(folder, nazwa)
else:
    arcpy.CreateFileGDB_management(folder,nazwa)

print("a geodatabase has been created")

#create a feature dataset
name_1="WRM"
name_2="trasy"
name_3="stacje_selekcja"
name_4="stacje_osobno"
ref=arcpy.SpatialReference(102194)

arcpy.CreateFeatureDataset_management(os.path.join(folder,nazwa)+".gdb", name_1,ref)
arcpy.CreateFeatureDataset_management(os.path.join(folder,nazwa)+".gdb", name_2,ref)
arcpy.CreateFeatureDataset_management(os.path.join(folder,nazwa)+".gdb", name_3,ref)
arcpy.CreateFeatureDataset_management(os.path.join(folder,nazwa)+".gdb", name_4,ref)

print("a feaute dataset has been created")

#overwriting results
arcpy.env.workspace=folder
arcpy.env.overwriteOutput = True

#Create a new shp layer from the csv file, and transform the coordinates
input_file=folder+r"\stacje.csv"
lng="dlugosc"
lat="szerokosc"
name="stacje_start"
spatial=arcpy.SpatialReference(4326)
spatial2=arcpy.SpatialReference(102194)

arcpy.MakeXYEventLayer_management(input_file,lng,lat,name,spatial)
arcpy.Project_management(name,"rower.gdb\stacje",spatial2)
arcpy.FeatureClassToFeatureClass_conversion(name,"rower.gdb\\WRM",name)

print("station has been created")

#create a rental layer
in_features=r"rower.gdb\WRM\stacje_start"
out_layer="stacja_layer"
out_field="nazwa"
table="dzien.dbf"
join_table=r"rower.gdb\dzien_dbf"
join_field="RETURN_PLA"
name_t="dzien"
lng="dlugosc"
lati="szerokosc"
name="stacja_day"
name_out="rower.gdb\stacje_dzien"

#second table
table2="s_rental.csv"
arcpy.TableToGeodatabase_conversion(table,"rower.gdb")
arcpy.TableToGeodatabase_conversion(table2,"rower.gdb")

join_table2=r"rower.gdb\s_rental_csv"
join_field2="s_rental"

try:
    arcpy.MakeFeatureLayer_management(in_features,out_layer)
    arcpy.JoinField_management(join_table,join_field,out_layer,out_field)
    
    arcpy.MakeXYEventLayer_management(join_table,lng,lati,name,spatial)
    #arcpy.FeatureClassToShapefile_conversion(name2, os.path.join(folder,nazwa)+".gdb")
    arcpy.Project_management(name,name_out,spatial2)
except:
    print("something goes wrong, try again")

join_table2=r"rower.gdb\s_rental_csv"
join_field2="s_rental"

in_features=r"rower.gdb\stacje_dzien"
out_field="rental_pla"

arcpy.MakeFeatureLayer_management(in_features,out_layer)
arcpy.AddJoin_management(out_layer,out_field,join_table2,join_field2)
arcpy.CopyFeatures_management(out_layer,r"rower.gdb\stacje_day")

print("rental layer has been created - stacje_day")

#add roads and new columns
in_layer=r"drogi_bdot.shp"
out_name="droga_bdot"
out_layer="rower.gdb\WRM"

arcpy.FeatureClassToFeatureClass_conversion(in_layer,out_layer,out_name)

droga ="rower.gdb\WRM\droga_bdot"
arcpy.AddField_management(droga, "v", "LONG", field_length=10)
arcpy.AddField_management(droga, "minutes", "FLOAT", field_length=25)

with arcpy.da.UpdateCursor(droga, ["v"]) as cursor:
    for row in cursor:
        row[0] = 5
        cursor.updateRow(row)

arcpy.CalculateField_management(droga, "minutes", "[length]/([v]*60)")

print("columns has been added")

#Station selection
points="rower.gdb\stacje"
outpath="rower.gdb\stacje_osobno"
arcpy.MakeFeatureLayer_management(points, "points_layer")

dict={}
with arcpy.da.SearchCursor(points,["id","stacja"]) as point_cursor:
    for i in point_cursor:
        dict[int(i[0])]=int(i[1])
        arcpy.SelectLayerByAttribute_management("points_layer","NEW_SELECTION",""" "stacja"= {} """.format(i[1]))
        arcpy.FeatureClassToFeatureClass_conversion("points_layer",outpath,"stacja_{}".format(i[1]))

print("station selection has been created")

#Rental selection
points="rower.gdb\stacje"
points2=r"rower.gdb\stacje_day"
outpath=r"rower.gdb\stacje_selekcja"
lista=[]

arcpy.MakeFeatureLayer_management(points, "points_layer")
arcpy.MakeFeatureLayer_management(points2, "points_layer2")

with arcpy.da.SearchCursor(points,["stacja","nazwa"]) as point_cursor:
    for i in point_cursor:
        #where_clause = "stacja={}".format(i[1])
        with arcpy.da.SearchCursor(points2, ["stacja","rental_pla"]) as cur:
            arcpy.SelectLayerByAttribute_management("points_layer2","NEW_SELECTION",""" "s_rental_csv_stacja_r"= {} """.format(i[0]))
            arcpy.FeatureClassToFeatureClass_conversion("points_layer2",outpath,"s_{}".format(i[0]))

print("rental selection has been created")

#Create network data from a template
arcpy.CheckOutExtension("Network")

network_dataset_template="szablon.xml"
output_feature_dataset="rower.gdb\WRM"

arcpy.CreateNetworkDatasetFromTemplate_na(network_dataset_template, output_feature_dataset)

network = "rower.gdb\WRM\WRM_ND"
accumulateAttributeName = "Meters" #["Meters","Minutes"]
impedanceAttribute = "minutes"

newpath = r"rower.gdb\trasy"

arcpy.CheckOutExtension("Network")

for i,l in dict.items():

    outNALayer="Trasa_{}".format(i)
    #if we need a route to be modified in the form of a lyr file - remove # below and at the end of the loop 
    #outLayerFile=folder+r"\\t_{}".format(i)
    inFacilities = r"rower.gdb\\stacje_osobno\\stacja_{}".format(l)
    inIncidents = r"rower.gdb\\stacje_selekcja\\s_{}".format(l)
    arcpy.na.BuildNetwork(network)
    try:
        NAResultObject=arcpy.na.MakeClosestFacilityLayer(network,outNALayer,impedanceAttribute,"TRAVEL_FROM","",1,"","NO_UTURNS")

        outNALayer = NAResultObject.getOutput(0)

        subLayerNames = arcpy.na.GetNAClassNames(outNALayer)

        facilitiesLayerName = subLayerNames["Facilities"]
        incidentsLayerName = subLayerNames["Incidents"]
        routeLayerName = subLayerNames["CFRoutes"]

        fieldMappings = arcpy.na.NAClassFieldMappings(outNALayer, incidentsLayerName)
        fieldMappings["Name"].mappedFieldName = "nazwa"
        arcpy.na.AddLocations(outNALayer, facilitiesLayerName, inFacilities, fieldMappings, "")

        fieldMappings = arcpy.na.NAClassFieldMappings(outNALayer, facilitiesLayerName)
        fieldMappings["Name"].mappedFieldName = "stacje_dzien_nazwa"
        arcpy.na.AddLocations(outNALayer, incidentsLayerName, inIncidents,fieldMappings, "")

        arcpy.na.Solve(outNALayer)

        RoutesSubLayer = arcpy.mapping.ListLayers(outNALayer, routeLayerName)[0]

        #arcpy.management.SaveToLayerFile(outNALayer,outLayerFile,"RELATIVE")
        arcpy.FeatureClassToFeatureClass_conversion(RoutesSubLayer, newpath,"t_{}".format(l))
    except:
        print('Set {} is empty'.format(l))

print "Routes has been created"

#merge layer
out=r"rower.gdb\\WRM\\t_calosc"
lista=[]
arcpy.env.workspace=r"rower.gdb\\trasy"

for fc in arcpy.ListFeatureClasses():
    lista.append(fc)

arcpy.Merge_management(lista,out)

#we want to know how much each route has been traveled. For this purpose, we will divide the routes we have just received into 2 stages
#first
arcpy.Dissolve_management(r"rower.gdb\\WRM\\t_calosc",r"rower.gdb\\WRM\\dissolve")
arcpy.SplitLine_management(r"rower.gdb\\WRM\\dissolve",r"rower.gdb\\WRM\\split")

#second
arcpy.SplitLine_management(r"rower.gdb\\WRM\\t_calosc",r"rower.gdb\\WRM\\split2")

#Spatial join
target=r"rower.gdb\\WRM\\split"
join=r"rower.gdb\\WRM\\split2"
out=r"rower.gdb\\WRM\\t_koncowe"
arcpy.SpatialJoin_analysis(target,join,out,"JOIN_ONE_TO_ONE","KEEP_ALL","","INTERSECT")

print('file t_koncowe contains the final result')
print('now it is enough to change the way the layer is displayed in the symbolization so that the line thickness reflects the number of passes')























