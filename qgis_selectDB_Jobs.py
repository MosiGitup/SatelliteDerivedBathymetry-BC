"""
# Copyright 2023 © Centre Interdisciplinaire de développement en Cartographie des Océans (CIDCO), Tous droits réservés
@Mohsen_Feizabadi ---
"""

from qgis.core import *
from qgis.gui import *
from qgis.PyQt.QtWidgets import *
from qgis.analysis import QgsNativeAlgorithms
import os, sys, csv
import schedule, time
import subprocess
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from subprocess import call
from featureStyle import pointStyle, rasterStyle
from qgis.PyQt.QtCore import QSize
from osgeo import gdal
import numpy as np
import pandas as pd
from PIL import Image

'''
***** QGIS configuration and load data from server by using API *****
'''

project_path = sys.argv[1]  # e.g. "/home/.../SDB/"
geojson_path = sys.argv[2]  # This directory exists
river_path = sys.argv[3]    # This directory exists
map_dir = sys.argv[4]       # The image exists in the main directory

## *** Initialize QGIS application
QgsApplication.setPrefixPath("/usr/bin/qgis.bin", True)
qgs = QgsApplication([], False)
qgs.initQgis()

## *** Set the application path
qgs.setPluginPath('/usr/lib/qgis/plugins')
sys.path.append('/usr/share/qgis/python/plugins')

## *** Import processing modules
import processing
from processing.core.Processing import Processing

Processing.initialize()
QgsProject.instance().removeAllMapLayers()
project = QgsProject.instance()
crs = QgsCoordinateReferenceSystem("EPSG:4326")
project.setCrs(crs)

## *** Select the project and related Mysql
reproject_crs = QgsCoordinateReferenceSystem("EPSG:3156")
bcRegions = ['T09UWS', 'T09UXS', 'T09UYR', 'T09UYS', 'T10UCV', 'T10UCA',
             'T10UCB', 'T10UDV', 'T10UDA', ]
epsg_region = ['EPSG --> 3156', 'EPSG --> 3157']
display_map = subprocess.Popen(["display", map_dir])
print('\033[1;34mREGIONS: ''\033[0m')
k = 0
for j in range(len(epsg_region)):
    print('\033[1;36m' + epsg_region[j] + '\033[0m')
    for i in range(k, len(bcRegions)):
        print(str(i + 1), '- ' + bcRegions[i])
        k += 1
        if i == 1:
            break
print('')
region_index = input('\033[1;32mSelect the region: ''\033[0m')
display_map.kill()

if 1 <= int(region_index) <= 2:
    reproject_crs = QgsCoordinateReferenceSystem("EPSG:3156")
    river_file = "River_epsg3156.shp"
elif 3 <= int(region_index) <= 9:
    reproject_crs = QgsCoordinateReferenceSystem("EPSG:3157")
    river_file = "River_epsg3157.shp"
if region_index == '1':
    mapJson = geojson_path + '/' + 'T09UWS.geojson'
elif region_index == '2':
    mapJson = geojson_path + '/' + 'T09UXS.geojson'
elif region_index == '3':
    mapJson = geojson_path + '/' + 'T09UYR.geojson'
elif region_index == '4':
    mapJson = geojson_path + '/' + 'T09UYS.geojson'
elif region_index == '5':
    mapJson = geojson_path + '/' + 'T10UCV.geojson'
elif region_index == '6':
    mapJson = geojson_path + '/' + 'T10UCA.geojson'
elif region_index == '7':
    mapJson = geojson_path + '/' + 'T10UCB.geojson'
elif region_index == '8':
    mapJson = geojson_path + '/' + 'T10UDV.geojson'
elif region_index == '9':
    mapJson = geojson_path + '/' + 'T10UDA.geojson'

## *** Create directory
seconds = time.time()
yr_mon_day = time.localtime(seconds)
pro_dir = 'SurBat_' + str(yr_mon_day.tm_year) + str(yr_mon_day.tm_mon) + str(yr_mon_day.tm_mday) + '-' + str(yr_mon_day.tm_hour) + 'h' + str(yr_mon_day.tm_min)
path = os.path.join(project_path, pro_dir)
try:
    os.mkdir(path)
except:
    print('')

print('\033[1;34mREQUIRED DATE OF BATHYMETRY DATA''\033[0m')
yr = int(input('\033[1;32mYear: '))
mn = int(input('\033[1;32mMonth: '))
dy = int(input('\033[1;32mDay: '))
td = int(input('\033[1;32mData Interval (in hour): '))

