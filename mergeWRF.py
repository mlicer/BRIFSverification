#!/usr/bin/python
"""
The code merges in time WRF modelData objects into a single object for plotting.

INPUT:
--stations: a list of station objects, containing data about the fields in the
	observationFields list.
--wrf_yesterday,wrf_today,wrf_tomorrow: lists of stations-long obsData objects
	containing WRF data at stations locations for yesterday, today and tomorrow,
	respectively. (today being strdate.)

OUTPUT:
--wrfTimes,wrfPressures: merged 3-day long timeseries of dates and pressures.

Author: Matjaz Licer, NIB MBS @socib
matjaz.licer@mbss.org
"""

import os,sys,re,requests,json
from datetime import datetime,timedelta
from netCDF4 import Dataset
import numpy as np
from sys import exit as q

def mergeWRF(stations,wrf_yesterday,wrf_today,wrf_tomorrow,pressureField):

# numpy.vstack(tup)
	ntimes = len(wrf_yesterday[0].Times)+len(wrf_today[0].Times)+len(wrf_tomorrow[0].Times)

	# merge Times:
	wrfTimes = []
	for wrf in [wrf_yesterday,wrf_today,wrf_tomorrow]:
		wrfTimes = np.append(wrfTimes,wrf[0].Times)

	# merge pressures for all three days and each station:
	wrfPressures = np.zeros( (len(stations) , ntimes) )
	for k in range(len(stations)):
		tmp_pressure = []
		for wrf in [wrf_yesterday,wrf_today,wrf_tomorrow]:
			tmp_pressure = np.append(tmp_pressure, getattr(wrf[k],pressureField))
		wrfPressures[k,:] = tmp_pressure

	return wrfTimes,wrfPressures
