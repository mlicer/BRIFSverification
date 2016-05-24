#!/usr/bin/python

"""
The code performs basic statistics on the data obtained from performBRIFSverification.py main().
External rerequisites:
--pandas, numpy

Author: Matjaz Licer, NIB MBS @socib
matjaz.licer@mbss.org
"""

import os,sys,re,requests,json, math,pickle
from sys import exit as q
from datetime import datetime,timedelta
import numpy as np
import pandas as pd


# define class which contains fields (attributes) from fields array:
class statisticalScores(object):
	def __init__(self):
	# initialize each field (attribute) to []:
		scores = ['AIR_PRE_CORR','AIR_PRE_RMSE','AIR_PRE_BIAS','WTR_PRE_BIAS','WTR_PRE_RMSE','SLEV_RMSE','SLEV_BIAS']
		for field in scores:
			setattr(self,field,np.array([]))

def basicStatistics(strdate,sensorType,stations,wrf_t_3days,wrf_p_3days,roms):

	t_init = datetime.strptime(strdate,'%Y%m%d')

	statsOut = np.array([])

	print "\nComputing statistics..."
	for i,station in enumerate(stations):

		print "... at station: ",station.location
		# create Pandas dataframes to be used for analyses:
		romsData = pd.DataFrame(columns=['romsTimes','romsElevs'])
		wrfData = pd.DataFrame(columns=['wrfTimes','wrfPressures'])
		stationData = pd.DataFrame(columns=['stationTimes','AIR_PRE','SLEV','WTR_PRE'])

		# fill Times:
		romsData['romsTimes'] = [datetime.strptime(t,"%Y%m%d%H%M") for t in roms[i].ocean_time if datetime.strptime(t,"%Y%m%d%H%M") > t_init]
		wrfData['wrfTimes'] = [datetime.strptime(t,"%Y-%m-%d_%H:%M:00") for t in wrf_t_3days if datetime.strptime(t,"%Y-%m-%d_%H:%M:00") > t_init]
		stationData['stationTimes'] = [datetime.strptime(t,"%Y%m%d%H%M") for t in station.time if datetime.strptime(t,"%Y%m%d%H%M") > t_init]

		# fill ROMS elevations and
		# -resample in time to 1 minute resolution
		# -interpolate over NaN:
		if len(roms[i].pointSSH)>0:
			# romsE = roms[i].pointSSH
			romsE = [e for k,e in enumerate(roms[i].pointSSH) if datetime.strptime(roms[i].ocean_time[k],"%Y%m%d%H%M") > t_init]
			romsE[romsE>1e4]=np.nan
			romsData['romsElevs'] = romsE
			romsData = romsData.set_index(['romsTimes'])
			romsData = romsData.resample('Min').interpolate()

		# fill WRF pressures and
		# -resample in time to 1 minute resolution
		# -interpolate over NaN:
		wrfData['wrfPressures'] = [p for k,p in enumerate(wrf_p_3days[i,:]) if datetime.strptime(wrf_t_3days[k],"%Y-%m-%d_%H:%M:00") > t_init]
		wrfData = wrfData.set_index(['wrfTimes'])
		wrfData = wrfData.resample('Min').interpolate()

		# fill stations data and
		# -resample in time to 1 minute resolution
		# -interpolate over NaN:
		if len(station.WTR_PRE)>0:
			stationData['WTR_PRE'] = [p for k,p in enumerate(station.WTR_PRE) if datetime.strptime(station.time[k],"%Y%m%d%H%M") > t_init]
		if len(station.SLEV)>0:
			stationData['SLEV'] = [e for k,e in enumerate(station.SLEV) if datetime.strptime(station.time[k],"%Y%m%d%H%M") > t_init]
		if len(station.AIR_PRE)>0:
			stationData['AIR_PRE']=[p for k,p in enumerate(station.AIR_PRE) if datetime.strptime(station.time[k],"%Y%m%d%H%M") > t_init]

		stationData = stationData.set_index(['stationTimes'])
		stationData = stationData.resample('Min')

		# do stuff with data:
#		print station.AIR_PRE
#		print allNANs(station.AIR_PRE)
		if len(station.AIR_PRE)>0 and not allNANs(station.AIR_PRE):
#			print "A ", station.AIR_PRE
#			print "B ",allNANs(station.AIR_PRE)
			# crop stationData to wrfData and interpolate over NANs:
			stationDataWRF = stationData.reindex(wrfData.index).interpolate()
			# join both datasets:
			merged = pd.concat([stationDataWRF.interpolate(),wrfData.interpolate()],axis=1)
			# compute air pressure correlations:
			AIR_PRE_CORR = merged.corr()
			# compute BIAS, RMSE:
			AIR_PRE_BIAS, AIR_PRE_RMSE = biasRMSE(stationDataWRF['AIR_PRE'],wrfData['wrfPressures'])
			APC = AIR_PRE_CORR['AIR_PRE']['wrfPressures']
		else:
			AIR_PRE_BIAS = AIR_PRE_RMSE = APC = np.array([])

			# print "IN:",station.location,APC,AIR_PRE_RMSE,AIR_PRE_BIAS

		if len(station.WTR_PRE)>0 and not allNANs(station.WTR_PRE) and not allNANs(romsData['romsElevs']):
			# crop stationData to wrfData:
			stationDataROMS = stationData.reindex(romsData.index).interpolate()
			merged = pd.concat([stationDataROMS.interpolate(),romsData.interpolate()],axis=1)
			WTR_PRE_BIAS, WTR_PRE_RMSE = biasRMSE(removeMean(stationDataROMS['WTR_PRE']),romsData['romsElevs'])
		else:
			WTR_PRE_BIAS = WTR_PRE_RMSE = np.array([])


		if len(station.SLEV)>0  and not allNANs(station.SLEV) and not allNANs(romsData['romsElevs']):
			# crop stationData to wrfData:
			stationDataROMS = stationData.reindex(romsData.index).interpolate()
			merged = pd.concat([stationDataROMS.interpolate(),romsData.interpolate()],axis=1)
			SLEV_BIAS, SLEV_RMSE = biasRMSE(stationDataROMS['SLEV'],romsData['romsElevs'])
		else:
			SLEV_BIAS = SLEV_RMSE = np.array([])

		stats = statisticalScores()
		setattr(stats,'AIR_PRE_BIAS',AIR_PRE_BIAS)
		setattr(stats,'AIR_PRE_RMSE',AIR_PRE_RMSE)
		setattr(stats,'AIR_PRE_CORR',APC)
		setattr(stats,'WTR_PRE_BIAS',WTR_PRE_BIAS)
		setattr(stats,'WTR_PRE_RMSE',WTR_PRE_RMSE)
		setattr(stats,'SLEV_BIAS',SLEV_BIAS)
		setattr(stats,'SLEV_RMSE',SLEV_RMSE)

		statsOut = np.append(statsOut,stats)
	return statsOut

def biasRMSE(y1,y2):
	return np.nanmean([y1[i] - y2[i] for i,v in enumerate(y1)]),\
	np.sqrt(np.nanmean([(y1[i] - y2[i])**2 for i,v in enumerate(y1)]))

def allNANs(y):
	y=np.array(y)
	ynn = [yy for i,yy in enumerate(y) if not np.isnan(y[i])]
	if len(ynn)>0:
		return False
	else:
		return True

def removeMean(y):
	return y-np.nanmean(y)

if __name__=='__main__':
	main()
