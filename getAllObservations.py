#!/usr/bin/python
"""
Retrieves all available observations from SOCIB data network using DataDiscovery
utility.

INPUT:
--strdate: string date YYYYMMDD
--timeWindow: time window for data retrieval in hours, should be: 48
"""
import os,sys,re,requests,json
from datetime import datetime,timedelta
from sys import exit as q
from netCDF4 import Dataset
import numpy as np

def getAllObservations(strdate, timeWindow):

	# read start date from console:
	startdatenum = datetime.strptime(strdate,'%Y%m%d')

	# convert start date to formatted string:
	startdatestring = datetime.strftime(startdatenum,'%Y-%m-%dT000000')

	# compute end date and convert to formatted string:
	enddatestring = datetime.strftime(startdatenum+timedelta(hours=timeWindow),'%Y-%m-%dT000000')

	# construct request string:
	requestString = 'http://apps.socib.es/DataDiscovery/list-platforms?'+\
	'init_datetime='+startdatestring+'&end_datetime='+enddatestring#+\
	# '&parameter='+parameter

	# request JSON:
	r = requests.get(requestString)

	# read JSON:
	allPlatforms = r.json()

	# initialize fileList to fill:
	fileList = []
	for k in range(len(allPlatforms)):
		# use regular expression to find OpenDAP URLs within the JSON list:
		m = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+\.nc', str(allPlatforms[k]))
		# if m is not empty, loop over its contents:
		if m:
			for kk in range(len(m)):
				# limit analysis to moored stations - otherwise you get also research vessels with non-constant lon/lats, which leads to errors.
				if 'mooring' in m[kk] and 'station' in m[kk] and 'L1' in m[kk]:
					# append URL to fileList if it's a station and L1 product:
					fileList.append(m[kk])


	# append CIUTADELLA manually:
	thredds='http://thredds.socib.es/thredds/dodsC/mooring/barometer/station_ciutadella-scb_baro005/L1/'
	station_sensor = '/dep0001_station-ciutadella_scb-baro005_L1_'
	fileList = appendStationManually(fileList,startdatenum,thredds,station_sensor)

	# append GALFI manually:
	thredds='http://thredds.socib.es/thredds/dodsC/mooring/weather_station/station_galfi-scb_met005/L1/'
	station_sensor = '/dep0001_station-galfi_scb-met005_L1_'
	fileList = appendStationManually(fileList,startdatenum,thredds,station_sensor)

	return fileList

def appendStationManually(fileList,startdatenum,thredds, station_sensor):
	# append CIUTADELLA barometer by hand since DataDiscovery does not find it:

	# construct datestrings for years and months to be inserted into THREDDS url:
	year_yesterday = datetime.strftime(startdatenum-timedelta(days=1),'%Y')
	month_yesterday = datetime.strftime(startdatenum-timedelta(days=1),'%m')
	year_today = datetime.strftime(startdatenum,'%Y')
	month_today = datetime.strftime(startdatenum,'%m')
	year_tomorrow = datetime.strftime(startdatenum+timedelta(days=1),'%Y')
	month_tomorrow = datetime.strftime(startdatenum+timedelta(days=1),'%m')
	year_aftertomorrow = datetime.strftime(startdatenum+timedelta(days=2),'%Y')
	month_aftertomorrow = datetime.strftime(startdatenum+timedelta(days=2),'%m')

	# construct filenames for yesterday, today, tomorrow and the day after tomorrow:
	f_yesterday = thredds+year_yesterday+station_sensor+year_yesterday+'-'+month_yesterday+'.nc'
	f_today = thredds+year_today+station_sensor+year_today+'-'+month_today+'.nc'
	f_tomorrow = thredds+year_tomorrow+station_sensor+year_tomorrow+'-'+month_tomorrow+'.nc'
	f_aftertomorrow = thredds+year_aftertomorrow+station_sensor+year_aftertomorrow+'-'+month_aftertomorrow+'.nc'

	# loop over unique filenames - this is done to include different months(years) if neccessary, or to just add one file if
	# files from ciutadella_yesterday to ciutadella_aftertomorrow are all the same file (i.e. if we are in the middle of the month):
	for fname in np.unique([f_yesterday,f_today,f_tomorrow,f_aftertomorrow]):
		try:
			# try to open ciut_fname URL = test if OpenDAP file exists at ciut_fname URL.
			Dataset(fname)
			# append to filelist:
			fileList.append(fname)
		except:
			pass

	return fileList
