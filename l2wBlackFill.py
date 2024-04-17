"""
# Copyright 2023 © Centre Interdisciplinaire de développement en Cartographie des Océans (CIDCO), Tous droits réservés
@Mohsen_Feizabadi ---
"""

import rasterio
import os, glob
import numpy as np

def BlackFill(acolitePath):
    search_criteria = "*_rhow_*.tif"
    com_fps = os.path.join(acolitePath, search_criteria)
    png_fps = glob.glob(com_fps)
    full_path = []
    fname = {}
    image_list = []
    out_meta = {}
    statsDict = {}
    statsList = {}
    for i in range(len(png_fps)):
        full_path.append(os.path.realpath(png_fps[i]))
        path, fname[i] = os.path.split(full_path[i])
        src = rasterio.open(png_fps[i])
        array = src.read()
        image_list.append(src)
        out_meta[i] = image_list[i].meta.copy()
        stats = []
        for band in array:
            stats.append({
                'min': np.nanmin(band),
                'mean': np.nanmean(band),
                'median': np.nanmedian(band),
                'max': np.nanmax(band)})
        statsDict[i] = stats
        stats = []
        for band in array:
            stats.append([np.nanmin(band), np.nanmean(band), np.nanmedian(band), np.nanmax(band)])
        statsList[i] = stats
    return statsDict, statsList