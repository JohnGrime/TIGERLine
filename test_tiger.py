#
# Author: John Grime 2020 (Emerging Technologies, U. Oklahoma Libraries)
# Alpha test : not for redistribution without explicit permission!
#
# Example of using the TIGERLine class to determine which shapes in a TIGERLine
# file enclose a specified point. The class allows filtering the data using
# specific keywords in fields, and simplification of the raw shape data to
# improve performance.
#
# - The TIGERLine class requires "shapefile" from the "pyshp" module:
#
# https://pypi.org/project/pyshp/ : "pip install pyshp", or whatever.
#
# - Example usage:
#
# Assuming you have the 2019 US state shapefile (see "States (and equivalent)"
# in https://www.census.gov/cgi-bin/geo/shapefiles/index.php) downloaded into
# a subdirectory of the current directory, pass the prefix for the shapefiles
# and some other information:
#
# python3 test_tiger.py tl_2019_us_state/tl_2019_us_state -120 37 granularity=0.2 min_dr=1e-1 filters="STUSPS:CA,IL,OK,MI"
#
# - The example above specified a debug file prefix, and so we get a bunch of
# fun files to examine and plot in gnuplot, e.g.:
#
# gnuplot> plot 'debug.outlines.txt' with lines linewidth 1, 'debug.potential.txt' with lines linewidth 1.1, 'debug.actual.txt' with lines linewidth 2, 'debug.features.txt' with lines
#

import math, sys
from TIGERLine import TIGERLine

# Map keys onto values of [converter function, (default) value]
params = {
	'granularity': [float, 0.1],
	'min_dr': [float, 1e-2],
	'filters': [str, ''],
}

# Offer some guidance to the user
def print_usage(prog, pmap):
	print('Usage:')
	print('')
	print(f'python3 {prog} path_prefix longitude latitude [granularity=x] [min_dr=x] [filters="key1:val1,val2..; key2=val1,val2,...; ..."]')
	print('')
	print('Where:')
	print('')
	print('path_prefix : path to shapefile files, including prefix')
	print(f'granularity : granularity of data grid (default: {str(pmap["granularity"])})')
	print(f'min_dr : minimum distance between consecutive points in a shape (default: {str(pmap["min_dr"])})')
	print(f'filters : list of filters to apply to shapefile data (default: no filters')
	print('')
	print('Example:')
	print('')
	print('Assuming the presence of the 2019 US state data shapefile (see "States (and equivalent) in https://www.census.gov/cgi-bin/geo/shapefiles/index.php) in a subdirectory of the current directory:')
	print('')
	print('python3 {path} tl_2019_us_state/tl_2019_us_state -120 37 granularity=0.2 min_dr=1e-1 filters="STUSPS:CA,IL,OK,MI"')
	print('')
	print('This example filters the input shapes to only test the specified point against California, Illinois, Oklahoma, and Michigan.')
	print('')
	print('Notes:')
	print('')
	print('- shapefile filter keys correspond to the fields in section 3.18 of the TIGERLine documentation (https://www.census.gov/programs-surveys/geography/technical-documentation/complete-technical-documentation/tiger-geo-line.html)')
	print('')
	sys.exit(0)

#
# Get command line input:
#
# fprefix : file prefix for TIGER/Line state boundary definitions
# tp : target point, longitude (x) and latitude (y, i.e. parallel to equator)
# filters : optional state data filters (e.g. filters="x:a,b,c; y:d; z:e,f" )
#

try:
	fprefix = sys.argv[1]
	tp = [float(v) for v in sys.argv[2:4]]
	for s in sys.argv[4:]:
		toks = s.split('=')
		if len(toks) != 2: continue

		key, val = toks
		if key in params: params[key][1] = params[key][0](val)
except:
	print_usage(sys.argv[0], params)

#
# Process any optional filters
#

data_filters = {}

for entry in params['filters'][1].split(';'):
	toks = entry.split(':')
	if len(toks) != 2: continue

	key,val = toks
	data_filters[key] = val.split(',')

print()
print(f'fprefix="{fprefix}" target point={tp} data_filters={data_filters}')

#
# Load shapefile and extract individual shapes
#

granularity = params['granularity'][1]
min_dr = params['min_dr'][1]

tl = TIGERLine(granularity=granularity)
tl.LoadFile(fprefix, filters=data_filters, min_dr=min_dr)

#
# Get enclosing shapes for target point; we're using debug output here.
#

results = tl.GetShapesEnclosing(tp[0],tp[1], 'debug')

print(f'Point {tp} intersects with {len(results)} shape(s).')
for (shape_i,count) in results:
	fields = tl.get_fields(shape_i)			
	name = fields['NAME'] if 'NAME' in fields else '?'
	print(f'  {shape_i} ({name}) : {count} boundary intersections')
print()
