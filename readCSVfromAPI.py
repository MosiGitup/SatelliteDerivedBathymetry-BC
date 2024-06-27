"""
# Copyright 2023 © Centre Interdisciplinaire de développement en Cartographie des Océans (CIDCO), Tous droits réservés
@Mohsen_Feizabadi ---
"""

import pandas as pd
import os


def sdbCSVpath(csvPath):
    if "_sdb.csv" in csvPath:
        vectorSDB = pd.read_csv(csvPath, sep=",", header=None, names=['x', 'y', 'z', 't'])
    else:
        vectorSDB = pd.read_csv(csvPath, sep=",", header=None, names=['x', 'y', 'z_el', 'z_cd', 'id', 't'], low_memory=False)
        lon = vectorSDB.x[0]
        lat = vectorSDB.y[0]
        z_el = vectorSDB.z_el[0]
        z_cd = vectorSDB.z_cd[0]
        
        vectorSDB = vectorSDB.drop(vectorSDB.index[0])
    _, tileName = os.path.split(csvPath)
    tileName = tileName[:6]
    vectorSDBonlyDate = []
    for i in range(1, len(vectorSDB)):
        vectorSDBonlyDate.append(vectorSDB.t[i][:10])
    vectorSDBonlyDate = list(set(vectorSDBonlyDate))
    vectorSDB_date = []
    for i in range(len(vectorSDBonlyDate)):
        vectorSDB_date.append(vectorSDBonlyDate[i][0:4] + vectorSDBonlyDate[i][5:7] + vectorSDBonlyDate[i][8:])
    timestamp_first = vectorSDB.t[1][:19]
    imageDownloadTime_from = timestamp_first[:10]
    timestamp_last = vectorSDB.t[len(vectorSDB) - 1][:19]
    imageDownloadTime_to = timestamp_last[:10]
    if "_sdb.csv" in csvPath:
        return imageDownloadTime_from, imageDownloadTime_to, vectorSDB, vectorSDB_date, tileName
    else:
        return imageDownloadTime_from, imageDownloadTime_to, vectorSDB, vectorSDB_date, tileName, lon, lat, z_el, z_cd
