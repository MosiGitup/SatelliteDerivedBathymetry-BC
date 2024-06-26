"""
# Copyright 2023 © Centre Interdisciplinaire de développement en Cartographie des Océans (CIDCO), Tous droits réservés
@Mohsen_Feizabadi 
"""

import logging, os, warnings, glob, subprocess, signal, sys
from tkinter import filedialog, Tk
import geojson
import pandas as pd
import _pickle as pickle
warnings.filterwarnings("ignore", message="Pandas requires version '2.7.3' or newer of 'numexpr'")

vrt_dir = sys.argv[14]
project_dir = sys.argv[15]
acolite_dir = sys.argv[16]
snap_output_dir = sys.argv[22]

def print_hi(name):
    print(f'\033[1;32m{name}\033[0;0m', '\n')


if __name__ == '__main__':
    print_hi('CIDCO: SATELLITE DERIVED BATHYMETRY - BC')

logging.getLogger('qgis').setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=DeprecationWarning)
sdbProcess = ['Surface From Bathymetry Data', 'Sattelite-Derived Bathymetry (CIDCO)',
              'Sattelite-Derived Bathymetry (ESA-SNAP)', 'Integration of Both SDBs and regional DEM']
print('\033[1;34mSATELLITE DERIVED BATHYMETRY PROCESS: ''\033[0m')
for i in range(len(sdbProcess)):
    print(str(i+1), '- ' + sdbProcess[i])
print('')
processStep = input('\033[1;32mSelect one of the steps: ')
if processStep == '1':
    print('')
    print_hi('The bathymetry points are received with "ApiCsbBathy" in QGIS application. After time checking of these points with Sentinel-2 images, \n'
             'bathymetry surface ("Multilevel B-Spline" method) will be created. The output surface (.tif) will be prepared for the next step. \n')
    import qgis_selectDB_Jobs
elif processStep == '2':
    print('')
    print_hi('The surfaces (.tif) convert to "Acolite" atmospheric correction program. After correction of Sentinel-2 (MSIL1C) images, the new "*rhow.tif" files \n'
             '(the surface level reflectance for water pixels) are applied in the "Satellite Derived Bathymetry" program. \n')
    from python_acolite_SDB import tifConvertorForAcolite, msiAcoliteCalculation, mergeAcoliteTifOutputs, sdbCalculationFull
    root = Tk()
    vrt_path = filedialog.askdirectory(initialdir=vrt_dir, title='Select VRT .tif files directory')
    root.update()
    root.destroy()
    project_path, _ = os.path.split(vrt_path)
    _, pro_dir = os.path.split(project_path)
    surfaceTXTpath, tifCRS = tifConvertorForAcolite(vrt_path, pro_dir)
    serachCriteria = "*_sdb.csv"
    sdb_csv_path = glob.glob(project_path + '/' + serachCriteria)
    _, tileName = os.path.split(sdb_csv_path[0])
    with open(project_path + '/variables.txt', 'rb') as handle:
        varDict = pickle.loads(handle.read())
    Date = (varDict['date1'], varDict['date2'])
    acoliteOutputDir, acoliteImagedir, acolitesFile, filtered_vectorSDB_projected = msiAcoliteCalculation(surfaceTXTpath, tifCRS, pro_dir, sdb_csv_path, tileName, varDict['uuidList'], varDict['imageList'], Date, varDict['vectorSDB_date'], varDict['filtered_vectorSDB'])
    acol_crs = mergeAcoliteTifOutputs(acoliteOutputDir, tifCRS)
    sdbCalculationFull(acoliteOutputDir, project_path, pro_dir, processStep, filtered_vectorSDB_projected, acol_crs)
elif processStep == '3':
    print('')
    print_hi('Sentinel-2 (MSIL2A) image will be downloaded (the same date as the previous step). Based on the selected region, the "Sampling", "Subset", \n'
             '"Sun-Deglint", "Land-Mask" and finally "Emperical Bathymetry" will be done in ESA-SNAP software. \n')
    print('\033[1;33m*** CLOSE SNAP DESKTOP !!! ***''\033[0m', '\n')
    fields = None
    for line in os.popen("ps ax | grep " + "SNAP" + " | grep -v grep"):
        fields = line.split()
    if fields:
        pid = fields[0]
        os.kill(int(pid), signal.SIGKILL)
    root = Tk()
    project_path = filedialog.askdirectory(initialdir=project_dir, title='Select project directory')
    root.update()
    root.destroy()
    _, pro_dir = os.path.split(project_path)
    serachCriteria = "*_sdb.csv"
    sdb_csv_path = glob.glob(project_path + '/' + serachCriteria)
    _, tileName = os.path.split(sdb_csv_path[0])
    tileName = tileName[4:10]
    from readCSVfromAPI import sdbCSVpath
    imageDownloadTime_from, imageDownloadTime_to, _, vectorSDB_date, _ = sdbCSVpath(sdb_csv_path[0])
    print('\033[1;34mDate interval to download the images: ''\033[0m')
    print('\033[1;32mFROM: ' + imageDownloadTime_from + '\033[0m')
    print('\033[1;32mTO: ' + imageDownloadTime_to + '\033[0m')
    firstDate = imageDownloadTime_from
    lastDate = imageDownloadTime_to
    root = Tk()
    acolite_path = filedialog.askdirectory(initialdir=acolite_dir, title='Select SDB outputs (from 2nd step) directory')
    root.update()
    root.destroy()
    searchCriteria = "*.geojson"
    geoFile = []
    gJson = []
    for (dir_path, dir_names, file_names) in os.walk(acolite_path):
        geoFile.extend(file_names)
        gJson += glob.glob(dir_path + '/' + searchCriteria)
    collection = []
    for file in gJson:
        with open(file) as f:
            layer = geojson.load(f)
            collection.append(layer['features'][0])
    geo_collection = geojson.FeatureCollection(collection)
    geojsonFile = acolite_path + '/map.geojson'
    with open(geojsonFile, 'w') as f:
        geojson.dump(geo_collection, f)
    from snap_empSDB import downloadL2A, ReaSamSubS2, Deglint, LandMasking, EmpBathymetry
    S2image, download_path, polygon = downloadL2A(firstDate, lastDate, geojsonFile, vectorSDB_date, tileName)
    s2dirName = ReaSamSubS2(S2image, download_path, polygon, acolite_path)
    Deglint(s2dirName)
    LandMasking(s2dirName)
    EmpBathymetry(project_path, s2dirName)
elif processStep == '4':
    print('')
    print_hi('Both satellite bathymetry outputs (CIDCO and ESA-SNAP versions) are intergegrated with the selected region DEM (30m Copernicus Global DEM). \n')
    from SNAP_DEM_SDBcombination import SnapDemSdb
    root = Tk()
    acolite_dir = filedialog.askdirectory(initialdir=snap_output_dir, title='Select SDB outputs (from 3rd step) directory')
    root.update()
    root.destroy()
    SnapDemSdb(acolite_dir)
print('\n', '\033[1;32mWELL DONE!!')