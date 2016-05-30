#!/usr/bin/python
"""
The code performs BRIFS verification against available in situ data. Available
data is determined by the DataDiscovery utility.
External rerequisites:
--HDF5 and netCDF C libraries, built with shared and OpenDAP support.
--numpy, scipy, matplotlib, netCDF4, pandas for Python2.7

INPUT: YYYYMMDD string of the date of verification and oper/hind mode, for example:

./performBRIFSverification.py 20160331 oper
./performBRIFSverification.py 20160331 hind


Author: Matjaz Licer, NIB MBS @socib
matjaz.licer@mbss.org
"""
import os,sys,re,requests,json
from datetime import datetime,timedelta
from netCDF4 import Dataset
import pandas
import numpy as np
from getAllObservations import *
from obsData import *
from modelData import *
from plotBRIFS import *
from mergeWRF import *
from basicStatistics import *
from sys import exit as q


def removeFile(filename):
	try:
		os.remove(filename)
	except:
		pass

def printHelp():
	print("\n")
	print("Check input arguments! Date string YYYYMMDD and oper/hind mode expected!")
	print("Example:")
	print("./performBRIFSverification.py "+datetime.now().strftime("%Y%m%d")+" oper")
	print("\nor\n./performBRIFSverification.py "+datetime.now().strftime("%Y%m%d")+" hind")

	print("\n")
	sys.exit()

def main():

	# check for input date YYYYMMDD from console:
	try:
		strdate=sys.argv[1]
		operMode = sys.argv[2]
	except:
		printHelp()

	# set OPERATIONAL wrf and roms netCDF output directories:

	if operMode=='oper':
		wrfdir = '/home/rissaga/new_setup/Archive/Outputs/WRF/'+strdate+'_op/'
	# set HINDCAST wrf and roms netCDF output directories:
	else:
		wrfdir = '/home/rissaga/new_setup/Archive/Outputs/WRF/'+strdate+'_hind/'

	# wrfdir = '/home/mlicer/'
	romsdir = '/home/rissaga/new_setup/Archive/Outputs/ROMS/'

	plotdir = '/home/mlicer/BRIFSverif/pyVerif/'+strdate+'/'

	os.system('mkdir -p '+plotdir)

	# determine timeWindow [hours] for comparisons:
	timeWindow=48

	# parse start date:
	startdatenum = datetime.strptime(strdate,'%Y%m%d')
	enddatenum = startdatenum+timedelta(hours=timeWindow)

	# set WRF files and dates to read:
	today = startdatenum
	yesterday = startdatenum-timedelta(days=1)
	tomorrow = startdatenum+timedelta(days=1)
	wrfdatestring = datetime.strftime(startdatenum,'%Y-%m-%d_12:00:00')
	wrfdatestring_yesterday = datetime.strftime(startdatenum-timedelta(days=1),'%Y-%m-%d_12:00:00')
	wrfdatestring_tomorrow = datetime.strftime(startdatenum+timedelta(days=1),'%Y-%m-%d_12:00:00')

	wrf_file = wrfdir+'wrfout_d02_'+wrfdatestring
	wrf_file_yesterday = wrfdir+'wrfout_d02_'+wrfdatestring_yesterday
	wrf_file_tomorrow = wrfdir+'wrfout_d02_'+wrfdatestring_tomorrow

	# specify fields for comparisons:
	observationFields=['time','LON','LAT','HEIGHT',\
	'SLEV','QC_SLEV',\
	'WTR_PRE','QC_WTR_PRE',\
	'AIR_PRE','QC_AIR_PRE']

	wrfFields=['location','Times','XLONG','XLAT', 'pointLon','pointLat', 'pointPSFC','pointMSLP']
	romsFields=['location','ocean_time','lon_rho','lat_rho','h','pointLon','pointLat', 'pointSSH']

	# get a list of all available observations:
	fileList = getAllObservations(strdate,timeWindow)

	# exit if empty:
	if not fileList:
		print('\n No observations found for this date: '+strdate+'! \n Exiting.')
		q()
	# keep working if not empty:
	else:
		print "\nReading observation files:"
		sensorType=[]
		for k in range(len(fileList)):
			print fileList[k],"..."
			# determine the sensorType, if any, from the filename:
			m = re.findall(r'.*_(\w+-\w+.?)_L1',fileList[k])
			if m:
				if 'station' in m[0]:
					sensorType.append('')
				else:
					sensorType.append(m[0])
		print ""

	# read the files to 'stations' data object and merge files (sensor types) from different months(years) if neccessary:
	stations,sensorType = obsData(fileList,sensorType,observationFields).read()

	# extract WRF for available grid points:
	wrf_yesterday = modelData(stations,yesterday,wrfFields,romsFields,wrfdir,romsdir, operMode).readWRF()
	wrf_today = modelData(stations,today,wrfFields,romsFields,wrfdir,romsdir, operMode).readWRF()
	wrf_tomorrow = modelData(stations,tomorrow,wrfFields,romsFields,wrfdir,romsdir, operMode).readWRF()

	# merge WRF times and air pressures from all three days for all stations:
	wrf_t_3days,wrf_p_3days = mergeWRF(stations,wrf_yesterday,wrf_today,wrf_tomorrow,'pointMSLP')
	# wrf_t_3days,wrf_p_3days = mergeWRF(stations,wrf_yesterday,wrf_today,wrf_tomorrow,'pointPSFC')

	# extract ROMS
	roms = modelData(stations,startdatenum,wrfFields,romsFields,wrfdir,romsdir, operMode).readROMS()

	# compute basic statistics (BIAS, RMSE, CORR):
	stats = basicStatistics(strdate,sensorType,stations,wrf_t_3days,wrf_p_3days,roms)

	# plot graphs:
	plotBRIFS(plotdir,strdate,sensorType,stations,wrf_t_3days,wrf_p_3days,roms,stats)


if __name__ == '__main__':
    main()
