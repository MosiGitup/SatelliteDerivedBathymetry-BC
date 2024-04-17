import logging, os, warnings, glob, subprocess, signal, sys
from tkinter import filedialog, Tk
import geojson
import pandas as pd
import _pickle as pickle
warnings.filterwarnings("ignore", message="Pandas requires version '2.7.3' or newer of 'numexpr'")


def print_hi(name):
    print(f'\033[1;32m{name}\033[0;0m', '\n')


if __name__ == '__main__':
    print_hi('CIDCO: CSB-BC')

logging.getLogger('qgis').setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=DeprecationWarning)
sdbProcess = ['Surface From Bathymetry Data', 'Sattelite-Derived Bathymetry (CIDCO)',
              'Sattelite-Derived Bathymetry (ESA-SNAP)', 'Integration of Both SDBs and regional DEM', 'All']
print('\033[1;34mSATELLITE DERIVED BATHYMETRY PROCESS: ''\033[0m')
for i in range(len(sdbProcess)):
    print(str(i+1), '- ' + sdbProcess[i])
print('')
processStep = input('\033[1;32mSelect one of the steps: ')
if processStep == '1':
    # from qgis_selectDB_Jobs import vrt_path, project_path, pro_dir, imageList, uuidList, filtered_vectorSDB, date1, date2, vectorSDB_date
    import qgis_selectDB_Jobs
elif processStep == '2':
    from python_acolite_SDB import tifConvertorForAcolite, msiAcoliteCalculation, mergeAcoliteTifOutputs, sdbCalculationFull
    root = Tk()
    vrt_path = filedialog.askdirectory(initialdir='/home/cidco/Documents/QGIS/projects/BC/SDB', title='Select VRT .tif files directory')
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
    mergeAcoliteTifOutputs(acoliteOutputDir)
    sdbCalculationFull(acoliteOutputDir, tifCRS, project_path, pro_dir, processStep, filtered_vectorSDB_projected)
elif processStep == '3':
    print('\033[1;33m*** CLOSE SNAP DESKTOP !!! ***''\033[0m', '\n')
    fields = None
    for line in os.popen("ps ax | grep " + "SNAP" + " | grep -v grep"):
        fields = line.split()
    if fields:
        pid = fields[0]
        os.kill(int(pid), signal.SIGKILL)
    root = Tk()
    project_path = filedialog.askdirectory(initialdir='/home/cidco/Documents/QGIS/projects/BC/SDB', title='Select project directory')
    root.update()
    root.destroy()
    _, pro_dir = os.path.split(project_path)
    serachCriteria = "*_sdb.csv"
    sdb_csv_path = glob.glob(project_path + '/' + serachCriteria)
    _, tileName = os.path.split(sdb_csv_path[0])
    tileName = tileName[4:10]
    # with open(project_path + '/variables.txt', 'rb') as handle:
    #     varDict = pickle.loads(handle.read())
    # imageListKey = list(varDict['filtered_vectorSDB'].keys())
    from readCSVfromAPI import sdbCSVpath
    imageDownloadTime_from, imageDownloadTime_to, _, vectorSDB_date, _ = sdbCSVpath(sdb_csv_path[0])
    print('\033[1;34mDate interval to download the images: ''\033[0m')
    print('\033[1;32mFROM: ' + imageDownloadTime_from + '\033[0m')
    print('\033[1;32mTO: ' + imageDownloadTime_to + '\033[0m')
    firstDate = imageDownloadTime_from
    lastDate = imageDownloadTime_to
    root = Tk()
    acolite_path = filedialog.askdirectory(initialdir='/media/cidco/blanc-sablon/Mosi Drive/Python3/Bathymetry/acolite_outputs', title='Select Acolite outputs directory')
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
    root = Tk()
    snapCSV_path = filedialog.askdirectory(initialdir='/home/cidco/Documents/QGIS/projects/BC/SDB', title='Select QGIS project directory')
    root.update()
    root.destroy()
    EmpBathymetry(snapCSV_path, s2dirName)
elif processStep == '4':
    from SNAP_DEM_SDBcombination import SnapDemSdb
    root = Tk()
    acolite_dir = filedialog.askdirectory(initialdir='/media/cidco/blanc-sablon/Mosi Drive/Python3/Bathymetry/acolite_outputs', title='Select Acolite Output directory')
    root.update()
    root.destroy()
    SnapDemSdb(acolite_dir)
else:
    from qgis_selectDB_Jobs import vrt_path, project_path, pro_dir
    from python_acolite_SDB import tifConvertorForAcolite, msiAcoliteCalculation, mergeAcoliteTifOutputs, sdbCalculationFull
    surfaceTXTpath, tifCRS = tifConvertorForAcolite(vrt_path, pro_dir)
    acoliteOutputDir, sat_image, acolitesFile, firstDate, lastDate = msiAcoliteCalculation(surfaceTXTpath, tifCRS, pro_dir)
    mergeAcoliteTifOutputs(acoliteOutputDir, acolitesFile)
    sdbCalculationFull(acoliteOutputDir, tifCRS, project_path, pro_dir, processStep)
    searchCriteria = "*.geojson"
    geoFile = []
    gJson = []
    for (dir_path, dir_names, file_names) in os.walk(acoliteOutputDir):
        geoFile.extend(file_names)
        gJson += glob.glob(dir_path + '/' + searchCriteria)
    collection = []
    for file in gJson:
        with open(file) as f:
            layer = geojson.load(f)
            collection.append(layer['features'][0])
    geo_collection = geojson.FeatureCollection(collection)
    geojsonFile = acoliteOutputDir + '/map.geojson'
    with open(geojsonFile, 'w') as f:
        geojson.dump(geo_collection, f)
    from snap_empSDB import downloadL2A, ReaSamSubS2, Deglint, LandMasking, EmpBathymetry
    print('\033[1;33m*** CLOSE SNAP DESKTOP !!! ***''\033[0m', '\n')
    S2image, download_path, polygon = downloadL2A(firstDate, lastDate, geojsonFile)
    s2dirName = ReaSamSubS2(S2image, download_path, polygon, acoliteOutputDir)
    Deglint(s2dirName)
    LandMasking(s2dirName)
    snapCSV_path = project_path + pro_dir
    EmpBathymetry(snapCSV_path, s2dirName)
    from SNAP_DEM_SDBcombination import SnapDemSdb
    SnapDemSdb(acoliteOutputDir)

print('\n', '\033[1;32mWELL DONE!!')