#!/usr/bin/python

"""
The code plots the data obtained from performBRIFSverification.py main().

Author: Matjaz Licer, NIB MBS @socib
matjaz.licer@mbss.org
"""

import os,sys,re,requests,json, math
from datetime import datetime,timedelta
from matplotlib.cbook import get_sample_data
import matplotlib.pyplot as plt
import matplotlib.colors as col
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import matplotlib.colors as col
from matplotlib.ticker import FuncFormatter
import matplotlib.cm as cm
from matplotlib.dates import YearLocator, MonthLocator, DateFormatter
import numpy as np
import pandas,pickle
from sys import exit as q
from scipy.signal import butter, lfilter,firwin
from scipy.signal import ellip,filtfilt
from matplotlib import rc,rcParams

# Charles' filter:
def filter_timeseries(pressure):
	# For the filter, it is necessary to set:
	#  * the cutoff frequency,
	#  * the filter length,
	#  * the window applied to the filter
	n1 = 128  # filter length
	windowsname = 'blackman'  # windows name
	sample_rate = 1 / 60.0  # one data per minute
	nyq_rate = sample_rate / 2.0  # Nyquist rate
	frqcut = 1.0 / (2000 * 3600.)  # cutoff frequency
	cutoff = frqcut / nyq_rate  # Cutoff relative to Nyquist rate
	taps1 = firwin(n1, cutoff=cutoff, window=(windowsname))
	pressure_filtered = lfilter(taps1, 1.0, pressure)
	delay = 0.5 * (n1 - 1) / sample_rate
	return pressure-pressure_filtered, delay, n1

# Butterworth bandpass filter:
def butter_bandpass(lowcut, highcut, fs, order):
	nyq = 0.5 * fs # Nyquist rate
	low = lowcut / nyq # Low end cutoff relative to Nyquist rate
	high = highcut / nyq # High end cutoff relative to Nyquist rate
	b, a = butter(order, [low, high], btype='band')
	return b, a


def butter_bandpass_filter(data, lowcut, highcut, fs, order):
	b, a = butter_bandpass(lowcut, highcut, fs, order=order)
	y = lfilter(b, a, data)
	return y

# formatter for pressure ticks on figures:
def air_pressure_fmt(y,pos):
	'The two args are the value and tick position'
	return '%5.0f' % (y)

# find out if array is all NaNs:
def allNaNs(y):
	y=np.array(y)
	allnan =True
	for i in range(len(y)):
		if not np.isnan(y[i]):
			allnan = False
	return allnan


def nan_helper(y):
	"""Helper to handle indices and logical indices of NaNs.

	Input:
		- y, 1d numpy array with possible NaNs
	Output:
		- nans, logical indices of NaNs
		- index, a function, with signature indices= index(logical_indices),
		  to convert logical indices of NaNs to 'equivalent' indices
	Example:
		>>> # linear interpolation of NaNs
		>>> nans, x= nan_helper(y)
		>>> y[nans]= np.interp(x(nans), x(~nans), y[~nans])
	"""
	y=np.array(y)
	return np.isnan(y), lambda z: z.nonzero()[0]

def naninterp(y):
	y = np.array(y)
	# find NaN locations:
	nans,x = nan_helper(y)
	# interpolate over NaNs:
	y[nans]= np.interp(x(nans), x(~nans), y[~nans])
	return y,nans