## *** Load the GeoJSON and get its extent
_, mapJson_name = os.path.split(mapJson)
mapJson_layer = QgsVectorLayer(mapJson, mapJson_name[:-8], 'ogr')
mapJson_extent = mapJson_layer.extent()
xmin_tile = mapJson_extent.xMinimum()
xmax_tile = mapJson_extent.xMaximum()
ymin_tile = mapJson_extent.yMinimum()
ymax_tile = mapJson_extent.yMaximum()

db_bathymetryCsv = project_path + mapJson_name[:-8] + "_" + pro_dir[7:pro_dir.find('-')] + "_" + str(yr) + str(mn) + str(dy) + ".csv"
if not os.path.isfile(db_bathymetryCsv):
    from ApiCsbBathy import CsvApi, year, month, day

## *** Verify Sentinel-2 images for the current timestamp
from readCSVfromAPI import sdbCSVpath
from SentinelAcquisition import SentinelQuery
date1, date2, vectorSDB, vectorSDB_date, tileName, lon, lat, z_el, z_cd = sdbCSVpath(db_bathymetryCsv)
imageList, uuidList, filtered_vectorSDB = SentinelQuery(project_path + pro_dir, mapJson, date1, date2, vectorSDB, vectorSDB_date, tileName)

output4 = "BathymetryPointsInsideTile.shp"
processing.run("native:createpointslayerfromtable", {'INPUT': QgsProcessingFeatureSourceDefinition(db_bathymetryCsv, selectedFeaturesOnly=False),
                                                     'XFIELD': lon,
                                                     'YFIELD': lat,
                                                     'ZFIELD': z_el,
                                                     'TARGET_CRS': 'EPSG:4326',
                                                     'OUTPUT': project_path + pro_dir + '/' + output4})
BathymetryPointsInsideTile = QgsVectorLayer(project_path + pro_dir + '/' + output4, 'BathymetryPointsInsideTile', "ogr")
BathymetryPointsInsideTile.setCrs(crs)
project.addMapLayer(BathymetryPointsInsideTile)

'''
***** Creation of Bathymetry Surface (WGS84) *****
'''

# *** Add river .shp
river_layer = QgsVectorLayer(river_path + river_file, 'River', "ogr")
river_layer.setCrs(crs)

## *** point style
pointStyle(BathymetryPointsInsideTile, 'ellipsoida')

## *** Multilevel B-Spline --> WGS84
output5 = 'Surface_' + mapJson_name[:-8] + '.sdat'
extent = BathymetryPointsInsideTile.extent()
xmin = extent.xMinimum()
xmax = extent.xMaximum()
ymin = extent.yMinimum()
ymax = extent.yMaximum()
xsize = int(abs(xmin - xmax) / 0.00009)  # 10m resolution in degree format
ysize = int(abs(ymin - ymax) / 0.00009)  # 10m resolution in degree format
call(['saga_cmd', 'grid_spline', '4', '-SHAPES', project_path + pro_dir + '/' + output4,
      '-FIELD', 'ellipsoida', '-TARGET_USER_SIZE', '0.00009',
      '-TARGET_USER_XMIN', f'{xmin}', '-TARGET_USER_XMAX', f'{xmax}',
      '-TARGET_USER_YMIN', f'{ymin}', '-TARGET_USER_YMAX', f'{ymax}',
      '-TARGET_USER_COLS', f'{xsize}', '-TARGET_USER_ROWS', f'{ysize}',
      '-LEVEL_MAX', '6', '-TARGET_OUT_GRID', project_path + pro_dir + '/' + output5])
surface = QgsRasterLayer(project_path + pro_dir + '/' + output5, output5[:-5])
if surface.isValid():
    surface.setCrs(crs)
    project.addMapLayer(surface)
else:
    print('Error: Failed to load surface layer')

# *** Clip raster by mask layer --> WGS84
output6 = 'SurfaceClip_' + mapJson_name[:-8] + '.tif'
processing.run("gdal:cliprasterbymasklayer", {
    'INPUT': project_path + pro_dir + '/' + output5,
    'MASK': river_path + river_file,
    'CROP_TO_CUTLINE': False,
    'KEEP_RESOLUTION': True,
    'OUTPUT': project_path + pro_dir + '/' + output6})
surfaceClip = QgsRasterLayer(project_path + pro_dir + '/' + output6, output6[:-4])
if surfaceClip.isValid():
    surfaceClip.setCrs(crs)
    rasterStyle(surfaceClip)
    project.addMapLayer(surfaceClip)
else:
    print('Error: Failed to load surfaceClip layer')

