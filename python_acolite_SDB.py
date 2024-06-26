"""
# Copyright 2023 © Centre Interdisciplinaire de développement en Cartographie des Océans (CIDCO), Tous droits réservés
@Mohsen_Feizabadi ---
"""

from tkinter import filedialog, Tk
import glob
import rasterio
import numpy as np
import csv, os, sys, fnmatch
import pandas as pd
from rasterio.merge import merge
from rasterio.warp import calculate_default_transform, reproject, Resampling
import shutil

initialdir_txt = sys.argv[9]
acolite_dir = sys.argv[10]

def tifConvertorForAcolite(vrtPath, pro_dir):
    searchCriteria = "*.tif"
    tifs = glob.glob(vrtPath + '/' + searchCriteria)
    fname = {}
    raster = {}
    raster_array = {}
    raster_txtFile = {}
    root = Tk()
    txtOutputPath = filedialog.askdirectory(parent=root, initialdir=initialdir_txt, title='Directory to save surfaces as .txt')
    root.update()
    root.destroy()
    txtOutputDir = os.path.join(txtOutputPath, pro_dir)
    try:
        os.mkdir(txtOutputDir)
    except:
        print('')
    for i in range(len(tifs)):
        path, fname[i] = os.path.split(tifs[i])
        src = rasterio.open(tifs[i])
        raster[i] = src.read()
        raster_array[i] = np.asarray(raster[i]).reshape(-1)
        height = src.shape[0]
        width = src.shape[1]
        cols, rows = np.meshgrid(np.arange(width), np.arange(height))
        xs, ys = rasterio.transform.xy(src.transform, rows, cols)
        lons = np.array(xs)
        lats = np.array(ys)
        print('\033[1;34m', str(i + 1) + ' : surface shape ' + str(lons.shape), '\033[0m')
        lons_array = np.asarray(lons).reshape(-1)
        lats_array = np.asarray(lats).reshape(-1)
        raster_txtFile[i] = zip(lons_array, lats_array, raster_array[i])
        txtFilepath = txtOutputDir + '/' + str(i + 1) + '.txt'
        with open(txtFilepath, 'w') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerows(raster_txtFile[i])
    tifCRS = src.crs
    return txtOutputDir, tifCRS


def msiAcoliteCalculation(txtPath, crs, pro_dir, sdb_csv_path, tileName, uuidList, imageList, Date, vectorSDB_date, filtered_vectorSDB):
    vectorSDB = pd.read_csv(sdb_csv_path[0], sep=",", header=None, names=['x', 'y', 'z', 't'])
    filtered_vectorSDB_projected = {}
    filtered_vectorSDB_keys = list(filtered_vectorSDB.keys())
    for k in range(len(filtered_vectorSDB)):
        numRow = filtered_vectorSDB[filtered_vectorSDB_keys[k]].index.tolist()
        filtered_vectorSDB_projected[filtered_vectorSDB_keys[k]] = vectorSDB.iloc[numRow[0]-1:numRow[-1]]
    import msi_acolite_rhow_modify
    searchCriteria = "*.txt"
    input_dir = glob.glob(txtPath + '/' + searchCriteria)
    fname = {}
    TideHeight = 0
    EPSG = crs.data['init'][5:]
    root = Tk()
    acoliteOutputPath = filedialog.askdirectory(initialdir=acolite_dir, title='Acolite Output Directory')
    root.update()
    root.destroy()
    acoliteOutputDir = os.path.join(acoliteOutputPath, pro_dir)
    L1C_path = acoliteOutputPath
    uuidKeys = list(uuidList.keys())
    num = 0
    for Img in range(len(uuidKeys)):
        for Dir in range(len(uuidList[uuidKeys[Img]])):
            print('\033[1;32mImage: ' + filtered_vectorSDB_keys[num] + '\033[0m')
            acoliteImagedir = acoliteOutputDir + '/' + filtered_vectorSDB_keys[num]
            acolitesFile = acoliteImagedir + '/Acolite'
            try:
                os.mkdir(acoliteOutputDir)
                os.mkdir(acoliteImagedir)
                os.mkdir(acolitesFile)
            except:
                print('')
            for i in range(len(input_dir)):
                path, fname[i] = os.path.split(input_dir[i])
                Surface = pd.read_csv(input_dir[i], sep=",", header=None, names=['x', 'y', 'z'])
                TmpPath = acolitesFile + '/' + fname[i][:-4]
                try:
                    os.mkdir(TmpPath)
                except:
                    print('')
                print("\033[1;34m ***** SURFACE " + str(i + 1) + " FROM " + str(len(input_dir)) + " *****"'\033[0m')
                if i == 0:
                    txtSurface = None
                    DownloadResult = None
                    DownloadResult, txtSurface = msi_acolite_rhow_modify.msi_acolite(Surface, TideHeight, EPSG, Date, TmpPath, L1C_path, vectorSDB_date, tileName, vectorSDB
                                                                                     ).get_rhow(uuidList[uuidKeys[Img]][Dir], imageList[uuidKeys[Img]][Dir], crs, filtered_vectorSDB_projected[filtered_vectorSDB_keys[num]], txtSurface, DownloadResult)
                else:
                    _, _ = msi_acolite_rhow_modify.msi_acolite(Surface, TideHeight, EPSG, Date, TmpPath, L1C_path, vectorSDB_date, tileName, vectorSDB
                                                               ).get_rhow(uuidList[uuidKeys[Img]][Dir], imageList[uuidKeys[Img]][Dir], crs, filtered_vectorSDB_projected[filtered_vectorSDB_keys[num]], txtSurface, DownloadResult)
            num += 1
            dir_num = os.listdir(acolitesFile)
            if len(dir_num) == 0:
                shutil.rmtree(acoliteImagedir, ignore_errors=True)
    return acoliteOutputDir, acoliteImagedir, acolitesFile, filtered_vectorSDB_projected


