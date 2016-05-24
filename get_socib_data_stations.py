#!/usr/bin/python3
import os,sys,re,requests,json
from datetime import datetime,timedelta

def removeFile(filename):
	try:
		os.remove(filename)
	except:
		pass

def printHelp():
	print("\n")
	print("Not enough input arguments! Date string yyyymmdd expected!")
	print("Example:")
	print("./get_socib_data_stations.py "+datetime.now().strftime("%Y%m%d"))
	print("\n")
	sys.exit()

def main():

	try:
		sys.argv[1]
	except:
		printHelp()

	# read start date from console:
	startdatenum = datetime.strptime(sys.argv[1],'%Y%m%d')

	# convert start date to formatted string:
	startdatestring = datetime.strftime(startdatenum,'%Y-%m-%dT000000')

	# compute end date and convert to formatted string:
	enddatestring = datetime.strftime(startdatenum+timedelta(hours=144),'%Y-%m-%dT000000')

	# construct request string:
	requestString = 'http://apps.socib.es/DataDiscovery/list-platforms?'+\
	'init_datetime='+startdatestring+'&end_datetime='+enddatestring#+\
	# '&parameter='+parameter

	# request JSON:
	r = requests.get(requestString)

	# read JSON:
	allPlatforms = r.json()

	with open('allPlatforms.json','w') as jsonf:
		jsonf.write("%s" % '[')
		for item in allPlatforms:
  			jsonf.write("%s\n" % item)
		jsonf.write("%s" % ']')
	jsonf.close()

	# initialize fileList to fill:
	fileList = []

	# loop through the list of dictionaries, looking for data:
	for k in range(len(allPlatforms)):
		if 'jsonPlatformProductList' in allPlatforms[k].keys():
			ncfile=allPlatforms[k]['jsonPlatformProductList'][0]['productsByProcessingLevel']['L1'][0]
			fileList.append(ncfile)
			print(ncfile)

	# write non-empty fileList to file:
	if fileList:
		removeFile('fileList.txt')
		with open('fileList.txt','w') as f:
			[f.write("%s\n"%(file)) for file in fileList]
		f.close()
	else:
		print("\n\n--->>> WARNING: NO STATIONS WERE FOUND FOR SPECIFIED DATE: "+startdatestring)

if __name__ == '__main__':
    main()
