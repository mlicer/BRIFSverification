#!/usr/bin/python
"""
Reads WRF and ROMS netCDF files and extracts model values at observational stations locations.

The calls

wrf_date = modelData(stations,date,wrfFields,romsFields,wrfdir,romsdir).readWRF()
roms = modelData(stations,startdatenum,wrfFields,romsFields,wrfdir,romsdir).readROMS()

read available data from the WRF/ROMS netCDFs in wrfdir/romsdir.

INPUT:
--stations: a list of station objects, containing data about the fields in the
	observationFields list.
--date: datenumber for yesterday, today or tomorrow. (toiday being strdate)
--wrfFields: a list of fields to fill from WRF netCDFs
--romsFields: a list of fields to fill from ROMS netCDFs
--wrfdir: directory with WRF netCDFs
--romsdir: directory with ROMS netCDFs

OUTPUT:
wrf_date/roms: stations-long list of modelData objects containing data about the
wrfFields or romsFields.

Author: Matjaz Licer, NIB MBS @socib
matjaz.licer@mbss.org
"""

import os,sys,re,requests,json
from datetime import datetime,timedelta
from netCDF4 import Dataset
import numpy as np
from sys import exit as q

class modelAtSensorLocation(object):
	def __init__(self,fields):
		# initialize each field (attribute) to []:
		for field in fields:
			setattr(self,field,np.array([]))

def findStationIndexInGrid(stationLon,stationLat,longrid2d,latgrid2d):
	a = abs(longrid2d-stationLon)+abs(latgrid2d-stationLat)
	return np.argmin(a,0)[0],np.argmin(a,1)[0]