## *** Save the project
layer_id = BathymetryPointsInsideTile.id()
surface_id = surface.id()
surfaceClip_id = surfaceClip.id()
project_name = "Bathymetry_" + mapJson_name[:-8] + ".qgs"
project.writeEntry("WMSServiceCapabilities", "/", "True")
project.writeEntry("WMSServiceTitle", "/", "Bathymetry")
project.writeEntry("WMSContactOrganization", "/", "CIDCO")
project.writeEntry("WMSOnlineResource", "/", "www.cidco.ca")
project.writeEntry("WMSContactPerson", "/", "Mohsen Feizabadi")
project.writeEntry("WMSContactMail", "/", "mohsen.feizabadi@cidco.ca")
project.writeEntry("WMSContactOrganization", "/", "CIDCO")

project.writeEntry("WMSExtent", "/", [str(xmin), str(ymin), str(xmax), str(ymax)])
project.writeEntry("WMSEpsgList", "/", ["EPSG:4326", "EPSG:3857"])
project.writeEntry("WMSCrsList", "/", ["EPSG:4326", "EPSG:3857"])

project.writeEntry("WMTSLayers", "Project", True)
project.writeEntry("WMTSPngLayers", "Project", True)
project.writeEntry("WMTSJpegLayers", "Project", True)

project.writeEntry("WMTSLayers", "Layer", [layer_id] + [surfaceClip_id])
project.writeEntry("WMTSPngLayers", "Layer", [layer_id] + [surfaceClip_id])
project.writeEntry("WMTSJpegLayers", "Layer", [layer_id] + [surfaceClip_id])

project.writeEntry("WMTSGrids", "CRS", ["4326", "3857"])

project.writeEntry("WFSLayers", "/", [layer_id])
project.writeEntry("WFSTLayers", "Update", [layer_id])
project.writeEntry("WFSTLayers", "Insert", [layer_id])
project.writeEntry("WFSTLayers", "Delete", [layer_id])
for j in layer_id.split():
    project.writeEntry("WFSLayersPrecision", "/" + j, 5)

project.writeEntry("WCSLayers", "/", [surfaceClip_id])
project.write(project_path + pro_dir + '/' + project_name)

'''
***** Bathymetry Surface Reprojections *****
'''

## *** River reprojection
riverReproject = 'River_' + reproject_crs.authid()[-4:] + '.shp'
processing.run("qgis:reprojectlayer", {
    'INPUT': river_path + river_file,
    'TARGET_CRS': reproject_crs,
    'OUTPUT': project_path + pro_dir + '/' + riverReproject})

## *** Vector reprojection
vectorReproject = 'Job_' + mapJson_name[:-8] + '_' + reproject_crs.authid()[-4:] + '.shp'
processing.run("qgis:reprojectlayer", {
    'INPUT': project_path + pro_dir + '/' + output4,
    'TARGET_CRS': reproject_crs,
    'OUTPUT': project_path + pro_dir + '/' + vectorReproject})
reprojectedVector = QgsVectorLayer(project_path + pro_dir + '/' + vectorReproject, vectorReproject[:-4], "ogr")

## *** Add geometry attributes for new projection and save them for SDB and SNAP processing
vectorReproject_csv = 'Job_' + mapJson_name[:-8] + '_' + reproject_crs.authid()[-4:] + '.csv'
processing.run("qgis:exportaddgeometrycolumns", {
    'INPUT': project_path + pro_dir + '/' + vectorReproject,
    'CALC_METHOD': 0,
    'OUTPUT': project_path + pro_dir + '/' + vectorReproject_csv})
csvFile = pd.read_csv(project_path + pro_dir + '/' + vectorReproject_csv, sep=",", header=0)
xcoord = np.asarray(csvFile.xcoord).reshape(-1)
ycoord = np.asarray(csvFile.ycoord).reshape(-1)
zcoord = np.asarray(csvFile.zcoord).reshape(-1)
timestamp = np.asarray(csvFile.Timestamp).reshape(-1)
csvFile_sdb = zip(xcoord, ycoord, zcoord, timestamp)
with open(project_path + pro_dir + '/' + vectorReproject_csv[:-4] + '_sdb.csv', 'w') as f:
    writer = csv.writer(f, delimiter=',')
    writer.writerows(csvFile_sdb)
latitude = np.asarray(csvFile.Latitude).reshape(-1)
longitude = np.asarray(csvFile.Longitude).reshape(-1)
depth = np.asarray(csvFile.Ellipsoida).reshape(-1)
csvFile_snap = zip(latitude, longitude, depth)
with open(project_path + pro_dir + '/' + 'Job_' + mapJson_name[:-8] + '_snap.csv', 'w') as f:
    writer = csv.writer(f, delimiter=',')
    writer.writerows(csvFile_snap)

