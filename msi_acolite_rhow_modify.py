"""
# Copyright 2023 © Centre Interdisciplinaire de développement en Cartographie des Océans (CIDCO), Tous droits réservés
@Mohsen_Feizabadi ---
"""

acolite_package = sys.argv[11]
username_copernicus = sys.argv[12]
password_copernicus = sys.argv[13]

import sys, os
UserHome = os.path.expanduser(acolite_package)
sys.path.append(os.path.join(UserHome))
import acolite as ac
import geopandas as gpd
import pandas as pd
import geojson, json
from sentinelsat import SentinelAPI, geojson_to_wkt
from shapely.geometry import box, Point
import shutil
import xarray as xr
import warnings, requests
from datetime import datetime, timedelta
import numpy as np

DownloadResult = None


## *** Class to download Sentinel-2 MSI data from Copernicus Hub and process it with ACOLITE to get the water reflectance values.
class msi_acolite:
    def __init__(self, Surface, TideHeight, EPSG, Date, TmpPath, L1C_path, vectorSDB_date, tileName, vectorSDB):
        self.EPSG = EPSG

        # Convert Surface to Geodataframe
        self.Surface = Surface
        self.GeometrySurface = gpd.points_from_xy(self.Surface['x'], self.Surface['y'], crs="EPSG:"+str(self.EPSG))
        self.gdf = gpd.GeoDataFrame(self.Surface, geometry=self.GeometrySurface)

        # Create BBox from Surface
        self.BBox = box(*self.gdf.total_bounds)

        # Convert BBox to WGS84 for satellite image search only
        self.BBoxJSON = gpd.GeoSeries([self.BBox]).set_crs('EPSG:'+str(self.EPSG)).to_crs('EPSG:4326').to_json()
        self.BBoxJSON = json.loads(self.BBoxJSON)
        self.Date = Date
        self.TmpPath = TmpPath
        self.L1C_path = L1C_path

        # Optional TideHeight to use H (water column height) instead of Z (bottom altitude)
        self.TidelHeight = TideHeight
        self.SDBdate = vectorSDB_date
        self.TileName = tileName[4:10]
        self.vectorSDB = vectorSDB

    ## *** Download the Sentinel-2 MSI data from Copernicus Hub
    def download_L1c(self, uuidList, imageList):
        global DownloadResult

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
        L1cPath = os.path.join(self.L1C_path, "L1C")
        try:
            os.makedirs(L1cPath)
        except:
            print("")
            pass
        url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({uuidList})/$value"
        headers = {"Authorization": f"Bearer {access_token}"}
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, headers=headers, stream=True)
        image_name = imageList
        downloaded_image = L1cPath + '/' + image_name + ".zip"
        if not os.path.isfile(downloaded_image):
            print('\033[1;32mDownloading ... ''\033[0m')
            with open(downloaded_image, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
        DownloadResult = downloaded_image
        return DownloadResult

    ## *** Water reflectance values calculation
    def get_rhow(self, uuidList, imageList, crs, filtered_vectorSDB_projected_selected, txtSurface, DownloadResult):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
        if not txtSurface:
            DownloadResult = self.download_L1c(uuidList, imageList)
            txtSurface = 1

        ## *** Create directory for ACOLITE processing
        AcolitePath = os.path.join(self.TmpPath)
        try:
            os.makedirs(AcolitePath)
        except:
            print("")
            pass
        _, file_dir = os.path.split(DownloadResult)

        ## *** Unzip the L1C product to input the SAFE folder to acolite
        shutil.unpack_archive(DownloadResult, AcolitePath)
        InFile = os.path.join(AcolitePath, file_dir[:-4]+".SAFE")

        ## *** Save the bounding box as a geojson file to use as a polygon limit in ACOLITE processing
        TmpGeojson = os.path.join(AcolitePath, "polygon_limit.geojson")
        with open(TmpGeojson, 'w') as outfile:
            json.dump(self.BBoxJSON, outfile)

        ## *** Define the ACOlITE settings for the atmospheric compensation processing
        acolitesettings = {"inputfile": InFile,
                           "output": AcolitePath,
                           "polygon": TmpGeojson,
                           "polygon_limit": True,
                           # "l2w_mask_threshold":0.06,
                           "l2w_parameters": ['rhow_*'],
                           "s2_target_res": 10,
                           "output_xy": True,
                           "reproject_before_ac": True,
                           "output_projection_epsg": self.EPSG,
                           "dsf_residual_glint_correction": True,
                           "l2w_export_geotiff": True,
                           "blackfill_skip": False
                           }
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
        gjsonFile = gpd.read_file(TmpGeojson)
        gjsonFile = gjsonFile.to_crs(crs)
        points = [Point(xy) for xy in zip(filtered_vectorSDB_projected_selected.x, filtered_vectorSDB_projected_selected.y)]
        pointsInsideTile = 0
        for point_index, point in enumerate(points):
            for index, row in gjsonFile.iterrows():
                if point.within(row.geometry):
                    pointsInsideTile += 1
                    break
        if pointsInsideTile == 0:
            print('\033[1;31mThere is no bathymetry points in this surface ... ''\033[0m')
            shutil.rmtree(AcolitePath, ignore_errors=True)
            return DownloadResult, txtSurface
        else:
            AcoliteResult = ac.acolite.acolite_run(settings=acolitesettings)
            from l2wBlackFill import BlackFill
            _, statsList = BlackFill(AcolitePath)
            for i in range(len(statsList)):
                if all(np.isnan(ele) for ele in statsList[i][0]):
                    print('\033[1;31mAcolite outputs have only ''nan'' values ... ''\033[0m')
                    shutil.rmtree(AcolitePath, ignore_errors=True)
                    return DownloadResult, txtSurface
            L2Array = xr.open_dataset(AcoliteResult[0]['l2w'][0])
            df = L2Array.to_dataframe()
            df = df.reset_index()
            df = df.drop(columns=['x', 'y', 'transverse_mercator', 'l2_flags'])
            df = df.rename(columns={'lon': 'x', 'lat': 'y'})
            shutil.rmtree(InFile, ignore_errors=True)
            return DownloadResult, txtSurface
