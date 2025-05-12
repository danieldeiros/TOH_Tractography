# -*- coding: utf-8 -*-
"""
Created on Thu May  8 10:58:00 2025

@author: danie
"""
# Spyder stuff
import matplotlib.pyplot as plt
from pydicom import examples

ds = examples.ct

plt.imshow(ds.pixel_array, cmap=plt.cm.gray)