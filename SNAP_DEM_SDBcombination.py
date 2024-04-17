"""
# Copyright 2023 © Centre Interdisciplinaire de développement en Cartographie des Océans (CIDCO), Tous droits réservés
@Mohsen_Feizabadi ---
"""

import rasterio
import os
from tkinter import filedialog, Tk
import numpy as np


def SnapDemSdb(acolite_dir):
    acolite_folder = list(os.walk(acolite_dir))
    search_criteria1 = "SNAP"
    search_criteria2 = ".tif"
    search_criteria3 = "SDB_"
    search_criteria4 = "LandMask"
    sdb_files = {}
    sdb_folders = {}
    snap_files = {}
    snap_folders = {}
    k = 0
    t = 0
    for i in range(len(acolite_folder)):
        sdb_files[k] = []
        sdb_folders[k] = []
        snap_files[t] = []
        snap_folders[t] = []
        for j in range(len(acolite_folder[i][2])):
            if search_criteria3 in acolite_folder[i][2][j] and search_criteria2 in acolite_folder[i][2][j]:
                if sdb_files[k]:
                    sdb_files[k] += [acolite_folder[i][2][j]]
                else:
                    sdb_files[k] = [acolite_folder[i][2][j]]
                    sdb_folders[k] = acolite_folder[i][0]
            sdb_files[k].sort()
            if search_criteria4 in acolite_folder[i][2][j]:
                mask_file = acolite_folder[i][2][j]
                mask_folder = acolite_folder[i][0]
            if search_criteria1 in acolite_folder[i][2][j] and search_criteria2 in acolite_folder[i][2][j]:
                if snap_files[t]:
                    snap_files[t] += [acolite_folder[i][2][j]]
                else:
                    snap_files[t] = [acolite_folder[i][2][j]]
                    snap_folders[t] = acolite_folder[i][0]
            snap_files[t].sort()
        if sdb_files[k]:
            k += 1
        if snap_files[t]:
            t += 1
        else:
            del snap_files[t]
            del snap_folders[t]
    raster = {}
    empBathy = {}
    SNAP = {}
    src_mask = rasterio.open(mask_folder + '/' + mask_file)
    LandMask = src_mask.read()
    for i in range(len(snap_files[0])):
        src = rasterio.open(snap_folders[0] + '/' + snap_files[0][i])
        raster[snap_files[0][i][-8:-4]] = src.read()
        empBathy[snap_files[0][i][-8:-4]] = np.where(raster[snap_files[0][i][-8:-4]] == 0, np.nan, raster[snap_files[0][i][-8:-4]])
        empBathy[snap_files[0][i][-8:-4]] = np.where((raster[snap_files[0][i][-8:-4]][0]) < -2000, np.nan, empBathy[snap_files[0][i][-8:-4]])
        SNAP[snap_files[0][i][-8:-4]] = np.where(LandMask[1] == 1, empBathy[snap_files[0][i][-8:-4]][0], np.nan)
        out_meta = src.meta.copy()
    SNAP_keys = list(SNAP.keys())
    DEM = raster[snap_files[0][0][-8:-4]][1]
    h_raster = raster[snap_files[0][0][-8:-4]][0].shape[0]
    w_raster = raster[snap_files[0][0][-8:-4]][0].shape[1]
    cols_raster, rows_raster = np.meshgrid(np.arange(w_raster), np.arange(h_raster))
    xs_raster, ys_raster = rasterio.transform.xy(src.transform, rows_raster, cols_raster)
    lon_raster = np.array(xs_raster)
    lat_raster = np.array(ys_raster)
    SDB = {}
    for i in range(len(sdb_files)):
        for j in range(2):
            src_sdb = rasterio.open(sdb_folders[i] + '/' + sdb_files[i][j])
            SDB[sdb_files[i][j][4:-4]] = src_sdb.read()
        out_meta_sdb = src_sdb.meta.copy()
    SDB_keys = list(SDB.keys())
    h_sdb = SDB[sdb_files[0][0][4:-4]][0].shape[0]
    w_sdb = SDB[sdb_files[0][0][4:-4]][0].shape[1]
    cols_sdb, rows_sdb = np.meshgrid(np.arange(w_sdb), np.arange(h_sdb))
    xs_sdb, ys_sdb = rasterio.transform.xy(src_sdb.transform, rows_sdb, cols_sdb)
    lon_sdb = np.array(xs_sdb)
    lat_sdb = np.array(ys_sdb)
    index = np.where((lon_sdb[0, 0] == lon_raster) & (lat_sdb[0, 0] == lat_raster))
    SNAP_DEM = {}
    v = 0
    for j in range(len(SNAP)):
        for q in range(len(SNAP) * 2):
            if q < 2 * v:
                continue
            SNAP_DEM[q] = np.nan_to_num(DEM) + np.nan_to_num(SNAP[SNAP_keys[j]])
            if q == 2 * j + 1:
                break
        v += 1
    SNAP_DEM_SDB = {}
    for k in range(len(SNAP_DEM)):
        SNAP_DEM_SDB[SDB_keys[k]] = SNAP_DEM[k]
        for i in range(h_sdb):
            for j in range(w_sdb):
                if not np.isnan(SDB[SDB_keys[k]][0][i][j]):
                    SNAP_DEM_SDB[SDB_keys[k]][index[0] + i, index[1] + j] = SDB[SDB_keys[k]][0][i][j]
    p = 0
    SnapDemSdb_path, _ = os.path.split(sdb_folders[0])
    for i in range(len(SNAP)):
        for j in range(2):
            filepath_bandRatio = SnapDemSdb_path + '/SNAP_' + snap_files[0][i][-8:-4] + '_DEM_SDB_' + sdb_files[i][j][4:-4] + '.tif'
            new_meta = out_meta
            new_meta.update(count=1)
            with rasterio.open(filepath_bandRatio, "w", **new_meta) as dest:
                dest.write(SNAP_DEM_SDB[SDB_keys[p]], 1)
                p += 1
