"""
# Copyright 2023 © Centre Interdisciplinaire de développement en Cartographie des Océans (CIDCO), Tous droits réservés
@Mohsen_Feizabadi ---
"""

from tkinter import filedialog, Tk
import rasterio
import numpy as np
import csv, os, sys, glob
import pandas as pd
from numpy.linalg import inv
from datetime import datetime, timedelta


class SatelliteDerivedBathymetry_all:
    """
    Satellite derived bathymetry calculation from water reflectance value as input file (.tif) by using two methods:
    1. Stumpf  --> https://doi.org/10.4319/lo.2003.48.1_part_2.0547
    2. Lyzenga --> https://doi.org/10.1080/01431168108948342
    """

    ## *** Its input are two bands (.tif) of L2W acolite outputs. Its outputs are two .csv files which includes; x, y and pixel value columns.
    def how_tif_inputs(acoliteaPath, select_process, tif_path, output_dir, acol_crs):
        if select_process == '1':

            ## *** select the bands (e.g. rhow_492 and rhow_560)
            root = Tk()
            search_criteria = "*.tif"
            tif_path = filedialog.askopenfilenames(filetypes=[(".tif file", search_criteria)], initialdir=acoliteaPath, title='Select the required r_how bands')
            root.update()
            root.destroy()
        tif_fps = list(tif_path)
        full_path = []
        fname = {}
        raster = []
        raster_array = {}

        ## *** Rater to array
        for i in range(len(tif_path)):
            full_path.append(os.path.realpath(tif_fps[i]))
            path, fname[i] = os.path.split(full_path[i])
            src = rasterio.open(tif_path[i])
            raster.append(src.read())
            raster_array[i] = np.asarray(raster[i]).reshape(-1)
        out_meta = src.meta.copy()
        if select_process == '1':
            output_dir = acoliteaPath
        output_dir_path, output_dir_fname = os.path.split(output_dir)
        if select_process == '1':
            save_dir = os.path.join(output_dir, fname[0][:-22] + fname[0][-13:-10] + '_' + fname[1][-13:-10])
        else:
            save_dir = os.path.join(output_dir, fname[0][:-22] + fname[0][-13:-10] + '_' + fname[1][-13:-10])
        try:
            os.mkdir(save_dir)
        except:
            print('')
        out_dir = 'outputs'
        dir_path = os.path.join(output_dir, out_dir)
        try:
            os.mkdir(dir_path)
        except:
            print('')
        if select_process == '1':
            result_dir = os.path.join(dir_path, fname[0][:-22] + fname[0][-13:-10] + '_' + fname[1][-13:-10])
        else:
            result_dir = os.path.join(dir_path, fname[0][:-22] + fname[0][-13:-10] + '_' + fname[1][-13:-10])
        try:
            os.mkdir(result_dir)
        except:
            print('')

        ## *** Calculation of band ratio of two bands (for Stumpf method)
        if select_process == '1':
            ratio_bands = np.log10(1000*raster[0])/np.log10(1000*raster[1])
            out_meta.update({"driver": "GTiff",
                             "crs": acol_crs
                             })
            filepath_bandRatio = result_dir + '/BandRatio_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '.tif'
            print('\033[1;34m', 'The band ratio .tif file of ' + fname[0][-18:-10] + ' and ' + fname[1][-18:-10] + ' is saved: ' +
                  result_dir + '/BandRatio_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '.tif', '\033[0m')
            with rasterio.open(filepath_bandRatio, "w", **out_meta) as dest:
                dest.write(ratio_bands)

        ## *** Saving .tif file to .csv file
        height = src.shape[0]
        width = src.shape[1]
        filepath_how = {}
        for k in range(len(raster)):
            cols, rows = np.meshgrid(np.arange(width), np.arange(height))
            xs, ys = rasterio.transform.xy(src.transform, rows, cols)
            lons= np.array(xs)
            lats = np.array(ys)
            lons_array = np.asarray(lons).reshape(-1)
            lats_array = np.asarray(lats).reshape(-1)
            raster_txtFile = zip(lons_array, lats_array, raster_array[k])
            print('\033[1;34m', str(k+1) + ". input .tif file: ", fname[k], '\033[0m')
            filepath_how[k] = save_dir + '/' + fname[k][-22:-10] + '.csv'
            print('\033[1;34m', 'and its output .csv file: ', fname[k][-22:-10] + '.csv', '\033[0m')
            with open(filepath_how[k], 'w') as f:
                writer = csv.writer(f, delimiter=',')
                writer.writerows(raster_txtFile)
        if select_process == '1':
            return raster, save_dir, output_dir_path, ratio_bands, out_meta, filepath_how, result_dir, fname, lons_array, lats_array, tif_path, output_dir
        else:
            return raster, save_dir, output_dir_path, out_meta, filepath_how, result_dir, fname, lons_array, lats_array

    ## *** Using bathymetry points as input (.csv), the mean value of all bathymetry points inside each pixel (10mx10m resolution) are calculated.
    def intersectPointPixel(filepath_how, select_process, vector_csv_path, output_dir_path, save_dir, qgisPath, filtered_vectorSDB_projected):
        if select_process == '1':
            search_criteria = "*_sdb.csv"
            vector_csv_path = glob.glob(qgisPath + search_criteria)
        _, fname_vec = os.path.split(vector_csv_path[0])

        ## *** Calling the registered raster file (.csv)
        raster_xyz = pd.read_csv(filepath_how[0], sep=",", header=None, names=['x', 'y', 'z'])

        ## *** Finding the indeces of minimum and maximum coordinates of raster (x and y)
        min_x = np.min(raster_xyz.x)
        max_y = np.max(raster_xyz.y)
        row_num = np.where(raster_xyz.x == min_x)
        col_num = np.where(raster_xyz.y == max_y)

        ## *** Assigning the grid coordinates
        grid_x_coord = raster_xyz.x[col_num[0]] - 5
        grid_y_coord = raster_xyz.y[row_num[0]] + 5
        last_x_grid = pd.Series([grid_x_coord[col_num[0][-1]] + 10], index=[grid_x_coord.index[-1] + 1])
        grid_x_coord = grid_x_coord._append(last_x_grid)
        first_y_grid = pd.Series([grid_y_coord[row_num[0][-1]] - 10], index=[grid_y_coord.index[-1] + len(col_num[0])])
        grid_y_coord = grid_y_coord._append(first_y_grid)

        ## *** Mean value of all bathymetry points which are inside a pixel. If the points are in a pixel with "NaN" value, the points are removed.
        raster_pix_ind = {}
        intersect_points = {}
        mean_values = {}
        for i in range(len(row_num[0])):
            for j in range(len(col_num[0])):
                raster_pix_ind = np.where(((filtered_vectorSDB_projected.x >= grid_x_coord[grid_x_coord.index[j]]) & (filtered_vectorSDB_projected.x <= grid_x_coord[grid_x_coord.index[j+1]])) & ((filtered_vectorSDB_projected.y <= grid_y_coord[grid_y_coord.index[i]]) & (filtered_vectorSDB_projected.y >= grid_y_coord[grid_y_coord.index[i+1]])))
                if len(raster_pix_ind[0]) > 0:
                    intersect_points[j, i] = filtered_vectorSDB_projected.iloc[raster_pix_ind]
                    mean_values[j, i] = pd.Series([grid_x_coord[grid_x_coord.index[j]] + 5, grid_y_coord[grid_y_coord.index[i]] - 5, float("{:.4f}".format(np.mean(intersect_points[j, i].z)))])
                    nan_detect = mean_values[j, i].dropna()
                    if len(nan_detect) == 2:
                        del mean_values[j, i]

        ## *** Saving the results in .csv format
        filepath_vec = save_dir + '/' + fname_vec[:-8] + '_insidePixels.csv'
        print('\033[1;34m', 'Points inside the pixels: ' + fname_vec[:-8] + '_insidePixels.csv', '\033[0m')
        pd.DataFrame.from_dict(data=mean_values, orient='index').to_csv(filepath_vec, header=False)
        return filepath_vec, vector_csv_path
    
    ## *** Calculation of pixels mean value for the band ratio pixles which have the bathymetry points for inserted two bands (Stumpf method).
    def BR_PointrasterCoordinates(filepath_how, filepath_vec, save_dir, fname):

        ## *** Calling the registered raster files and bathymetry points file (.csv).
        raster1 = pd.read_csv(filepath_how[0], sep=",", header=None, names=['x', 'y', 'z'])
        raster2 = pd.read_csv(filepath_how[1], sep=",", header=None, names=['x', 'y', 'z'])
        points = pd.read_csv(filepath_vec, sep=",", header=None, names=['x', 'y', 'z'])

        ## *** Band ratio calculation and create a dataframe.
        raster_ratio = {'x': raster1.x, 'y': raster1.y, 'z': np.log10(1000*raster1.z)/np.log10(1000*raster2.z)}
        raster_ratio_xyz = pd.DataFrame(raster_ratio)

        ## *** Assigning the x and y coordinates for new dataframe and removing the "NaN" values.
        control_points = points.iloc[:].values
        raster_index = []
        pixel_extract = {}
        for i in range(len(control_points)):
            raster_index.append(np.where((raster_ratio_xyz.x == control_points[i][0]) & (raster_ratio_xyz.y == control_points[i][1])))
            pixel_extract[i] = pd.Series([raster_ratio_xyz.x[raster_index[i][0][0]], raster_ratio_xyz.y[raster_index[i][0][0]], raster_ratio_xyz.z[raster_index[i][0][0]]])
            raster_nan_detect = pixel_extract[i].dropna()
            if len(raster_nan_detect) == 2:
                del pixel_extract[i]

        pixel_extract_keys = list(pixel_extract.keys())
        control_points_extract = control_points[pixel_extract_keys]
        pixel_extract_values = list(pixel_extract.values())
        new_pixel_extract = []
        for j in range(len(pixel_extract)):
            new_pixel_extract.append(list(pixel_extract_values[j]))
        new_pixel_extract = np.array(new_pixel_extract)

        ## *** Saving the results in .csv format
        filepath_ras = save_dir + '/BR_vector_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '.csv'
        print('\033[1;34m', 'Band ratio vector file: BR_vector_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '.csv', '\033[0m')
        pd.DataFrame(new_pixel_extract).to_csv(filepath_ras, sep=",", header=False, index=True)
        return control_points_extract, filepath_ras, new_pixel_extract
    
    ## *** Calculation of Stumpf parameters with the Least square method.
    def BR_linearRegression(control_points_extract, filepath_ras, result_dir, fname, new_pixel_extract):

        """
        A.X = L
        A = Coefficient matrix
        X = Unknown parameters
        L = Observations or exact values
        In our case the matrix is:
                   -   -
        [x 1]      | a |  = [L]
             (1*2) | b |       (1*1)
                   -   - (2*1)
        
        x = raster pixels
        L = control points
        
        """

        ## *** Coefficient matrix
        def Jacobian(points):
            J = np.zeros(shape=(1, 2))
            J[0][0] = points
            J[0][1] = 1
            return J

        ## *** Approximation matrix
        def Approximation(a, b, x):
            L = a*x + b
            return L

        ## *** Calling the band ratio file and bathymetry points file as control points (.csv).
        rp = pd.read_csv(filepath_ras, sep=",", header=None, names=['x', 'y', 'z'])
        rp_pixel = np.array(rp.z)
        cp_point = control_points_extract[:, 2]
        X = np.zeros(shape=(2, 1))
        Approximate_value = np.zeros(shape=(2, 1))
        A = np.zeros(shape=(len(rp), 2))
        F = np.zeros(shape=(len(rp), 1))
        Iteration = 1
        error = 1

        ## *** Repeat the computation until reached to the desired accuracy.
        while error > 10e-5:
            Approximate_value[0] = X[0]     # a
            Approximate_value[1] = X[1]     # b
            for i in range(len(rp)):
                A[i][:] = Jacobian(rp_pixel[i])
                F[i] = cp_point[i] - Approximation(Approximate_value[0], Approximate_value[1], rp_pixel[i])

            X = inv(A.T.dot(A)).dot(A.T.dot(F))
            X = X + Approximate_value 
            Iteration = Iteration + 1
            error1 = abs(abs(X[0])-abs(Approximate_value[0]))
            error2 = abs(abs(X[1])-abs(Approximate_value[1]))
            error = ((error1**2 + error2**2)/2)**0.5
        print('')
        rp_point = X[0][0] * new_pixel_extract[:, 2] + X[1][0]
        results_output = result_dir + '/outputs_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '_BR.txt'
        stdout_fileno = sys.stdout        
        linReg_output = ['Linear regression parameters:', 'a(m1) = ' f'{X[0][0]:.3f}', 'b(m0) = ' f'{X[1][0]:.3f}']
        sys.stdout = open(results_output, 'w')
        for ip in linReg_output:
            sys.stdout.write(ip + '\n')
            stdout_fileno.write(ip + '\n')
        sys.stdout.close()
        sys.stdout = stdout_fileno
        return X, rp_pixel, cp_point, rp_point
    
    ## *** Band ratio (Stumpf) satellite derived bathymetry
    def BR_SDB(X, ratio_bands, out_meta, result_dir, fname, acol_crs):
        SDB = X[0][0] * ratio_bands + X[1][0]
        out_meta.update({"driver": "GTiff",
                         "crs": acol_crs
                         })
        print('')
        filepath_SDB = result_dir + '/SDB_BandRatio_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '.tif' 
        print('\033[1;34m', 'The result of Band Ratio SDB .tif file: ' + result_dir + '/SDB_BandRatio_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '.tif', '\033[0m')
        with rasterio.open(filepath_SDB, "w", **out_meta) as dest:
            dest.write(SDB)
        return SDB

    ## *** Calculation of pixels mean value which have the bathymetry points for inserted two bands (Lyzenga method).
    def LL_PointrasterCoordinates(filepath_how, filepath_vec, save_dir, fname):

        ## *** Calling the registered raster files and bathymetry points file (.csv).
        raster1 = pd.read_csv(filepath_how[0], sep=",", header=None, names=['x', 'y', 'z'])
        raster2 = pd.read_csv(filepath_how[1], sep=",", header=None, names=['x', 'y', 'z'])
        points = pd.read_csv(filepath_vec, sep=",", header=None, names=['x', 'y', 'z'])

        ## *** Assigning the x and y coordinates for both rasters and removing the "NaN" values.
        control_points = points.iloc[:].values
        raster_index = []
        pixel_extract_r1 = {}
        pixel_extract_r2 = {}
        for i in range(len(control_points)):
            raster_index.append(np.where((raster1.x == control_points[i][0]) & (raster1.y == control_points[i][1])))
            pixel_extract_r1[i] = pd.Series([raster1.x[raster_index[i][0][0]], raster1.y[raster_index[i][0][0]], raster1.z[raster_index[i][0][0]]])
            pixel_extract_r2[i] = pd.Series([raster2.x[raster_index[i][0][0]], raster2.y[raster_index[i][0][0]], raster2.z[raster_index[i][0][0]]])
            raster_nan_detect = pixel_extract_r1[i].dropna()
            if len(raster_nan_detect) == 2:
                del pixel_extract_r1[i], pixel_extract_r2[i]

        pixel_extract_keys = list(pixel_extract_r1.keys())
        control_points_extract = control_points[pixel_extract_keys]
        pixel_extract_r1_values = list(pixel_extract_r1.values())
        pixel_extract_r2_values = list(pixel_extract_r2.values())
        new_pixel_extract = []
        for j in range(len(pixel_extract_r1)):
            new_pixel_extract.append(list(pixel_extract_r1_values[j]))
            new_pixel_extract[j] = new_pixel_extract[j] + [pixel_extract_r2_values[j][2]]
        new_pixel_extract = np.array(new_pixel_extract)
        print('')

        ## *** Saving the results of two rasters in the same .csv format
        filepath_ras = save_dir + '/LL_vector_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '.csv'
        print('\033[1;34m', 'Vector file for two selected bands: LL_vector_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '.csv', '\033[0m')
        pd.DataFrame(new_pixel_extract).to_csv(filepath_ras, sep=",", header=False, index=True)
        return control_points_extract, filepath_ras, new_pixel_extract
    
    ## *** Calculation of Lyzenga parameters with the Least square method.
    def LL_linearRegression(control_points_extract, filepath_ras, result_dir, fname, new_pixel_extract):

        """
        A.X = L
        A = Coefficient matrix
        X = Unknown parameters
        L = Observations or exact values
        In our case the matrix is:
                        -    -
        [1 x1 x2]      | a  |  
                 (1*3) | b1 |   = [L]    
                       | b2 |        (1*1)
                       -    -(3*1)
        
        xi = raster pixels
        L = control points
        
        """

        ## *** Coefficient matrix
        def Jacobian(points):
            J = np.zeros(shape=(1, 3))
            J[0][0] = 1
            J[0][1] = points[0]
            J[0][2] = points[1]
            return J

        ## *** Approximation matrix
        def Approximation(a, b1, b2, x1, x2):
            L = a + b1*x1 + b2*x2
            return L

        ## *** Calling the raster bands file and bathymetry points file as control points (.csv).
        rp = pd.read_csv(filepath_ras, sep=",", header=None, names=['x', 'y', 'band1', 'band2'])
        rp_pixel = np.array([rp.band1, rp.band2]).T
        cp_point = control_points_extract[:, 2]

        ## *** Finding the index of more than 30m depth of bathymetry points.
        below30_index = np.where(control_points_extract[:, 2] <= -30)
        below30 = np.column_stack((below30_index[0], rp_pixel[below30_index[0]]))

        """
        Log-Linear formula:
        L_linear = Ln(Li - Li_min)
        L_linear: linearized spectral value
        Li: pixel values of band i (raster files)
        Li_min: minimum values of band i (more than 30m depth)
        """

        min_reflect_rhow = []
        rp_pixel_sub = []
        nan_values = {}
        for j in range(2):
            min_reflect_rhow.append(min(below30[:, j+1]))
            nan_values[j] = np.where(rp_pixel[:, j] - min_reflect_rhow[j] <= 0.00000001)
            rp_pixel[nan_values[j], j] = min_reflect_rhow[j] + 0.0001
            rp_pixel_sub.append(np.log(rp_pixel[:, j] - min_reflect_rhow[j]))
        rp_pixel_sub = np.array([rp_pixel_sub[0], rp_pixel_sub[1]]).T    

        X = np.zeros(shape=(3, 1))
        Approximate_value = np.zeros(shape=(3, 1))
        A = np.zeros(shape=(len(rp), 3))
        F = np.zeros(shape=(len(rp), 1))
        Iteration = 1
        error = 1

        ## *** Repeat the computation until reached to the desired accuracy.
        while error > 10e-5:
            Approximate_value[0] = X[0]     # a
            Approximate_value[1] = X[1]     # b1
            Approximate_value[2] = X[2]     # b2
            for i in range(len(rp)):
                A[i][:] = Jacobian(rp_pixel_sub[i])
                F[i] = cp_point[i] - Approximation(Approximate_value[0], Approximate_value[1], Approximate_value[2], rp_pixel_sub[i][0], rp_pixel_sub[i][1])
            X = inv(A.T.dot(A)).dot(A.T.dot(F))
            X = X + Approximate_value 
            Iteration = Iteration + 1
            error1 = abs(abs(X[0])-abs(Approximate_value[0]))
            error2 = abs(abs(X[1])-abs(Approximate_value[1]))
            error3 = abs(abs(X[2])-abs(Approximate_value[2]))
            error = ((error1**2 + error2**2 + error3**2)/3)**0.5
        print('')
        nan_values_rp_point = {}
        for i in range(2):
            nan_values_rp_point[i] = np.where(new_pixel_extract[:, i+2] - min_reflect_rhow[i] <= 0.00000001)
            new_pixel_extract[:, i+2][nan_values_rp_point[i][0]] = min_reflect_rhow[i] + 0.0001
        rp_point = X[0][0] + (X[1][0] * np.log(new_pixel_extract[:, 2] - min_reflect_rhow[0])) + (X[2][0] * np.log(new_pixel_extract[:, 3] - min_reflect_rhow[1]))
        results_output = result_dir + '/outputs_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '_LL.txt'
        stdout_fileno = sys.stdout        
        linReg_output = ['Multiple linear regression parameters:', 'a = ' f'{X[0][0]:.3f}', 'b1 = ' f'{X[1][0]:.3f}', 'b2 = ' f'{X[2][0]:.3f}']
        sys.stdout = open(results_output, 'w')
        for ip in linReg_output:
            sys.stdout.write(ip + '\n')
            stdout_fileno.write(ip + '\n')
        sys.stdout.close()
        sys.stdout = stdout_fileno
        return X, rp_pixel, cp_point, min_reflect_rhow, rp_point
    
    ## *** Log-Linear (Lyzenga) satellite derived bathymetry
    def LL_SDB(X, raster, min_reflect_rhow, out_meta, result_dir, fname, acol_crs):
        nan_values_ras = {}
        for i in range(2):
            nan_values_ras[i] = np.where(raster[i][0] - min_reflect_rhow[i] <= 0.00000001)
            raster[i][0][nan_values_ras[i][0], nan_values_ras[i][1]] = min_reflect_rhow[i] + 0.0001
        SDB = X[0][0] + (X[1][0] * np.log(raster[0][0] - min_reflect_rhow[0])) + (X[2][0] * np.log(raster[1][0] - min_reflect_rhow[1]))
        out_meta.update({"driver": "GTiff",
                         "crs": acol_crs
                         })
        print('')
        filepath_SDB = result_dir + '/SDB_LogLinear_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '.tif'
        print('\033[1;34m', 'The result of Log-Linear SDB .tif file is in:' + result_dir + '/SDB_LogLinear_' + fname[0][-13:-10] + '_' + fname[1][-13:-10] + '.tif', '\033[0m')
        with rasterio.open(filepath_SDB, "w", **out_meta) as dest:
            dest.write(SDB, 1)
            
        return SDB
