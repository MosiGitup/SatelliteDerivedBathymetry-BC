"""
# Copyright 2023 © Centre Interdisciplinaire de développement en Cartographie des Océans (CIDCO), Tous droits réservés
@Mohsen_Feizabadi ---
"""

snappy_dir = sys.argv[17]
username_copernicus = sys.argv[18]
password_copernicus = sys.argv[19]
download_dir = sys.argv[20]
snap_bin_dir = sys.argv[21]

import sys
sys.path.append(snappy_dir)
import snappy
from datetime import datetime, timedelta, date
import os, glob, subprocess, requests, json
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
from tkinter import filedialog, Tk
import zipfile
from zipfile import ZipFile
from shapely.geometry import Polygon
import numpy as np
import pandas as pd

def downloadL2A(date1, date2, geoFile, vectorSDB_date, tileName):
    gjsonFile = read_geojson(geoFile)
    west = []
    south = []
    east = []
    north = []
    for i in range(len(gjsonFile['features'])):
        west.append(gjsonFile['features'][i].bbox[0])
        south.append(gjsonFile['features'][i].bbox[1])
        east.append(gjsonFile['features'][i].bbox[2])
        north.append(gjsonFile['features'][i].bbox[3])
    left = min(west) - 0.02
    right = max(east) + 0.02
    up = max(north) + 0.02
    down = min(south) - 0.02
    geoPoly = Polygon([(left, down), (right, down), (right, up), (left, up)])
    footprint = geoPoly.wkt
    productname = 'SENTINEL-2'
    cloudCover = '99.00'
    productType = 'S2MSI2A'

    def get_access_token(username: str, password: str) -> str:
        data = {
            "client_id": "cdse-public",
            "username": username,
            "password": password,
            "grant_type": "password",
        }
        try:
            r = requests.post(
                "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
                data=data,
            )
            r.raise_for_status()
        except Exception as e:
            raise e
        return r.json()["access_token"]
    access_token = get_access_token(username_copernicus, password_copernicus)
    Fjson = requests.get(f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq '{productname}' and\
                          Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value lt {cloudCover}) and\
                          Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq '{productType}') and\
                          OData.CSC.Intersects(area=geography'SRID=4326;{footprint}') and\
                          ContentDate/Start gt {date1}T00:00:00.000Z and ContentDate/Start lt {date2}T00:00:00.000Z&$top=1000").json()
    products_df = pd.DataFrame.from_dict(Fjson['value'])
    if len(products_df) == 0:
        raise ValueError("No product found for the given parameters")
    imgs = []
    img_ind = []
    ind = []
    print('\033[1;34mAvailable L2A images in determined time interval''\033[0m', '\n')
    for im in range(len(products_df)):
        imgs.append(products_df.Name[im][:-5])
        img_ind.append(products_df.Id[im])
        ind.append(im)
    vectorSDB_date.sort()
    for i in range(len(imgs)):
        for j in range(len(vectorSDB_date)):
            if vectorSDB_date[j] in imgs[i] and tileName in imgs[i]:
                print('\033[1;34m', '[' + str(i) + '] ---> ', imgs[i], '\033[0m')
    select_image = input('\033[1;32mSelect your interest image number: ''\033[0m')
    root = Tk()
    download_path = filedialog.askdirectory(initialdir=download_dir, title='Select Image Download directory')
    root.update()
    root.destroy()
    url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({img_ind[int(select_image)]})/$value"
    headers = {"Authorization": f"Bearer {access_token}"}
    session = requests.Session()
    session.headers.update(headers)
    response = session.get(url, headers=headers, stream=True)
    image_name = imgs[int(select_image)]
    downloaded_image = download_path + '/' + image_name + ".zip"
    if not os.path.isfile(downloaded_image):
        print('\033[1;32mDownloading ... ''\033[0m')
        with open(downloaded_image, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
    return imgs[int(select_image)], download_path, geoPoly


def ReaSamSubS2(s2image, S2path, poly, acolite_path):
    S2ZipFile = S2path + '/' + s2image + '.zip'
    s2_read = snappy.ProductIO.readProduct(S2ZipFile)
    with ZipFile(S2ZipFile, 'r') as s2file:
        s2file = s2file.read(s2_read.getName() + '.SAFE/manifest.safe')
        mtd_txt = s2file.decode()
        coord_index_1 = mtd_txt.find("<gml:coordinates>")
        coord_index_2 = mtd_txt.find("</gml:coordinates>")
        coord = mtd_txt[coord_index_1 + 17: coord_index_2]
        coord_image = coord.split()
    image_coord = np.zeros(shape=(int(len(coord_image)/2), 2))
    for i in range(len(image_coord)):
        image_coord[i][1] = float(coord_image[2*i])
        image_coord[i][0] = float(coord_image[2*i+1])
    minLon_img = min(image_coord[:, 0])
    maxLon_img = max(image_coord[:, 0])
    minLat_img = min(image_coord[:, 1])
    maxLat_img = max(image_coord[:, 1])
    PolyB = list(poly.bounds)
    if PolyB[0] < minLon_img:
        PolyB[0] = minLon_img
    elif PolyB[1] < minLat_img:
        PolyB[1] = minLat_img
    elif PolyB[2] > maxLon_img:
        PolyB[2] = maxLon_img
    elif PolyB[3] > maxLat_img:
        PolyB[3] = maxLat_img
    poly = Polygon([(PolyB[0], PolyB[1]), (PolyB[2], PolyB[1]), (PolyB[2], PolyB[3]), (PolyB[0], PolyB[3])])
    snapDir = acolite_path + '/SNAP'
    s2dirName = snapDir + '/' + s2image[:26]
    try:
        os.mkdir(snapDir)
        os.mkdir(s2dirName)
    except:
        print('')
    parameters = snappy.HashMap()
    parameters.put('referenceBand', 'B2')
    resample = snappy.GPF.createProduct("Resample", parameters, s2_read)
    geom = poly.wkt
    parameters = snappy.HashMap()
    parameters.put('copyMetadata', True)
    parameters.put('geoRegion', geom)
    subset = snappy.GPF.createProduct("Subset", parameters, resample)
    outputPath_name = s2dirName + '/' + s2_read.getName() + '_Res_Sub'
    snappy.ProductIO.writeProduct(subset, outputPath_name, 'BEAM-DIMAP')
    return s2dirName


def Deglint(s2dirName):
    print('')
    print('\033[1;34mCreate vector layer for \"Sun Glint Area\". The name of this layer must be \"polygon\".''\033[0m', '\n')
    print('\033[1;33mDO NOT FORGET TO DELETE \"tie-points\" LAYERS !!!''\033[0m', '\n')
    print('\033[1;34mAfter saving product, close SNAP and wait ...''\033[0m', '\n')
    subprocess.call(["sh", snap_bin_dir])
    subset_merge = os.path.join(s2dirName, '*_Res_Sub.dim')
    subsetPath = glob.glob(subset_merge)
    resample_subset = snappy.ProductIO.readProduct(subsetPath[0])
    parameters = snappy.HashMap()
    parameters.put('referenceBand', 'B8')
    parameters.put('sourceBands', 'B1,B2,B3,B4')
    parameters.put('sunGlintVector', 'polygon')
    dglint = snappy.GPF.createProduct("DeglintOp", parameters, resample_subset)
    deglintName = s2dirName + '/' + resample_subset.getName() + '_deglint'
    snappy.ProductIO.writeProduct(dglint, deglintName, 'BEAM-DIMAP')
    return


def LandMasking(s2dirName):
    deglint_merge = os.path.join(s2dirName, '*_Res_Sub_deglint.dim')
    deglintPath = glob.glob(deglint_merge)
    deglint = snappy.ProductIO.readProduct(deglintPath[0])
    parameters = snappy.HashMap()
    parameters.put('referenceBands', 'B8')
    parameters.put('sourceBands', 'B1,B2,B3,B4')
    parameters.put('thresholdString', '0.05')
    mask = snappy.GPF.createProduct("LandCloudWhiteCapMaskOp", parameters, deglint)
    maskName = s2dirName + '/' + deglint.getName() + '_mask'
    maskName_tif = s2dirName + '/' + 'LandMask_' + deglint.getName()[11:19]
    snappy.ProductIO.writeProduct(mask, maskName, 'BEAM-DIMAP')
    snappy.ProductIO.writeProduct(mask, maskName_tif, 'GeoTIFF')
    return


def EmpBathymetry(csv_path, s2dirName):
    mask_merge = os.path.join(s2dirName, '*_Res_Sub_deglint_mask.dim')
    maskPath = glob.glob(mask_merge)
    masking = snappy.ProductIO.readProduct(maskPath[0])
    search_criteria = "*_snap.csv"
    csvPath_merge = os.path.join(csv_path, search_criteria)
    vector_csv_path = glob.glob(csvPath_merge)
    repeat = 'y'
    while repeat == 'y':
        parameters = snappy.HashMap()
        print('')
        bandcomb = input('\033[1;32mSelect band combination (two bands \"WITH comma separator\" and \"WITHOUT space\") [B1,B2,B3,B4,...]: ''\033[0m')
        parameters.put('sourceBands', bandcomb)
        parameters.put('bathymetryFile', vector_csv_path[0])
        empBathy = snappy.GPF.createProduct("EmpiricalBathymetryOp", parameters, masking)
        parameters = snappy.HashMap()
        parameters.put('demName', 'Copernicus 30m Global DEM')
        parameters.put('demResamplingMethod', 'BICUBIC_INTERPOLATION')
        parameters.put('elevationBandName', 'DEM')
        empBathyDEM = snappy.GPF.createProduct("AddElevation", parameters, empBathy)
        bathyName = s2dirName + '/' + masking.getName() + '_empBathy_' + bandcomb[:2] + bandcomb[3:]
        bathyName_tif = s2dirName + '/' + 'SNAPempBathy_' + masking.getName()[11:19] + '_' + bandcomb[:2] + bandcomb[3:]
        snappy.ProductIO.writeProduct(empBathyDEM, bathyName, 'BEAM-DIMAP')
        snappy.ProductIO.writeProduct(empBathyDEM, bathyName_tif, 'GeoTIFF')
        repeat = input('\033[1;32mDo you want to select another combination (y or n)? ''\033[0m')
    return
