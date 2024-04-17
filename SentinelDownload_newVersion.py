#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 12 08:14:43 2023

@author: cidco
"""

import os
import glob
import geojson
from sentinelsat import read_geojson, geojson_to_wkt, SentinelAPI
from shapely.geometry import Polygon
from tkinter import filedialog, Tk
import pandas as pd
import requests

#*** OData API
root = Tk()
acolite_path = filedialog.askdirectory(initialdir='/media/cidco/blanc-sablon/Mosi Drive/Python3/Bathymetry', title='Select Acolite outputs directory')
root.update()
root.destroy()
shp = 'map.geojson'
date1 = '2023-09-01'
date2 = '2023-09-10'
gjsonFile = read_geojson(acolite_path + '/' + shp)
west = []
south = []
east = []
north = []
for i in range(len(gjsonFile['features'])):
    west.append(gjsonFile['features'][i].bbox[0])
    south.append(gjsonFile['features'][i].bbox[1])
    east.append(gjsonFile['features'][i].bbox[2])
    north.append(gjsonFile['features'][i].bbox[3])
left = min(west)
right = max(east)
up = max(north)
down = min(south)
F = Polygon([(left, down), (right, down), (right, up), (left, up)])
footprint = F.wkt
productname='SENTINEL-2'
cloudCover = '30.00'
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
        raise e(
            f"Access token creation failed. Reponse from the server was: {r.json()}"
        )
    return r.json()["access_token"]
access_token = get_access_token('mohsen.feizabadi@umontreal.ca', 'MosiCoper_2018')
json = requests.get(f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq '{productname}' and\
                      Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value lt '{cloudCover}') and\
                      Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq '{productType}') and\
                      OData.CSC.Intersects(area=geography'SRID=4326;{footprint}') and\
                      ContentDate/Start gt {date1}T00:00:00.000Z and ContentDate/Start lt {date2}T00:00:00.000Z&$top=10").json()
products_df = pd.DataFrame.from_dict(json['value'])
imgs = []
img_ind = []
ind = []
for im in range(len(products_df)):
    imgs.append(products_df.Name[im][:-5])
    img_ind.append(products_df.Id[im])
    ind.append(im)
for i in range(len(imgs)):
    print('\033[1;34m', '[' + str(i) + '] ---> ', imgs[i], '\033[0m')
select_image = input('\033[1;32mSelect your interest image number: ''\033[0m')

url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({img_ind[int(select_image)]})/$value"

headers = {"Authorization": f"Bearer {access_token}"}

session = requests.Session()
session.headers.update(headers)
response = session.get(url, headers=headers, stream=True)
image_name = imgs[int(select_image)]
with open(acolite_path + '/' + image_name + ".zip", "wb") as file:
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            file.write(chunk)