## *** Multilevel B-Spline --> EPSG: 3156, 3157
surfaceReproject = 'Surface_' + mapJson_name[:-8] + '_' + reproject_crs.authid()[-4:] + '.sdat'
extent_rep = reprojectedVector.extent()
xsize = int(abs(extent_rep.xMinimum() - extent_rep.xMaximum()) / 10)  # 10m resolution
ysize = int(abs(extent_rep.yMinimum() - extent_rep.yMaximum()) / 10)  # 10m resolution
call(['saga_cmd', 'grid_spline', '4', '-SHAPES', project_path + pro_dir + '/' + vectorReproject,
      '-FIELD', 'ellipsoida', '-TARGET_USER_SIZE', '10',
      '-TARGET_USER_XMIN', f'{extent_rep.xMinimum()}', '-TARGET_USER_XMAX', f'{extent_rep.xMaximum()}',
      '-TARGET_USER_YMIN', f'{extent_rep.yMinimum()}', '-TARGET_USER_YMAX', f'{extent_rep.yMaximum()}',
      '-TARGET_USER_COLS', f'{xsize}', '-TARGET_USER_ROWS', f'{ysize}',
      '-LEVEL_MAX', '6', '-TARGET_OUT_GRID', project_path + pro_dir + '/' + surfaceReproject])

## *** Clip raster by mask layer --> EPSG: 3156, 3157
clipSurfaceReproject = 'SurfaceClip_' + mapJson_name[:-8] + '_' + reproject_crs.authid()[-4:] + '.tif'
processing.run("gdal:cliprasterbymasklayer", {
    'INPUT': project_path + pro_dir + '/' + surfaceReproject,
    'MASK': project_path + pro_dir + '/' + riverReproject,
    'CROP_TO_CUTLINE': False,
    'KEEP_RESOLUTION': True,
    'OUTPUT': project_path + pro_dir + '/' + clipSurfaceReproject})

## *** Saving images as VRT .tif
vrt_path = os.path.join(project_path + pro_dir, 'VRT')
try:
    os.mkdir(vrt_path)
except:
    print('')
ds = gdal.Open(project_path + pro_dir + '/' + clipSurfaceReproject)
band = ds.GetRasterBand(1)
xsize = band.XSize
ysize = band.YSize
tile_size_x = 999
tile_size_y = 999
countX = 1
k = 1
for i in range(0, xsize, tile_size_x):
    countY = 1
    for j in range(0, ysize, tile_size_y):
        sizeX = countX * tile_size_x
        if sizeX > xsize and countX > 1:
            sizeX = (countX - 1) * tile_size_x
            imageXsize = xsize % sizeX
        elif sizeX > xsize and countX == 1:
            imageXsize = xsize
        else:
            imageXsize = tile_size_x
        sizeY = countY * tile_size_y
        if sizeY > ysize and countY > 1:
            sizeY = (countY - 1) * tile_size_y
            imageYsize = ysize % sizeY
        elif sizeY > ysize and countY == 1:
            imageYsize = ysize
        else:
            imageYsize = tile_size_y
        com_string = "gdal_translate -of GTIFF -srcwin " + str(i) + ", " + str(j) + ", " + str(imageXsize) + ", " + str(
                      imageYsize) + " " + str(project_path + pro_dir + '/' + clipSurfaceReproject) + " " + str(vrt_path) + '/tile_' + str(k) + ".tif"
        os.system(com_string)
        countY += 1
        k += 1
    countX += 1
tifFiles_name = os.listdir(vrt_path)
tifFiles_name = sorted(tifFiles_name, key=lambda x: int(x.split('_')[1].split('.')[0]))
tifFiles = {}
tifExtent = {}
tifPolygon = {}
k = 0
for tifs in tifFiles_name:
    tifFiles[tifs] = QgsRasterLayer(vrt_path + '/' + tifFiles_name[k], '')
    tifExtent[tifs] = tifFiles[tifs].extent()
    tifPolygon[tifs] = QgsVectorLayer("Polygon?crs=" + tifFiles[tifs].crs().authid(), "tile_" + str(k + 1) + "_poly", "memory")
    fields = QgsFields()
    fields.append(QgsField("ID", QVariant.Int))
    tifPolygon[tifs].dataProvider().addAttributes(fields)
    tifPolygon[tifs].updateFields()
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromRect(tifExtent[tifs]))
    feature.setAttributes([1])
    tifPolygon[tifs].dataProvider().addFeatures([feature])
    tifPolygon[tifs].updateExtents()
    project.addMapLayer(tifPolygon[tifs])
    A = processing.run("qgis:selectbylocation", {
                                                  'INPUT': BathymetryPointsInsideTile,
                                                  'PREDICATE': 0,
                                                  'INTERSECT': tifPolygon[tifs],
                                                  'METHOD': 0})
    selected_count = A['OUTPUT'].selectedFeatureCount()
    if selected_count < 1:
        os.remove(vrt_path + '/' + tifFiles_name[k])
    k += 1
