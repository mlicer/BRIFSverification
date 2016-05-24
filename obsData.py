#!/usr/bin/python
"""
The call

stations,sensorType = obsData(fileList,sensorType,observationFields).read()

reads available data from the list provided by getAllObservations.py, and merges
the data in time, if neccessary.

INPUT:
--fileList: a list of netCDF files provided by getAllObservations.py
--sensorType: a list of sensor types from SOCIB network, provided by getAllObservations.py
--observationFields: a list of observation fields to read from netCDFs in fileList

OUTPUT:
--stations: a list of station objects, containing data about the fields in the
	observationFields list. Merged in time if neccessary.
--sensorType: a merged list of sensorType-s for every station in the stations list

Author: Matjaz Licer, NIB MBS @socib
matjaz.licer@mbss.org
"""
import os,sys,re,requests,json
from datetime import datetime,timedelta
from netCDF4 import Dataset
import numpy as np
from sys import exit as q

# define class which contains fields (attributes) from fields array:
class station(object):
	def __init__(self,fields):
		# initialize each field (attribute) to []:
		for field in fields:
			setattr(self,field,np.array([]))

def mergeStationObjectProperties(objectToMergeFrom, objectToMergeTo):
	# loop over contents of objectToMergeFrom and append its data to objectToMergeTo
	for property in objectToMergeFrom.__dict__:
		# only merge station data, not its metadata (location,LAT,LON):
		if property not in ['location','LAT','LON']:
			setattr(objectToMergeTo, property, np.append(getattr(objectToMergeTo, property),getattr(objectToMergeFrom, property)))

	return objectToMergeTo

# define object which contains all available observation data:
class obsData(object):
	# inputs to obsData object:
	# --list of netCDF files to be read (fileList)
	# --list of sensorTypes (sensorType)
	# --list of data fields to be read from these files (fields list):
	def __init__(self,fileList,sensorType,fields):
		self.fileList = fileList
		self.fields = fields
		self.sensorType = sensorType
		# initialize obsData.sensors attribute:
		self.sensors = np.array([])

	# function (method) for netCDF reading (uses netCDF4 Dataset):
	def read(self):
		# loop over fileList:
		for ii,fname in enumerate(self.fileList):
			f = Dataset(fname)
			# fill values in currentStation object:
			currentStation = fillVals(fname,f,self.fields)
			# append currentStation object to sensors:
			self.sensors = np.append(self.sensors,currentStation)

		# if strdate is at the end of the month(year), and model run spans over two separate months (years),
		# data has to be merged from two netCDF filenames. And we need to take sensorType into account to
		# only merge data from the same sensorType:

		# initialize merged temporary arrays:
		merged = np.array([])
		mergedSensorTypes = np.array([])

		# loop over fileList:
		for ii,fname in enumerate(self.fileList):
			# if two consecutive files are found that match in sensor type and location, this means
			# they are from the same station but from two consecutive months (years), so we merge their contents:
			if ii>0 and self.sensorType[ii]==self.sensorType[ii-1] and  \
			self.sensors[ii].location == self.sensors[ii-1].location:
				merged = np.append(merged,mergeStationObjectProperties(self.sensors[ii], self.sensors[ii-1]))
				mergedSensorTypes = np.append(mergedSensorTypes,self.sensorType[ii])
			else:
				merged = np.append(merged,self.sensors[ii])
				mergedSensorTypes = np.append(mergedSensorTypes,self.sensorType[ii])

		return merged,mergedSensorTypes


def fillVals(fname,f,fields):
	# initialize an instance of class station, named currentStation:
	currentStation=station(fields)
	# extract location name from filename:
	m = re.findall(r'(\w+)_(\w+)',fname.split('/')[7])
	currentStation.location=m[0][1]

	# fill currentStation with data fields (if they exist in netCDF):
	for k,field in enumerate(fields):
		if 'time' in field:
			wrftimes = f.variables[field][:]
			t = [datetime.strptime("1970-01-01","%Y-%m-%d") + timedelta(seconds = wrftimes[x]) for x in range(len(wrftimes))]
			t = [datetime.strftime(tt,"%Y%m%d%H%M") for tt in t]

			setattr(currentStation,field,np.array(t))
		else:
			try:
				setattr(currentStation,field,np.array(f.variables[field][:]))
			except:
				pass
	return currentStation
