#
# Author: John Grime 2020 (Emerging Technologies, U. Oklahoma Libraries)
# Alpha test : not for redistribution without explicit permission!
#
# Class for reading and filtering TIGER/Line data, and then testing if defined
# shapes enclose a specific target point.
#
# This is useful for filtering geographical data, but be careful; full-res
# data from e.g. U.S. Census Bureau can lead to numerical issues as some
# boundary line segments are extremely small.
#
# It's best to simplify the shapes!
#
# I typically use min_dr ~= 1e-2 (approx. 100m), which preserves the basic
# boundaries while making the calculations more stable - and faster, as shapes
# are then defined using fewer points.
#
# The class requires "shapefile" from the "pyshp" module:
#
# https://pypi.org/project/pyshp/ : "pip install pyshp", or whatever.
#

import math, shapefile

class TIGERLine:
	'''
	Class to simplify TIGER/Line data and find shapes enclosing a specified
	point. Requires the "shapefile" module from "pyshp".
	'''

	def __init__(self, granularity: float = 1, ymin: float = -360.0):

		self.gran = granularity
		self.ymin = ymin

		self.shapefile = None
		self.shapes = None

		# Maps lattice y cell coord => line sections spanning that cell
		self.ly_to_linesections = {}

	def to_lattice(self, y: float):
		'''
		Convert floating point y coordinate into lattice cell coordinate
		'''

		return int((y-self.ymin)/self.gran)

	def filter(self, fields: dict, filters: dict):
		'''
		Returns False if fields[key] is not found in filters[key] for any key
		in filters, else returns True.
		'''

		for key,vals in filters.items():
			if (key in fields) and (fields[key] not in vals): return False

		return True

	def simplify_shape(self, shape_i: int, min_dr: float):
		'''
		Simplifies a shape by ensuring that consecutive points in the shape are
		separated by at least min_dr.
		'''

		shape = self.shapes[shape_i]
		parts, points = shape.parts, shape.points
		n_parts, n_points = len(parts), len(points)

		min_dr2 = min_dr*min_dr
		parts_, points_ = [], []

		# Simplify each part of the shape independently.
		for part_i in range(n_parts):

			# Start/stop indices of points representing this part of the shape
			i = parts[part_i]
			j = parts[part_i+1] if part_i<n_parts-1 else n_points

			p0 = points[i]
			parts_.append( len(points_) )
			points_.append(p0) # AFTER update of parts_

			# Note: final point in each part is just the original point again,
			# so skip final point and explicitly close polygon after the loop.
			for p in points[i+1:j-1]:
				# If current point is sufficient distance from last point ...
				dx, dy = p[0]-p0[0], p[1]-p0[1]
				if (dx*dx + dy*dy) < min_dr2: continue
				points_.append(p)
				p0 = p

			# Explicitly close part by reconnecting to the first simplified
			# point in the current part.
			i = parts_[-1]
			points_.append( (points_[i][0],points_[i][1]) )

		return parts_, points_

	def get_fields(self, shape_i: int):
		'''
		Returns the fields associated with the specified shape as a dictionary.
		'''

		# Skip leading DeletionFlag tuple to get field keys
		field_keys = [ f[0] for f in self.shapefile.fields[1:]]

		record = self.shapefile.record(shape_i)
		return { k:record[j] for j,k in enumerate(field_keys) }

	def dbg_info(self,
		tx,ty: float,
		output_prefix: str,
		intersections, bboxes: dict,
		potentials: list):

		'''
		Print some debug information. This is entirely optional, and I put it
		in a separate method so as not to clutter up the actual calculations.
		'''

		# Write box corner coords to file
		def write_box(x,y,dx,dy: float, f):
			print(f'{x} {y}', file=f)
			print(f'{x+dx} {y}', file=f)
			print(f'{x+dx} {y+dy}', file=f)
			print(f'{x} {y+dy}', file=f)
			print(f'{x} {y}', file=f)
			print('', file=f)

		# Write an 'X' shape to file, with centre at x,y
		def write_x(x,y,dx,dy: float, f):
			print(f'{x-dx} {y-dy}', file=f)
			print(f'{x+dx} {y+dy}', file=f)
			print('', file=f)
			print(f'{x-dx} {y+dy}', file=f)
			print(f'{x+dx} {y-dy}', file=f)
			print('', file=f)

		# Write line section definition and some metadata to file
		def write_linesection(shape_i,part_i,i: int, x0,y0,x1,y1: float, f):
			dx, dy = x1-x0, y1-y0
			dr = math.sqrt(dx*dx + dy*dy)
			print(f'# Line section ({shape_i}:{part_i}:{i} : dx={dx:e} dy={dy:e} dr={dr:e})', file=f)
			print(f'{x0} {y0}', file=f)
			print(f'{x1} {y1}', file=f)
			print('', file=f)

		outlines_out = open(f'{output_prefix}.outlines.txt', 'w')
		features_out = open(f'{output_prefix}.features.txt', 'w')
		potential_out = open(f'{output_prefix}.potential.txt', 'w')
		actual_out = open(f'{output_prefix}.actual.txt', 'w')

		# Print some debug information to stdout
		print()
		print(f'Point ({tx},{ty})')
		print(f'  {len(potentials)} potentially intersecting line sections')
		print(f'  {len(intersections)} potentially enclosing shapes')
		for shape_i,lst in intersections.items():
			fields = self.get_fields(shape_i)			
			name = fields['NAME'] if 'NAME' in fields else '?'

			# Even (or zero!) intersections = outside polygon.
			n = len(lst)
			what = '  OUTSIDE' if (n%2==0) else '+ INSIDE'
			print(f'    {what} shape {shape_i} ({name}, {n})')

		print()

		# Write target point location
		print(f'# Target point as "X"', file=features_out)
		write_x(tx, ty, self.gran/2, self.gran/2, features_out)

		# For all shapes that are "interesting":
		for shape_i,(x0,y0,x1,y1) in bboxes.items():

			shape = self.shapes[shape_i]
			parts, points = shape.parts, shape.points

			# Save shape outline(s)
			n_parts = len(shape.parts)
			for part_i in range(n_parts):
				i = parts[part_i]
				j = parts[part_i+1] if part_i<n_parts-1 else len(points)
				print(f'# Outline of shape.part {shape_i}.{part_i}', file=outlines_out)
				for p in points[i:j]: print(f'{p[0]} {p[1]}', file=outlines_out)
				print('', file=outlines_out)

			# Save bounding box for all potentially intersecting line sections
			print(f'# Bounding box for potential collisions in shape {shape_i}', file=features_out)
			write_box(x0,y0, x1-x0,y1-y0, features_out)

		# Save potentially intersecting line sections
		for (shape_i,part_i,i) in potentials:
			shape = self.shapes[shape_i]
			(x0, y0), (x1, y1) = shape.points[i], shape.points[i+1]
			write_linesection(shape_i,part_i,i, x0,y0,x1,y1, potential_out)

		# Save actually intersecting line sections
		for shape_i in intersections:
			shape = self.shapes[shape_i]				
			for (_,part_i,i) in intersections[shape_i]:
				(x0, y0), (x1, y1) = shape.points[i], shape.points[i+1]
				write_linesection(shape_i,part_i,i, x0,y0,x1,y1, actual_out)

		outlines_out.close()
		features_out.close()
		potential_out.close()
		actual_out.close()

	def LoadFile(self, file_path: str, filters: dict = {}, min_dr: float = 0):
		'''
		Loads a TIGER/Line shape file and generates a map of lattice y coordinates
		to a list of line sections that span the lattice cell.
		'''

		self.shapefile = shapefile.Reader(file_path)
		self.shapes = self.shapefile.shapes()

		print()
		print(f'{len(self.shapes)} shapes total. Fields:')
		for f in self.shapefile.fields: print('  ', f)
		print()

		#
		# Generate map of y lattice coordinate to line sections that span
		# that y lattice cell.
		#

		self.ly_to_linesecs = {}

		for shape_i,shape in enumerate(self.shapes):

			fields = self.get_fields(shape_i)
			name = fields['NAME'] if 'NAME' in fields else '?'

			# Filter out unwanted shapes
			if self.filter(fields, filters) == False:
				continue

			# Should we simplify the shape?
			if min_dr > 0:
				parts, points = self.simplify_shape(shape_i, min_dr)
				print(f'Shape {shape_i} ({name}): simplified {len(shape.points)} points to {len(points)}')
				shape.parts = parts
				shape.points = points

			parts, points = shape.parts, shape.points
			n_parts, n_points = len(parts), len(points)

			# Walk line sections in part, noting lattice cells spanned by each section
			for part_i in range(n_parts):

				# Start/stop indices of points in this shape part
				start = parts[part_i]
				stop = parts[part_i+1] if part_i<n_parts-1 else n_points

				# Line sections denoted by consecutive points
				for point_i in range(start,stop-1):

					pi, pj = points[point_i], points[point_i+1]

					# Get y span of line section, convert to lattice coords
					ylo, yhi = min(pi[1],pj[1]), max(pi[1],pj[1])
					ylo, yhi = self.to_lattice(ylo), self.to_lattice(yhi)

					# Add line section to list for each y lattice coord spanned.
					# Note: span range is INCLUSIVE of upper bound!
					for y in range(ylo, yhi+1):

						if y not in self.ly_to_linesecs:
							self.ly_to_linesecs[y] = []

						self.ly_to_linesecs[y].append( [shape_i,part_i,point_i] )

	def GetShapesEnclosing(self, tx: float, ty: float, debug_prefix: str = None):
		'''
		Given a target point, return the list of shapes enclosing that point.
		'''

		def dict_append(k, d, v):
			if k not in d: d[k] = []
			d[k].append(v)

		tolerance = 1e-9
		results = []

		#
		# Test if target point is in a polygon defined by line sections; we
		# look for intersections of a line projected horizontal-right from the
		# target point with the line sections that define the polygon boundary.
		# Zero or even intersection count indicates target point is outside the
		# polygon, while an odd count indicates the point is inside.
		#

		# Lattice y coordinate of lattice cell that encloses the target point
		ly = self.to_lattice(ty)

		# If no line sections span ly, target point outside all defined shapes
		if ly not in self.ly_to_linesecs: return []

		# Get line sections spanning ly
		ls_starts = self.ly_to_linesecs[ly]

		intersections = {} # shape_i => list of actual intersections
		dbg_shape_to_bb = {} # debug: shape_i => bounding box of potential collisions
		dbg_potential = []   # debug: all potential line section collisions

		for ls in ls_starts:

			shape_i, part_i, i = ls

			shape = self.shapes[shape_i]
			parts, points = shape.parts, shape.points
			(x0, y0), (x1, y1) = points[i], points[i+1]

			# Record some debug information, if needed
			if debug_prefix:

				# Update per-shape bounding box for all line sections that
				# could *potentially* collide with the test line
				minx, maxx = min(x0,x1), max(x0,x1)
				miny, maxy = min(y0,y1), max(y0,y1)

				if shape_i in dbg_shape_to_bb:
					minx_, miny_, maxx_, maxy_ = dbg_shape_to_bb[shape_i]
					minx, maxx = min(minx,minx_), max(maxx,maxx_)
					miny, maxy = min(miny,miny_), max(maxy,maxy_)

				dbg_shape_to_bb[shape_i] = (minx,miny, maxx,maxy)

				# Update list of all *potential* line section collisions
				dbg_potential.append( (shape_i,part_i,i) )

			# If target y outside line section y extents, collision impossible
			if (ty<min(y0,y1)) or (ty>max(y0,y1)): continue

			dx, dy = x1-x0, y1-y0

			# Horizontal edge; ignore.
			if abs(dy) < tolerance: continue

			# Vertical edge; just test x coordinate directly
			if abs(dx) < tolerance:
				if tx < x0:
					dict_append(shape_i, intersections, ls)
				continue

			# Projected x coord at point of intersection (from y = mx + c)
			# dx and dy (and thus, dydx) cannot be zero at this point, so no
			# divide-by-zero should occur in the following.
			dydx = dy/dx
			x_ = (ty-y0) / dydx
			x_ = x_ + x0

			# If x coord of intersection is before target point x coord, no
			# collision. Otherwise, collision with this line section!
			if x_ < tx: continue

			dict_append(shape_i, intersections, ls)

		# Even (or zero!) intersection count = outside polygon
		for shape_i,lst in intersections.items():
			if len(lst) % 2 != 0:
				results.append( (shape_i,len(lst)) )

		#
		# Print/save a bunch of debug output, if specified.
		#
		if debug_prefix:
			self.dbg_info(tx,ty, debug_prefix, intersections, dbg_shape_to_bb, dbg_potential)

		return results
