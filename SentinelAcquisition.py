"""
# Copyright 2023 © Centre Interdisciplinaire de développement en Cartographie des Océans (CIDCO), Tous droits réservés
@Mohsen_Feizabadi ---
"""

import os
import glob
import geojson
from shapely.geometry import Polygon
from tkinter import filedialog, Tk
import pandas as pd
import geopandas as gpd
import requests
from datetime import datetime, timedelta
import _pickle as pickle

username_copernicus = sys.argv[7]
password_copernicus = sys.argv[8]

def SentinelQuery(project_path, gjson, date1, date2, vectorSDB, vectorSDB_date, tileName):
    gjsonFile = gpd.read_file(gjson)
    west = []
    south = []
    east = []
    north = []
    left = gjsonFile.bounds.minx
    right = gjsonFile.bounds.maxx
    up = gjsonFile.bounds.maxy
    down = gjsonFile.bounds.miny
    F = Polygon([(left, down), (right, down), (right, up), (left, up)])
    footprint = F.wkt
    productname='SENTINEL-2'
    cloudCover = ['5.00', '10.00', '15.00', '100.0']
    productType = 'S2MSI1C'
    print('\033[1;34mDate interval to download the images: ''\033[0m')
    print('\033[1;32mFROM: ' + date1 + '\033[0m')
    print('\033[1;32mTO: ' + date2 + '\033[0m')
    imageList = {}
    uuidList = {}
    filtered_vectorSDB = {}
    for cp in range(len(cloudCover)):

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
        json = requests.get(f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq '{productname}' and\
                              Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value lt {cloudCover[cp]}) and\
                              Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq '{productType}') and\
                              OData.CSC.Intersects(area=geography'SRID=4326;{footprint}') and\
                              ContentDate/Start gt {date1}T00:00:00.000Z and ContentDate/Start lt {date2}T00:00:00.000Z&$top=1000").json()
        products_df = pd.DataFrame.from_dict(json['value'])
        if len(products_df) == 0:
            raise ValueError("No product found for the given parameters")
        repeatFirstLoop = 1
        while repeatFirstLoop > 0:
            imageList[cloudCover[cp] + '% Cloud'] = []
            uuidList[cloudCover[cp] + '% Cloud'] = []
            imgs = []
            img_ind = []
            ind = []
            print('\n')
            print('\033[1;34mAvailable L1C images in determined time interval''\033[0m' + '\033[1;32m', '(' + cloudCover[cp] + '% Cloud)''\033[0m')
            for im in range(len(products_df)):
                imgs.append(products_df.Name[im][:-5])
                img_ind.append(products_df.Id[im])
                ind.append(im)
            Img_oneLoop = 0
            vectorSDB_date.sort()
            for i in range(len(imgs)):
                for j in range(len(vectorSDB_date)):
                    if vectorSDB_date[j] in imgs[i] and tileName in imgs[i]:
                        print('\033[1;34m', '[' + str(i) + '] ---> ', imgs[i], '\033[0m')
                        Img_oneLoop += 1
            if Img_oneLoop == 0:
                print("\033[1;33mTHERE IS NO IMAGE IN THE TIMESTAMP OF BATHYMETRY DATA FOR THIS CLOUD COVERAGE !!!"'\033[0m')
            print('\n')
            qst2 = 0
            repeatSecondLoop = 1
            while repeatSecondLoop > 0:
                if qst2 == 0:
                    select_image = input('\033[1;32mSelect your interest image number (If there is no image with this cloud percentage OR you want see other images with other cloud percentage, press R/r): ''\033[0m')
                    if select_image == 'R' or select_image == 'r':
                        repeatFirstLoop = 0
                        repeatSecondLoop = 0
                        break
                elif qst2 == 1:
                    select_image = input('\033[1;32mSelect another image number OR press r/R: ''\033[0m')
                    if select_image == 'R' or select_image == 'r':
                        repeatFirstLoop = 0
                        repeatSecondLoop = 0
                        break
                UUID = img_ind[int(select_image)]
                sat_image = imgs[int(select_image)]
                satDateTime_index1 = sat_image.find('_', 4)
                satDateTime_index2 = sat_image.find('_', satDateTime_index1 + 1)
                satDateTime = sat_image[satDateTime_index1 + 1: satDateTime_index2]
                satDateTime_dbFormat = (satDateTime[:4] + '-' + satDateTime[4:6] + '-' + satDateTime[6:8] + ' ' +
                                        satDateTime[9:11] + ':' + satDateTime[11:13] + ':' + satDateTime[13:])
                sat_date_time = datetime.strptime(satDateTime_dbFormat, '%Y-%m-%d %H:%M:%S')
                one_hour_before = sat_date_time - timedelta(hours=1)
                one_hour_after = sat_date_time + timedelta(hours=1)
                new_vectorSDB = pd.to_datetime(vectorSDB['t'][1:])
                bathy_vectorSDB = new_vectorSDB[(new_vectorSDB >= one_hour_before) & (new_vectorSDB <= one_hour_after)]
                filtered_vectorSDB[sat_image[11:26]] = bathy_vectorSDB
                bathyPointsInImage = len(bathy_vectorSDB)
                print('\033[1;36mNumber of bathymetry points in this acqusition imagery --> ' + str(bathyPointsInImage) + '\033[0m')
                if bathy_vectorSDB.empty:
                    filtered_vectorSDB.pop(sat_image[11:26])
                    if Img_oneLoop > 1:
                        qst2 = 1
                        continue
                else:
                    if imageList[cloudCover[cp] + '% Cloud']:
                        imageList[cloudCover[cp] + '% Cloud'] += [sat_image]
                        uuidList[cloudCover[cp] + '% Cloud'] += [UUID]
                    else:
                        imageList[cloudCover[cp] + '% Cloud'] = [sat_image]
                        uuidList[cloudCover[cp] + '% Cloud'] = [UUID]
                    qst1 = input('\033[1;32mWould you like to select another image (y oy n): ''\033[0m')
                    if qst1 == 'y':
                        qst2 = 1
                        continue
                    else:
                        repeatFirstLoop = 0
                        repeatSecondLoop = 0
                        qst2 = 0
                        break
        if len(uuidList[cloudCover[cp] + '% Cloud']) == 0:
            del uuidList[cloudCover[cp] + '% Cloud']
            del imageList[cloudCover[cp] + '% Cloud']
        varDict = {'date1': date1, 'date2': date2, 'vectorSDB_date': vectorSDB_date, 'imageList': imageList,
                   'uuidList': uuidList, 'filtered_vectorSDB': filtered_vectorSDB}
        with open(project_path + '/variables.txt', 'wb') as f:
            f.write(pickle.dumps(varDict))
    return imageList, uuidList, filtered_vectorSDB