# define class which contains fields (attributes) from fields array:
class modelData(object):
	def __init__(self,stations,startdatenum,wrfFields,romsFields,wrfdir,romsdir, operMode):
		self.stations = stations
		self.startdatenum = startdatenum
		self.wrfFields = wrfFields
		self.romsFields = romsFields
		self.wrfdir = wrfdir
		self.romsdir =  romsdir
		self.WRFatSensorLocation = modelAtSensorLocation(self.wrfFields)
		self.WRFall = np.array([])
		self.ROMSatSensorLocation = np.array([])

		self.wrfdatestring = datetime.strftime(self.startdatenum,'%Y-%m-%d_12:00:00')
		self.romsdatestring = datetime.strftime(self.startdatenum,'%Y%m%d')

		self.wrf_file = self.wrfdir+'wrfout_d02_'+self.wrfdatestring

		if operMode=='oper':
			self.roms_parent_file = self.romsdir+'roms_BRIFS_parent_'+self.romsdatestring+'_op_his.nc'
			self.roms_child_file = self.romsdir+'roms_BRIFS_child_'+self.romsdatestring+'_op_his.nc'
		else:
			self.roms_parent_file = self.romsdir+'roms_BRIFS_parent_'+self.romsdatestring+'_hind_his.nc'
			self.roms_child_file = self.romsdir+'roms_BRIFS_child_'+self.romsdatestring+'_hind_his.nc'

	def readWRF(self):
		# WRF reader
		# loop over three days of netCDF results:
		locations=np.array([])
		f = Dataset(self.wrf_file)

		print "\nReading WRF for date: ",self.wrfdatestring," ..."

		# read WRF file:
		wrflon3d = f.variables['XLONG'][:]
		wrflat3d = f.variables['XLAT'][:]
		HGT = f.variables['HGT'][:]
		T2 = f.variables['T2'][:]
		Q2 = f.variables['Q2'][:]
		PSFC = f.variables['PSFC'][:]

		# find grid indices of station locations in WRF grid:
		for station in self.stations:
			# print "Reading WRF file: "+self.wrf_file
			print "Extracting WRF at location: ",station.location
			currentWRF = modelAtSensorLocation(self.wrfFields)

			# loop over the fields that are supposed to be read:
			for field in self.wrfFields:

				# some fields are not in the netCDF but we need them for the verification,
				# so we try to read the netCDF and pass if it doesn't work out. If the field
				# can be read from netCDF, we append it to the currentWRF:
				try:
					if 'Times' in field:
						t = ["".join(f.variables[field][k]) for k in range(len(f.variables[field][:]))]
						setattr(currentWRF,field,np.append(getattr(currentWRF, field),t))
					elif 'XLONG' in field or 'XLAT' in field:
						setattr(currentWRF,field,np.array(f.variables[field][0,:,:]))
					else:
						setattr(currentWRF,field,np.append(getattr(currentWRF, field),np.array(f.variables[field][:])))
				except:
					pass

			# append station location to currentWRF:
			currentWRF.location = np.append(currentWRF.location,station.location)
			# find indices of station location in WRF grid:
			i_station,j_station = findStationIndexInGrid(station.LON,station.LAT,wrflon3d[0,:,:],wrflat3d[0,:,:])
			# write station's lat,lon position to currentWRF
			currentWRF.pointLon  = np.append(currentWRF.pointLon,i_station)
			currentWRF.pointLat = np.append(currentWRF.pointLat,j_station)

			# compute mean sea level pressure at this point
			currentWRF.pointMSLP=np.append(currentWRF.pointMSLP,\
			np.array(1.e-2 * PSFC[:,i_station,j_station]*np.exp(9.81*HGT[:,i_station,j_station]/(287*T2[:,i_station,j_station]*(1+0.61*Q2[:,i_station,j_station])))))

			# compute mean sea level pressure at this point
			currentWRF.pointPSFC=np.append(currentWRF.pointPSFC,np.array(1.e-2 * PSFC[:,i_station,j_station]))

			# append current station to all stations:
			self.WRFall = np.append(self.WRFall,currentWRF)

		return self.WRFall

	def readROMS(self):

		### ROMS----------------
		# open netCDF:
		f_parent = Dataset(self.roms_parent_file)
		f_child = Dataset(self.roms_child_file)

		# read grid:
		print ""
		print "Reading ROMS parent..."

		roms_parent_lon = f_parent.variables['lon_rho'][:]
		roms_parent_lat = f_parent.variables['lat_rho'][:]
		roms_parent_mask = f_parent.variables['mask_rho'][:]
		roms_parent_zeta = f_parent.variables['zeta'][:]

		# set boundaries:
		roms_parent_lonmin = np.amin(np.amin(roms_parent_lon))
		roms_parent_lonmax = np.amax(np.amax(roms_parent_lon))
		roms_parent_latmin = np.amin(np.amin(roms_parent_lat))
		roms_parent_latmax = np.amax(np.amax(roms_parent_lat))

		# determine if child ROMS needs to be read:
		ciutadellaDataExists=False

		for station in self.stations:
			if 'ciutadella' in station.location:
				ciutadellaDataExists=True

		# if yes, read it:
		if ciutadellaDataExists:
			print "Reading ROMS child..."
			roms_child_lon = f_child.variables['lon_rho'][:]
			roms_child_lat = f_child.variables['lat_rho'][:]
			roms_child_mask = f_child.variables['mask_rho'][:]
			roms_child_zeta = f_child.variables['zeta'][:]

		# loop over all stations:
		for k in range(self.stations.size):
			# initialize object that contains ROMS values at sensor locations:
			currentROMS = modelAtSensorLocation(self.romsFields)
			currentROMS.location = np.append(currentROMS.location,self.stations[k].location)
			print "Extracting ROMS at location: ",currentROMS.location[0]

			# if we read ciutadella data, we read ROMS_child, else we read ROMS_parent:
			if 'ciutadella' not in currentROMS.location:
				# we loop over fields to be filled:
				for field in self.romsFields:
					# if they are contained in the netCDF, fill them:
					try:
						if 'ocean_time' in field:
							t = [datetime.strptime("1968-05-23","%Y-%m-%d") + timedelta(seconds = f_parent.variables[field][x]) for x in range(len(f_parent.variables[field][:]))]
							t = [datetime.strftime(tt,"%Y%m%d%H%M") for tt in t]
							setattr(currentROMS,field,t)
						else:
							setattr(currentROMS,field,np.array(f_parent.variables[field][:]))
					# if they are not contained in the netCDF, they will be filled manually, so just pass.
					except:
						pass
			else: # we read ROMS_child:
				for field in self.romsFields:
					try:
						if 'ocean_time' in field:
							t = [datetime.strptime("1968-05-23","%Y-%m-%d") + timedelta(seconds = f_child.variables[field][x]) for x in range(len(f_child.variables[field][:]))]
							t = [datetime.strftime(tt,"%Y%m%d%H%M") for tt in t]
							setattr(currentROMS,field,t)
						else:
							setattr(currentROMS,field,np.array(f_child.variables[field][:]))
					except:
						pass
			#
			# if not ciutadella, work with ROMS_parent
			if 'ciutadella' not in currentROMS.location:
				# we find station's location in ROMS grid:
				i_station,j_station = findStationIndexInGrid(self.stations[k].LON,self.stations[k].LAT,roms_parent_lon,roms_parent_lat)
				# if it is inside the ROMS domain, append its lons/lats to the currentROMS, otherwise ignore.
				if i_station > 0 and i_station < len(roms_parent_lon[1,:]) and\
				j_station > 0 and j_station < len(roms_parent_lat[:,1]):
					currentROMS.pointLon  = np.append(currentROMS.pointLon,i_station)
					currentROMS.pointLat = np.append(currentROMS.pointLat,j_station)
					currentROMS.pointSSH = np.append(currentROMS.pointSSH, np.array(roms_parent_zeta[:,i_station,j_station]))
			else: # if ciutadella, work with ROMS_child:
				i_station,j_station = findStationIndexInGrid(self.stations[k].LON,self.stations[k].LAT,roms_child_lon,roms_child_lat)
				currentROMS.pointLon  = np.append(currentROMS.pointLon,i_station)
				currentROMS.pointLat = np.append(currentROMS.pointLat,j_station)
				currentROMS.pointSSH = np.append(currentROMS.pointSSH, np.array(roms_child_zeta[:,i_station,j_station]))

			# append currentROMS and return:
			self.ROMSatSensorLocation = np.append(self.ROMSatSensorLocation,currentROMS)

		return self.ROMSatSensorLocation