def plotBRIFS(strdate,sensorType,stations,wrf_t_3days,wrf_p_3days,roms,stats):
# plotting main subroutine:

	rcParams['font.family'] = 'serif'
	rcParams['font.serif'] = ['Times New Roman']
	rotationAngle=30
	obsColor = 'orangered'
	modelColor = 'steelblue'
	modelColor = 'navy'
	# SOCIB logo [left,bottom,hsize,vsize] in figure percent:
	# socibLogoLocationSize = [0.74, 0.11, 0.15, 0.15]
	socibLogoLocationSize = [0.0, 0.925, 0.1, 0.1]
	t_init = datetime.strptime(strdate,'%Y%m%d')
	title_datestring = datetime.strftime(t_init,'%Y %m %d')

	print ""
	print "Plotting graphs..."

	# loop over stations:
	for k in range(len(stations)):
		print "... at station: ",stations[k].location,':',stations[k].time[0],stations[k].time[-1],sensorType[k]

		# if not empty and if ok data (check QC flag), plot:
		if len(stations[k].SLEV)>1 and np.any(np.where(stations[k].QC_SLEV<4,1,0)) and np.any(np.where(roms[k].pointSSH<1000.,1,0)):
			# convert strings to datetime objects:
			stationTimes = [datetime.strptime(t,"%Y%m%d%H%M") for t in stations[k].time]
			romsTimes = [datetime.strptime(t,"%Y%m%d%H%M") for t in roms[k].ocean_time]

			# exclude missing values from current location SSH timeseries:
			idx = [i for i,SSH in enumerate(roms[k].pointSSH) if SSH < 1000.]
			romsT = [romsTimes[i] for i in idx]
			romsSSH = [roms[k].pointSSH[i] for i in idx]

			# plot if values are not missing:
			if len(idx)>1 and isinstance(stats[k].SLEV_RMSE,float) and isinstance(stats[k].SLEV_BIAS,float):
				# setup for high-pass filter:
				samplingFrequency = 1/((stationTimes[1]-stationTimes[0]).total_seconds())
				lowCutoff = 0.02
				hiCutoff = 8
				order = 3
				# filter observations:

				# before we perform any filtering, we need to interpolate over NaNs:
				slevHF,nans=naninterp(stations[k].SLEV)

				# apply high pass filter:
				slevHF = butter_bandpass_filter(slevHF-np.nanmean(slevHF), samplingFrequency, lowCutoff,hiCutoff, order)
				# filter ROMS:
				romsHF = butter_bandpass_filter(romsSSH, samplingFrequency, lowCutoff,hiCutoff, order)

				tHF = stationTimes

				fig = plt.figure(1)
				plt.xticks(rotation=rotationAngle, ha='right')
				# plt.plot(stationTimes,stations[k].SLEV,'g')
				plt.plot(tHF,slevHF,color=obsColor,label='OBS')
				# plt.plot(tHF,stations[k].SLEV-slevHF,'k')
				plt.plot(romsT,romsHF,color=modelColor,label='ROMS')
				plt.legend(loc='lower left')
				titleString = "High-pass filtered sea levels [m] at station %s\n Date: %s \n SLEV-ROMS BIAS: %5.2f m; SLEV-ROMS RMSE: %5.2f m." \
				% (stations[k].location.upper(),title_datestring,stats[k].SLEV_BIAS,stats[k].SLEV_RMSE)
				plt.title(titleString)
				plt.ylabel('Sea level [m]',rotation=0, ha='right')
				days = DateFormatter('%d %b %H:%M')
				hours = DateFormatter('%H')
				plt.gcf().axes[0].xaxis.set_major_formatter(days)
				plt.gcf().axes[0].xaxis.set_minor_formatter(hours)
				plt.xlim( t_init, romsT[-1] )
				plt.ylim( -0.6, 0.6 )
				plt.grid()

				# insert SOCIB logo:
				im = plt.imread(get_sample_data(('/home/mlicer/latex/logo-Socib_HR.png')))
				newax = fig.add_axes(socibLogoLocationSize, anchor='NE',zorder=10)
				newax.imshow(im)
				newax.axis('off')
				pngname = 'SLEV_'+stations[k].location+'_'+sensorType[k]+'_'+strdate+'.png'
				pngname = pngname.replace('__','_')
				fig.savefig(pngname, bbox_inches='tight')
				plt.close()


		#if stations[k].location=='galfi':

			#print len(stations[k].AIR_PRE),np.any(np.where(stations[k].QC_AIR_PRE<4,1,0)),isinstance(stats[k].AIR_PRE_CORR,float),isinstance(stats[k].AIR_PRE_RMSE,float),isinstance(stats[k].AIR_PRE_BIAS,float)

		if len(stations[k].AIR_PRE)>1 and np.any(np.where(stations[k].QC_AIR_PRE<4,1,0)) and \
			isinstance(stats[k].AIR_PRE_CORR,float) and isinstance(stats[k].AIR_PRE_RMSE,float) and isinstance(stats[k].AIR_PRE_BIAS,float):
			stationTimes = [datetime.strptime(t,"%Y%m%d%H%M") for t in stations[k].time]
			wrfTimes = [datetime.strptime(t,"%Y-%m-%d_%H:%M:00") for t in wrf_t_3days]

			idx = [i for i,p in enumerate(stationTimes) if stationTimes[i]>wrfTimes[0] and stationTimes[i]<wrfTimes[-1]]

			pmin = np.amin(wrf_p_3days[k,:])-3
			pmax = np.amax(wrf_p_3days[k,:])+3

			pressure_formatter = FuncFormatter(air_pressure_fmt)

			fig = plt.figure(1)
			plt.xticks(rotation=rotationAngle, ha='right')
			plt.plot(stationTimes,stations[k].AIR_PRE,color=obsColor,label='OBS')
			plt.plot(wrfTimes,wrf_p_3days[k,:],color=modelColor,label='WRF')
			plt.legend(loc='lower left')
			titleString = "Air pressure [hPa] at station %s\n Date: %s \n OBS-WRF BIAS: %5.2f hPa; OBS-WRF RMSE: %5.2f hPa;\n OBS-WRF CORR: %5.2f." \
			% (stations[k].location.upper(),title_datestring,stats[k].AIR_PRE_BIAS,stats[k].AIR_PRE_RMSE,stats[k].AIR_PRE_CORR)
			plt.title(titleString)
			plt.ylabel('Air pressure [hPa]',rotation=0, ha='right')
			days = DateFormatter('%d %b %H:%M')
			hours = DateFormatter('%H')
			plt.gcf().axes[0].xaxis.set_major_formatter(days)
			plt.gcf().axes[0].xaxis.set_minor_formatter(hours)
			plt.gcf().axes[0].yaxis.set_major_formatter(pressure_formatter)
			plt.xlim( t_init, wrfTimes[-1] )
			plt.ylim( pmin,pmax)
			plt.grid()

			# insert SOCIB logo:
			im = plt.imread(get_sample_data(('/home/mlicer/latex/logo-Socib_HR.png')))
			newax = fig.add_axes(socibLogoLocationSize, anchor='NE',zorder=10)
			newax.imshow(im)
			newax.axis('off')
			pngname = 'AIR_PRE_'+stations[k].location+'_'+sensorType[k]+'_'+strdate+'.png'
			pngname = pngname.replace('__','_')
			fig.savefig(pngname, bbox_inches='tight')
			plt.close()
		#
		if len(stations[k].WTR_PRE)>1 and np.any(np.where(stations[k].QC_WTR_PRE<4,1,0)) \
			and isinstance(stats[k].WTR_PRE_RMSE,float) and isinstance(stats[k].WTR_PRE_BIAS,float):

			stationTimes = [datetime.strptime(t,"%Y%m%d%H%M") for t in stations[k].time]
			romsTimes = [datetime.strptime(t,"%Y%m%d%H%M") for t in roms[k].ocean_time]

			idx = [i for i,SSH in enumerate(roms[k].pointSSH) if SSH < 1000.]
			romsT = [romsTimes[i] for i in idx]
			romsSSH = [roms[k].pointSSH[i] for i in idx]


			if len(idx)>1:
				samplingFrequency = 1/((stationTimes[1]-stationTimes[0]).total_seconds())
				lowCutoff = 3 # ( * samplingFrequency / 2)
				hiCutoff = 8 # ( * samplingFrequency / 2)
				order=2

				# before we perform any filtering, we need to interpolate over NaNs:
				slevHF,nans = naninterp(stations[k].WTR_PRE)

				# apply high pass filter:
				slevHF = butter_bandpass_filter(slevHF-np.nanmean(slevHF), samplingFrequency, lowCutoff,hiCutoff, order)
				romsHF = butter_bandpass_filter(romsSSH, samplingFrequency, lowCutoff,hiCutoff, order)

				tHF = stationTimes#[tt for i,tt in enumerate(stationTimes) if i not in nans] #[tt - timedelta(seconds=delay) for tt in stationTimes]
				#slevHF = [el for i,el in enumerate(slevHF) if i not in nans]

				fig = plt.figure(1)
				plt.xticks(rotation=rotationAngle, ha='right')
				# plt.plot(stationTimes,stations[k].SLEV,'g')
				plt.plot(tHF,slevHF,color=obsColor,label='OBS')
				# plt.plot(tHF,stations[k].SLEV-slevHF,'k')
				plt.plot(romsT,romsHF,color=modelColor,label='ROMS')
				plt.legend(loc='lower left')
				titleString = "High-pass filtered sea levels [m] at station %s\n Date: %s \n SLEV-ROMS BIAS: %5.2f m; SLEV-ROMS RMSE: %5.2f m." \
				% (stations[k].location.upper(),title_datestring,stats[k].WTR_PRE_BIAS,stats[k].WTR_PRE_RMSE)
				plt.title(titleString)
				plt.ylabel('Sea level [m]',rotation=0, ha='right')
				days = DateFormatter('%d %b %H:%M')
				hours = DateFormatter('%H')
				plt.gcf().axes[0].xaxis.set_major_formatter(days)
				plt.gcf().axes[0].xaxis.set_minor_formatter(hours)
				plt.xlim( t_init, romsT[-1] )
				plt.ylim( -0.6, 0.6 )
				plt.grid()

			# insert SOCIB logo:
				im = plt.imread(get_sample_data(('/home/mlicer/latex/logo-Socib_HR.png')))
				newax = fig.add_axes(socibLogoLocationSize, anchor='NE',zorder=10)
				newax.imshow(im)
				newax.axis('off')
				pngname = 'SLEV_'+stations[k].location+'_'+sensorType[k]+'_'+strdate+'.png'
				pngname = pngname.replace('__','_')
				fig.savefig(pngname, bbox_inches='tight')
				plt.close()


if __name__=='__main__':
	main()
