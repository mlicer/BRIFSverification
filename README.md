# BRIFSverification

Author: Matjaz Licer, matjaz.licer@nib.si

This is documentation for BRIFS system verification Python tools, running at SOCIB SCBD067 computer at IMEDEA, Mallorca. These tools allow us to operationaly (daily) compare BRIFS system outputs with all available in situ data from SOCIB observational network and plot high-quality images of comparisons.

External prerequisites:

--HDF5 and netCDF C libraries, built with shared and OpenDAP support.

--numpy, scipy, matplotlib, netCDF4, pandas for Python2.7


INPUT: YYYYMMDD string of the date of verification and oper/hind mode, for example:

./performBRIFSverification.py 20160331 oper

./performBRIFSverification.py 20160331 hind

See BRIFSverificationCodes.pdf for further information. 

