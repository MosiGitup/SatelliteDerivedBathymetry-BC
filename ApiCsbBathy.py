"""
# Copyright 2023 © Centre Interdisciplinaire de développement en Cartographie des Océans (CIDCO), Tous droits réservés
@Mohsen_Feizabadi ---
"""

import os
import sys
import requests
from qgis_selectDB_Jobs import ymin_tile, ymax_tile, xmin_tile, xmax_tile, project_path, yr_mon_day, mapJson_name, yr, mn, dy, td, host_name

access_email = sys.argv[5]
access_key = sys.argv[6]

csvPath = project_path
today_csv = str(yr_mon_day.tm_year) + str(yr_mon_day.tm_mon) + str(yr_mon_day.tm_mday)
print('\033[1;32mVerification of acceptable jobs ... ''\033[0m')
year = yr
month = mn
day = dy
timeDiff = td

class CsvApi:
    def __init__(self, host="localhost"):
        self.host = host

    def upload(self, userName, key, minLat, maxLat, minLon, maxLon, csvPath, maxDepth, year, month, day, hour, minute, timeDiff):
        sys.stderr.write("requesting ... \n")

        url = "http://{}/CSBWeb/CsvServlet".format("csb.cidco.ca")
        payload = {
            "email": userName,
            "apiCsvKey": key,
            "minLat": minLat,
            "maxLat": maxLat,
            "minLon": minLon,
            "maxLon": maxLon,
            "pathCsv": csvPath,
            "maxDepth": maxDepth,
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
            "min": minute,
            "timeDiff": timeDiff
        }
        r = requests.post(url, json=payload)

        if r.status_code == 200:
            with open(csvPath + "/" + mapJson_name[:-8] + "_" + today_csv + "_" + str(year) + str(month) + str(day) + ".csv", "wb") as file:
                file.write(r.content)
            print("File downloaded successfully as '.csv'")
        elif r.status_code == 204:
            print("Error: {}  No Bathymetry avalaible for this area".format(r.status_code))
        elif r.status_code == 401:
            print("Error: {}  Access denied, this API key is not valid.".format(r.status_code))
        else:
            print("Error: {}".format(r.status_code))


csv = CsvApi()

try:
    userName = access_email
    key = access_key
    minLat = ymin_tile
    maxLat = ymax_tile
    minLon = xmin_tile
    maxLon = xmax_tile
    csvPath = csvPath
    maxDepth = 0
    year = year
    month = month
    day = day
    hour = 0
    minute = 0
    timeDiff = timeDiff
    csv.upload(userName, key, minLat, maxLat, minLon, maxLon, csvPath, maxDepth, year, month, day, hour, minute, timeDiff)
except Exception as e:
    sys.stderr.write("Upload failed: {}\n".format(str(e)))