def mergeAcoliteTifOutputs(acolitePath, tifCRS):
    dirAcolite = os.listdir(acolitePath)
    for acoliteDir in dirAcolite:
        acolite_folder = list(os.walk(acolitePath + '/' + acoliteDir))

        def extract_numeric_part(folder_name):
            try:
                return int(folder_name.lstrip("folder"))
            except ValueError:
                return float('inf')

        acolite_folder = sorted(acolite_folder, key=lambda x: extract_numeric_part(os.path.basename(x[0])))
        out_meta = {}
        sort_meta = []
        search_criteria = ".tif"
        tif_files = {}
        k = 0
        for i in range(len(acolite_folder)-2):
            tif_files[k] = []
            for j in range(len(acolite_folder[i][2])):
                if search_criteria in acolite_folder[i][2][j]:
                    if tif_files[k]:
                        tif_files[k] += [acolite_folder[i][2][j]]
                    else:
                        tif_files[k] = [acolite_folder[i][2][j]]
            tif_files[k].sort()
            k += 1
        for j in range(len(tif_files[0])):
            image_list = []
            sort_meta = []
            for i in range(len(acolite_folder)-2):
                tif_path = acolite_folder[i][0] + '/' + tif_files[i][j]
                src = rasterio.open(tif_path)
                image_list.append(src)
                out_meta[i] = image_list[i - 1].meta.copy()
                sort_meta.append(out_meta[i])
                mosaic, out_trans = merge(image_list)
                sort_meta[i - 1].update({"height": mosaic.shape[1],
                                         "width": mosaic.shape[2],
                                         "transform": out_trans,
                                         })
                with rasterio.open(acolitePath + '/' + acoliteDir + '/' + tif_files[i][j][:-4] + '_Merge.tif', "w",
                                   **sort_meta[i - 1]) as dest:
                    dest.write(mosaic)

    search_criteria = "*.tif"
    project = tifCRS
    for acoliteDir in dirAcolite:
        comp_files = os.path.join(acolitePath + '/' + acoliteDir, search_criteria)
        merge_folder = glob.glob(comp_files)
        image_list = []
        out_meta = {}
        for i in range(len(merge_folder)):
            full_path = os.path.realpath(merge_folder[i])
            _, filename = os.path.split(full_path)
            src = rasterio.open(merge_folder[i])
            image_list.append(src)
            out_meta[i] = image_list[i].meta.copy()
            transform, width, height = calculate_default_transform(image_list[i].crs, project, image_list[i].width, image_list[i].height, *image_list[i].bounds)
            kwargs = image_list[i].meta.copy()
            kwargs.update({
                'crs': project,
                'transform': transform,
                'width': width,
                'height': height
            })
            with rasterio.open(acolitePath + '/' + acoliteDir + '/' + filename, "w", **kwargs) as dst:
                for t in range(1, image_list[i].count + 1):
                    reproject(
                        source=rasterio.band(image_list[i], t),
                        destination=rasterio.band(dst, t),
                        image_transform=image_list[i].transform,
                        image_crs=image_list[i].crs,
                        dst_transform=transform,
                        dst_crs=project,
                        resampling=Resampling.nearest)
    return project


