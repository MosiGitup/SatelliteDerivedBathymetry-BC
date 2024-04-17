"""
# Copyright 2023 © Centre Interdisciplinaire de développement en Cartographie des Océans (CIDCO), Tous droits réservés
@Mohsen_Feizabadi ---
"""

from qgis.core import *
from PyQt5.QtGui import QColor
import numpy as np


def pointStyle(pointLayer, field):
    num_classes = 9
    classification_method = QgsClassificationQuantile()

    format = QgsRendererRangeLabelFormat()
    format.setFormat("%1 - %2")
    format.setPrecision(2)
    format.setTrimTrailingZeroes(True)

    default_style = QgsStyle().defaultStyle()
    color_ramp = default_style.colorRamp('Turbo')

    renderer = QgsGraduatedSymbolRenderer()
    renderer.setClassAttribute(field)

    renderer.setClassificationMethod(classification_method)
    renderer.setLabelFormat(format)
    renderer.updateClasses(pointLayer, num_classes)
    renderer.updateColorRamp(color_ramp)

    pointLayer.setRenderer(renderer)
    pointLayer.triggerRepaint()


def rasterStyle(rasterLayer):
    provider = rasterLayer.dataProvider()
    stats = provider.bandStatistics(1, QgsRasterBandStats.All)
    min = stats.minimumValue
    max = stats.maximumValue
    raster_interval = np.zeros(5)
    raster_interval[0] = min
    raster_interval[-1] = max
    for num_cls in range(1, 4):
        raster_interval[num_cls] = raster_interval[num_cls - 1] + ((max - min) / 5)
    shader = QgsRasterShader()
    fnc = QgsColorRampShader(
        minimumValue=min,
        maximumValue=max,
        type=QgsColorRampShader.Interpolated)
    i = []
    i.append(fnc.ColorRampItem(min, QColor('#d7191c')))
    i.append(fnc.ColorRampItem(raster_interval[1], QColor('#fdae61')))
    i.append(fnc.ColorRampItem(raster_interval[2], QColor('#ffffbf')))
    i.append(fnc.ColorRampItem(raster_interval[3], QColor('#abdda4')))
    i.append(fnc.ColorRampItem(max, QColor('#2b83ba')))

    fnc.setColorRampItemList(i)
    shader.setRasterShaderFunction(fnc)
    renderer = QgsSingleBandPseudoColorRenderer(provider, 1, shader)
    renderer.setOpacity(1.0)
    renderer.legendSymbologyItems()
    rasterLayer.setRenderer(renderer)
    rasterLayer.triggerRepaint()