def sdbCalculationFull(acoliteOutputDir, project_path, pro_dir, processStep, filtered_vectorSDB_projected, acol_crs):
    from SatelliteDerivedBathymetry import SatelliteDerivedBathymetry_all
    dirAcolite = os.listdir(acoliteOutputDir)
    for acoliteDir in dirAcolite:
        print('\033[1;32mSDB processing for image: ' + acoliteDir + '\033[0m')
        acoliteaPath = acoliteOutputDir + '/' + acoliteDir
        if processStep == '2':
            qgisPath = project_path + '/'
        else:
            qgisPath = project_path + pro_dir + '/'
        repeat = 'y'
        while repeat == 'y':

            # *** Band Ratio
            select_process = '1'
            tif_path = None
            output_dir = None
            vector_csv_path = None
            raster, save_dir, output_dir_path, ratio_bands, out_meta, filepath_how, result_dir, fname, lons_array, lats_array, tif_path, output_dir = SatelliteDerivedBathymetry_all.how_tif_inputs(acoliteaPath, select_process, tif_path, output_dir, acol_crs)
            filepath_vec, vector_csv_path = SatelliteDerivedBathymetry_all.intersectPointPixel(filepath_how, select_process, vector_csv_path, output_dir_path, save_dir, qgisPath, filtered_vectorSDB_projected[acoliteDir])
            control_points_extract, filepath_ras, new_pixel_extract = SatelliteDerivedBathymetry_all.BR_PointrasterCoordinates(filepath_how, filepath_vec, save_dir, fname)
            X, rp_pixel, cp_point, rp_point = SatelliteDerivedBathymetry_all.BR_linearRegression(control_points_extract, filepath_ras, result_dir, fname, new_pixel_extract)
            SDB = SatelliteDerivedBathymetry_all.BR_SDB(X, ratio_bands, out_meta, result_dir, fname, acol_crs)
            filepath_excel = result_dir + '/band_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '_linear.csv'
            pd.DataFrame(np.stack((cp_point, rp_point, rp_pixel), axis=1)).to_csv(filepath_excel, sep=",", header=False, index=True)
            SDB_array = np.asarray(SDB).reshape(-1)
            SDB_txtFile = zip(lons_array, lats_array, SDB_array)
            SDB_filepath = result_dir + '/SDB_BandRatio_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '.csv'
            print('\033[1;34m', 'SDB .csv file: ', result_dir + '/SDB_BandRatio_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '.csv', '\033[0m')
            with open(SDB_filepath, 'w') as f:
                writer = csv.writer(f, delimiter=',')
                writer.writerows(SDB_txtFile)

            # *** Log-Linear
            select_process = '2'
            raster, save_dir, output_dir_path, out_meta, filepath_how, result_dir, fname, lons_array, lats_array = SatelliteDerivedBathymetry_all.how_tif_inputs(acoliteaPath, select_process, tif_path, output_dir, acol_crs)
            filepath_vec, _ = SatelliteDerivedBathymetry_all.intersectPointPixel(filepath_how, select_process, vector_csv_path, output_dir_path, save_dir, qgisPath, filtered_vectorSDB_projected[acoliteDir])
            control_points_extract, filepath_ras, new_pixel_extract = SatelliteDerivedBathymetry_all.LL_PointrasterCoordinates(filepath_how, filepath_vec, save_dir, fname)
            X, rp_pixel, cp_point, min_reflect_rhow, rp_point = SatelliteDerivedBathymetry_all.LL_linearRegression(control_points_extract, filepath_ras, result_dir, fname, new_pixel_extract)
            SDB = SatelliteDerivedBathymetry_all.LL_SDB(X, raster, min_reflect_rhow, out_meta, result_dir, fname, acol_crs)
            filepath_excel = result_dir + '/band_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '_multiLinear.csv'
            pd.DataFrame(np.stack((cp_point, rp_point), axis=1)).to_csv(filepath_excel, sep=",", header=False, index=True)
            SDB_array = np.asarray(SDB).reshape(-1)
            SDB_txtFile = zip(lons_array, lats_array, SDB_array)
            SDB_filepath = result_dir + '/SDB_LogLinear_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '.csv'
            print('\033[1;34m', 'SDB .csv file: ', result_dir + '/SDB_LogLinear_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '.csv', '\033[0m')
            with open(SDB_filepath, 'w') as f:
                writer = csv.writer(f, delimiter=',')
                writer.writerows(SDB_txtFile)
            print('')
            repeat = input('\033[1;32mDo you want to select another combination (y or n)? ''\033[0m')
    return
