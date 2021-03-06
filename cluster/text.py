
import utils
import itertools
import collections
import Levenshtein
from constants import *


class TextLineMatcher:

	PERFECT = 0
	PARTIAL1 = 1  # line1 matches two lines in lines2
	PARTIAL2 = 2  # line2 matches two lines in lines1
	SUFFIX1 = 3   # line1 is a suffix of line2
	SUFFIX2 = 4   # line2 is a suffix of line1
	PREFIX1 = 5   # line1 is a prefix of line2
	PREFIX2 = 6   # line2 is a prefix of line1
	# prefixes and suffixes are condensed into Partials if they can

	OP_STR = {PERFECT: "Perfect", PARTIAL1: "Partial1", PARTIAL2: "Partial2", SUFFIX1: "Suffix1",
				SUFFIX2: "Suffix2", PREFIX1: "Prefix1", PREFIX2: "Prefix2"}

	
	def __init__(self, lines1, lines2, dist_thresh, partials=False):
		'''
		:param lines1: lines of TextLines
		:param lines2: lines of TextLines
		:param dist_thresh: num distance threshold
		:param partials: bool whether to use partial matches or not
		'''
		self.lines1 = lines1
		self.lines2 = lines2
		self.dist_thresh = dist_thresh
		self.dist_thresh_sqr = dist_thresh * dist_thresh
		self.do_partial_matches = partials
		self.matches = None

	def op_str(self, op):
		return self.OP_STR.get(op)
	
	def similarity(self):
		''' :return: 0-1 similarity score between the two text lines '''
		self.get_matches()  # make sure that lines get matched
		total_val = 0.0
		matched_val = 0.0
		for line, matched in zip(itertools.chain(self.first.lines, self.second.lines), 
				itertools.chain(self.first_matches, self.second_matches)):
			total_val += line.match_value()
			if matched:
				matched_val += line.match_value()
		return matched_val / total_val if total_val else 0.5

	def _clear_matches(self):
		''' Marks all lines as not matched '''
		self.first_matches = [False] * len(self.lines1)
		self.second_matches = [False] * len(self.lines2)

	def _find_perfect_matches(self):
		self._clear_matches()
		perfect_matches = list()
		for idx1, line1 in enumerate(self.lines1):
			for idx2, line2 in enumerate(self.lines2):
				if self.second_matches[idx2]:
					continue
				match = self.perfect_match(line1, line2)
				if match:
					perfect_matches.append( (self.PERFECT, line1, line2) )
					self.first_matches[idx1] = True
					self.second_matches[idx2] = True
					break
		return perfect_matches

	def perfect_match(self, line1, line2):
		'''
		A Perfect match is defined to be two lines whose start positions are within
			the distance threshold, whose sizes are similar, and whose normalized
			edit distance is below some threshold
		:param line1: TextLine
		:param line2: TextLine
		:return: bool
		'''
		#if (utils.e_dist_sqr(line1.pos, line2.pos) > self.dist_thresh_sqr and
		#	utils.e_dist_sqr(line1.end_pos, line2.end_pos( > self.dist_thresh_sqr):	
			
		#if not (utils.ratio(line1.size[0], line2.size[0]) > self.SIZE_RATIO and
		#	utils.ratio(line1.size[1], line2.size[1]) > self.SIZE_RATIO):
		#	return False

		# optimization using diff in length as a lower bound on edit distance
		if (utils.e_dist_sqr(line1.pos, line2.pos) > self.dist_thresh_sqr or 
			utils.ratio(line1.N, line2.N) < (1 - TEXT_EDIT_DIST_THRESH)):
			return False

		# check equality before heavy calculation
		edit_dist = Levenshtein.distance(line1.text, line2.text) if line1.text != line2.text else 0
		norm = edit_dist / float(max(line1.N, line2.N))
		return edit_dist <= 1 or norm <= TEXT_EDIT_DIST_THRESH

	def suffix_match(self, suffix, complete):
		'''
		A Suffix match is defined to be two lines whose end positions are within
			the distance threshold, the average character width is within
			a threshold and the edit distance between the suffix and the truncated
			other string is below a threshold.
		:param suffix: TextLine that might be the suffix of complete
		:param complete: TextLine that might contain suffix
		:return: bool Whether suffix is a suffix of complete or not
		'''
		if complete.N <= suffix.N or utils.e_dist_sqr(complete.end_pos, suffix.end_pos) > self.dist_thresh_sqr:
			return False

		#if not utils.ratio(complete.char_width(), suffix.char_width()) > self.SIZE_RATIO:
		#	return False

		edit_dist = Levenshtein.distance(complete.text[-1*suffix.N:], suffix.text)
		norm = edit_dist / float(suffix.N)
		return edit_dist <= 1 or norm <= TEXT_EDIT_DIST_THRESH

	def prefix_match(self, prefix, complete):
		''' Same as suffix match, except with a prefix '''
		if complete.N <= prefix.N or utils.e_dist_sqr(complete.pos, prefix.pos) > self.dist_thresh_sqr:
			return False

		#if not utils.ratio(complete.char_width(), prefix.char_width()) > self.SIZE_RATIO:
		#	return False

		edit_dist = Levenshtein.distance(complete.text[:prefix.N], prefix.text)
		norm = edit_dist / float(prefix.N)
		return edit_dist <= 1 or norm <= TEXT_EDIT_DIST_THRESH

	def _find_partial_matches(self):
		''' Finds Prefix/Suffix matches among the unmatched lines '''
		partial_matches = list()
		for idx1, line1 in enumerate(self.lines1):
			if self.first_matches[idx1]:
				continue
			for idx2, line2 in enumerate(self.lines2):
				if self.second_matches[idx2]:
					continue
				if self.prefix_match(line1, line2):
					partial_matches.append( (self.PREFIX1, line1, line2) )
				if self.prefix_match(line2, line1):
					partial_matches.append( (self.PREFIX2, line1, line2) )
				if self.suffix_match(line1, line2):
					partial_matches.append( (self.SUFFIX1, line1, line2) )
				if self.suffix_match(line2, line1):
					partial_matches.append( (self.SUFFIX2, line1, line2) )
		return partial_matches

	def _condense_matches(self, partials):
		''' :param partials: list of tuples - (type, line1, line2) '''
		condensed = list()
		# mapping of complete lines to the possible partials in the other list
		# one_two[complete_line] == list(prefix1, prefix2, ..., suffix1, suffix2, ...)
		one_two = collections.defaultdict(list)
		two_one = collections.defaultdict(list)
		for part in partials:
			op, line1, line2 = part
			if op in [self.PREFIX2, self.SUFFIX2]:
				one_two[line1].append((op, line2))
			if op in [self.PREFIX1, self.SUFFIX1]:
				two_one[line2].append((op, line1))

		# TODO: disambiguating multiple prefixes/suffixes
		for line1, matches in one_two.iteritems():
			prefix = suffix = None
			for match in matches:
				op, line = match
				if op == self.PREFIX2:
					prefix = line
				if op == self.SUFFIX2:
					suffix = line
			if prefix is None or suffix is None:
				continue
			l = prefix.N + suffix.N
			if utils.ratio(l, line1.N) > (1 - TEXT_EDIT_DIST_THRESH):
				# we have an actual partial match
				condensed.append( (self.PARTIAL1, line1, prefix, suffix,
									self._norm_edit_dist(line1.text, prefix.text + suffix.text)) )

		for line2, matches in two_one.iteritems():
			prefix = suffix = None
			for match in matches:
				op, line = match
				if op == self.PREFIX1:
					prefix = line
				if op == self.SUFFIX1:
					suffix = line
			if prefix is None or suffix is None:
				continue
			l = prefix.N + suffix.N
			if utils.ratio(l, line2.N) > (1 - TEXT_EDIT_DIST_THRESH):
				# we have an actual partial match
				condensed.append( (self.PARTIAL2, line2, prefix, suffix,
									self._norm_edit_dist(line2.text, prefix.text + suffix.text)) )
		return condensed

	def get_matches(self):
		''' :return: list of tuples (op, line1, line2) '''
		if self.matches is None:
			matches = self._find_perfect_matches()
			if self.do_partial_matches:
				partials = self._find_partial_matches()
				condensed = self._condense_matches(partials)
				# mark the matches
				for match in condensed:
					for line in match[1:-1]:
						#line.matched = True
						if line in self.lines1:
							idx1 = self.lines1.index(line)
							self.first_matches[idx1]
						else:
							idx2 = self.lines2.index(line)
							self.second_matches[idx2]
				matches += condensed
			self.matches = matches
			
		return self.matches

	def similarity_by_region(self, rows, cols, size):
		'''
		:param rows: int number of rows
		:param cols: int number of cols
		:param size: (int, int) size of image1
		:return: list(list(float(0-1))) matrix of regional percentage matches
		'''
		self.get_matches()
		#print "sim_mat(rows=%d, cols=%d, size=%s)" % (rows, cols, size)
		width = (size[0] / cols) + 1
		height = (size[1] / rows) + 1
		#print "\twidth:", width
		#print "\theight:", height
		total_mat = [([0] * cols) for r in xrange(rows)]
		matched_mat = [([0] * cols) for r in xrange(rows)]
		total = 0
		for idx1, line in enumerate(self.lines1):
			br = line.bottom_right()
			#print "\t", line
			#print "\tul: %s\t br: %s" % (line.pos, br)
			regions = self._get_regions(line, width, height)
			#print regions
			for r, c, val in regions:
				if r >= rows or c >= cols or r < 0 or c < 0:
					continue
				#print r, c, val
				if self.first_matches[idx1]:
					matched_mat[r][c] += val
				#else:
				#	print r, c, val, line
				total_mat[r][c] += val
				total += val
		perc_mat = [([0] * cols) for r in xrange(rows)]
		weight_mat = [([0] * cols) for r in xrange(rows)]
		for r in xrange(rows):
			for c in xrange(cols):
				perc_mat[r][c] = matched_mat[r][c] / total_mat[r][c] if total_mat[r][c] else 0 #float('NaN')
				weight_mat[r][c] = total_mat[r][c] / total if total else (1.0 / rows * cols)
		return perc_mat, weight_mat

	def _get_regions(self, line, width, height):
		line_area = float(line.size[0] * line.size[1])
		if line_area == 0:
			return list()
		line_value = line.match_value()
		#print line
		#print "\tarea: %.0f \tvalue: %d" % (line_area, line_value)
		ul = line.pos
		br = line.bottom_right()
		row1, col1 = self._get_region(ul, width, height)
		row2, col2 = self._get_region(br, width, height)
		#print "\t%s\t%s" % ( (row1, col1), (row2, col2) )
		regions = list()
		for row in xrange(row1, row2 + 1):
			for col in xrange(col1, col2 + 1):
				x = ul[0] if col == col1 else col * width
				y = ul[1] if row == row1 else row * height
				#print "\t", row, col, (x, y)
				overlap = self._get_region_overlap( (x, y), br, width, height)
				#print "\t", overlap
				regions.append( (row, col, line_value * (overlap / line_area)) )
		return regions

	def _get_region(self, pos, width, height):
		row = int(pos[1]) / height
		col = int(pos[0]) / width
		return (row, col)

	def _get_region_overlap(self, pos1, pos2, width, height):
		'''
		:param pos1: (x, y) upper left corner of rect
		:param pos2: (x, y) bottom right corner of rect
		:param width: width of tesselating rectangular regions
		:param height: height of tesselating rectangular regions
		return the overlap area of the region contain pos1 with rectangle (pos1, pos2)
		'''
		w = min(width - (pos1[0] % width), pos2[0] - pos1[0])
		h = min(height - (pos1[1] % height), pos2[1] - pos1[1])
		return w * h

	def print_matches(self, matches):
		print
		print "** Text Line Matches **"
		for match in matches:
			op = match[0]
			print
			print "\t%s" % self.get_op(op)
			for line in match[1:]:
				print "\t%s" % str(line)
		print

	def _norm_edit_dist(self, str1, str2):
		edit_dist = Levenshtein.distance(str1, str2)
		norm = edit_dist / float(max(len(str1), len(str2)))
		return norm
		
	def merge(self):
		'''
		:return: list of TextLine - lines1, lines2 merged into one list
		'''
		matches = self.get_matches()
		merged_list = list()
		for match in matches:
			#print
			#print match
			op = match[0]
			if op == self.PERFECT:
				line1 = match[1]
				line2 = match[2]
				line1.aggregate(line2)
				#print "\t", line1
				merged_list.append(line1)
			if op == self.PARTIAL1:
				#print "Partial 1"
				line1 = match[1]
				prefix = match[2]
				suffix = match[3]
				line1.aggregate_partial(prefix, suffix)
				merged_list.append(line1)
			if op == self.PARTIAL2:
				#print "Partial 2"
				line2 = match[1]
				prefix = match[2]
				suffix = match[3]
				prefix.aggregate_as_prefix(line2)
				suffix.aggregate_as_suffix(line2)
				merged_list.append(prefix)
				merged_list.append(suffix)
		for idx1, line in enumerate(self.lines1):
			if not self.first_matches[idx1]:
				merged_list.append(line)
		for idx2, line in enumerate(self.lines2):
			if not self.second_matches[idx2]:
				merged_list.append(line)
		return merged_list

	def push_away(self, perc):
		'''
		Modifies both sequences.  
		If everything matches, they can't get pushed apart
		'''
		matches = self.get_matches()
		self._push_away_helper(self.lines1, perc)
		self._push_away_helper(self.lines2, perc)

	def _push_away_helper(self, lines, perc):
		matched_weight = 0
		unmatched_weight = 0
		for line in lines:
			if line.matched:
				matched_weight += line.match_value()
			else:
				unmatched_weight += line.match_value()
		if unmatched_weight == 0:
			# cannot push apart because everything matched
			return
		total_weight = matched_weight + unmatched_weight
		redistribute_weight = matched_weight * perc

		#print "\nTotal Weight: %.2f" % total_weight
		#print "\tMatched Weight: %.2f" % matched_weight
		#print "\tUnMatched Weight: %.2f" % unmatched_weight
		#print "\tRedistributed Weight: %.2f" % redistribute_weight
		for line in lines:
			if line.matched:
				line.count *= (1 - perc)
			else:
				# rich get richer scheme
				line.count += redistribute_weight / unmatched_weight

	def get_match_vector(self):
		self.get_matches()
		return self.first_matches
		#return map(lambda line: 1 if line.matched else 0, self.lines1)

#class TextLineKDMatcher:
#
#	PERFECT = 0
#	PARTIAL1 = 1  # line1 matches two lines in lines2
#	PARTIAL2 = 2  # line2 matches two lines in lines1
#	SUFFIX1 = 3   # line1 is a suffix of line2
#	SUFFIX2 = 4   # line2 is a suffix of line1
#	PREFIX1 = 5   # line1 is a prefix of line2
#	PREFIX2 = 6   # line2 is a prefix of line1
#	# prefixes and suffixes are condensed into Partials if they can
#
#	OP_STR = {PERFECT: "Perfect", PARTIAL1: "Partial1", PARTIAL2: "Partial2", SUFFIX1: "Suffix1",
#				SUFFIX2: "Suffix2", PREFIX1: "Prefix1", PREFIX2: "Prefix2"}
#
#	
#	def __init__(self, first, second, dist_thresh, partials=False):
#		'''
#		:param dist_thresh: num distance threshold
#		:param partials: bool whether to use partial matches or not
#		'''
#		self.first = first
#		self.second = second
#
#		self.dist_thresh = dist_thresh
#		self.dist_thresh_sqr = dist_thresh * dist_thresh
#		self.do_partial_matches = partials
#		self.matches = None
#
#	def op_str(self, op):
#		return self.OP_STR.get(op)
#	
#	def similarity(self):
#		''' :return: 0-1 similarity score between the two text lines '''
#		self.get_matches()  # make sure that lines get matched
#		total_val = 0.0
#		matched_val = 0.0
#		for line, matched in zip(itertools.chain(self.first.lines, self.second.lines), 
#				itertools.chain(self.first_matches, self.second_matches)):
#			total_val += line.match_value()
#			if matched:
#				matched_val += line.match_value()
#		return matched_val / total_val if total_val else 0.5
#
#	def _clear_matches(self):
#		''' Marks all lines as not matched '''
#		self.first_matches = [False] * len(self.first.lines)
#		self.second_matches = [False] * len(self.second.lines)
#
#	def _find_perfect_matches(self):
#		self._clear_matches()
#		perfect_matches = list()
#		potential_matches = self.first.kd_tree.query_ball_tree(self.second.kd_tree, self.dist_thresh)
#		for idx1, line1 in enumerate(self.first.lines):
#			for idx2 in potential_matches[idx1]:
#				line2 = self.second.lines[idx2]
#				if line2.matched:
#					continue
#				if self.perfect_match(line1, line2):
#					perfect_matches.append( (self.PERFECT, line1, line2) )
#					line1.matched = True
#					line2.matched = True
#					break
#		return perfect_matches
#
#	def perfect_match(self, line1, line2):
#		'''
#		A Perfect match is defined to be two lines whose start positions are within
#			the distance threshold, whose sizes are similar, and whose normalized
#			edit distance is below some threshold
#		:param line1: TextLine
#		:param line2: TextLine
#		:return: bool
#		'''
#		if utils.ratio(line1.N, line2.N) < (1 - TEXT_EDIT_DIST_THRESH):
#			return False
#
#		# check equality before heavy calculation
#		edit_dist = Levenshtein.distance(line1.text, line2.text) if line1.text != line2.text else 0
#		norm = edit_dist / float(max(line1.N, line2.N))
#		return edit_dist <= 1 or norm <= TEXT_EDIT_DIST_THRESH
#
#	def suffix_match(self, suffix, complete):
#		'''
#		A Suffix match is defined to be two lines whose end positions are within
#			the distance threshold, the average character width is within
#			a threshold and the edit distance between the suffix and the truncated
#			other string is below a threshold.
#		:param suffix: TextLine that might be the suffix of complete
#		:param complete: TextLine that might contain suffix
#		:return: bool Whether suffix is a suffix of complete or not
#		'''
#		if complete.N <= suffix.N or utils.e_dist_sqr(complete.end_pos, suffix.end_pos) > self.dist_thresh_sqr:
#			return False
#
#		#if not utils.ratio(complete.char_width(), suffix.char_width()) > self.SIZE_RATIO:
#		#	return False
#
#		edit_dist = Levenshtein.distance(complete.text[-1*suffix.N:], suffix.text)
#		norm = edit_dist / float(suffix.N)
#		return edit_dist <= 1 or norm <= TEXT_EDIT_DIST_THRESH
#
#	def prefix_match(self, prefix, complete):
#		''' Same as suffix match, except with a prefix '''
#		if complete.N <= prefix.N:
#			return False
#
#		#if not utils.ratio(complete.char_width(), prefix.char_width()) > self.SIZE_RATIO:
#		#	return False
#
#		edit_dist = Levenshtein.distance(complete.text[:prefix.N], prefix.text)
#		norm = edit_dist / float(prefix.N)
#		return edit_dist <= 1 or norm <= TEXT_EDIT_DIST_THRESH
#
#	# could probably optimize this a bit more
#	def _find_partial_matches(self):
#		''' Finds Prefix/Suffix matches among the unmatched lines '''
#		partial_matches = list()
#		potential_matches = self.first.kd_tree.query_ball_tree(self.second.kd_tree, 1.2 * self.dist_thresh)
#		for idx1, line1 in enumerate(filter(lambda line: not line.matched, self.first.lines)):
#			for idx2 in potential_matches[idx1]:
#				line2 = self.second.lines[idx2]
#				if line2.matched:
#					continue
#				if self.prefix_match(line1, line2):
#					partial_matches.append( (self.PREFIX1, line1, line2) )
#				if self.prefix_match(line2, line1):
#					partial_matches.append( (self.PREFIX2, line1, line2) )
#				if self.suffix_match(line1, line2):
#					partial_matches.append( (self.SUFFIX1, line1, line2) )
#				if self.suffix_match(line2, line1):
#					partial_matches.append( (self.SUFFIX2, line1, line2) )
#		return partial_matches
#
#	def _condense_matches(self, partials):
#		''' :param partials: list of tuples - (type, line1, line2) '''
#		condensed = list()
#		# mapping of complete lines to the possible partials in the other list
#		# one_two[complete_line] == list(prefix1, prefix2, ..., suffix1, suffix2, ...)
#		one_two = collections.defaultdict(list)
#		two_one = collections.defaultdict(list)
#		for part in partials:
#			op, line1, line2 = part
#			if op in [self.PREFIX2, self.SUFFIX2]:
#				one_two[line1].append((op, line2))
#			if op in [self.PREFIX1, self.SUFFIX1]:
#				two_one[line2].append((op, line1))
#
#		# TODO: disambiguating multiple prefixes/suffixes
#		for line1, matches in one_two.iteritems():
#			prefix = suffix = None
#			for match in matches:
#				op, line = match
#				if op == self.PREFIX2:
#					prefix = line
#				if op == self.SUFFIX2:
#					suffix = line
#			if prefix is None or suffix is None:
#				continue
#			l = prefix.N + suffix.N
#			if utils.ratio(l, line1.N) > (1 - TEXT_EDIT_DIST_THRESH):
#				# we have an actual partial match
#				condensed.append( (self.PARTIAL1, line1, prefix, suffix,
#									self._norm_edit_dist(line1.text, prefix.text + suffix.text)) )
#
#		for line2, matches in two_one.iteritems():
#			prefix = suffix = None
#			for match in matches:
#				op, line = match
#				if op == self.PREFIX1:
#					prefix = line
#				if op == self.SUFFIX1:
#					suffix = line
#			if prefix is None or suffix is None:
#				continue
#			l = prefix.N + suffix.N
#			if utils.ratio(l, line2.N) > (1 - TEXT_EDIT_DIST_THRESH):
#				# we have an actual partial match
#				condensed.append( (self.PARTIAL2, line2, prefix, suffix,
#									self._norm_edit_dist(line2.text, prefix.text + suffix.text)) )
#		return condensed
#
#	def get_matches(self):
#		''' :return: list of tuples (op, line1, line2) '''
#		if self.matches is None:
#			matches = self._find_perfect_matches()
#			if self.do_partial_matches:
#				partials = self._find_partial_matches()
#				condensed = self._condense_matches(partials)
#				# mark the matches
#				for match in condensed:
#					for line in match[1:-1]:
#						line.matched = True
#				matches += condensed
#			self.matches = matches
#			
#		return self.matches
#
#	def similarity_by_region(self, rows, cols, size):
#		'''
#		:param rows: int number of rows
#		:param cols: int number of cols
#		:param size: (int, int) size of image1
#		:return: list(list(float(0-1))) matrix of regional percentage matches
#		'''
#		self.get_matches()
#		#print "sim_mat(rows=%d, cols=%d, size=%s)" % (rows, cols, size)
#		width = (size[0] / cols) + 1
#		height = (size[1] / rows) + 1
#		#print "\twidth:", width
#		#print "\theight:", height
#		total_mat = [([0] * cols) for r in xrange(rows)]
#		matched_mat = [([0] * cols) for r in xrange(rows)]
#		total = 0
#		for line in self.first.lines:
#			br = line.bottom_right()
#			#print "\t", line
#			#print "\tul: %s\t br: %s" % (line.pos, br)
#			regions = self._get_regions(line, width, height)
#			#print regions
#			for r, c, val in regions:
#				if r >= rows or c >= cols or r < 0 or c < 0:
#					continue
#				#print r, c, val
#				if line.matched:
#					matched_mat[r][c] += val
#				#else:
#				#	print r, c, val, line
#				total_mat[r][c] += val
#				total += val
#		perc_mat = [([0] * cols) for r in xrange(rows)]
#		weight_mat = [([0] * cols) for r in xrange(rows)]
#		for r in xrange(rows):
#			for c in xrange(cols):
#				perc_mat[r][c] = matched_mat[r][c] / total_mat[r][c] if total_mat[r][c] else 0 #float('NaN')
#				weight_mat[r][c] = total_mat[r][c] / total if total else (1.0 / rows * cols)
#		return perc_mat, weight_mat
#
#	def _get_regions(self, line, width, height):
#		line_area = float(line.size[0] * line.size[1])
#		if line_area == 0:
#			return list()
#		line_value = line.match_value()
#		#print line
#		#print "\tarea: %.0f \tvalue: %d" % (line_area, line_value)
#		ul = line.pos
#		br = line.bottom_right()
#		row1, col1 = self._get_region(ul, width, height)
#		row2, col2 = self._get_region(br, width, height)
#		#print "\t%s\t%s" % ( (row1, col1), (row2, col2) )
#		regions = list()
#		for row in xrange(row1, row2 + 1):
#			for col in xrange(col1, col2 + 1):
#				x = ul[0] if col == col1 else col * width
#				y = ul[1] if row == row1 else row * height
#				#print "\t", row, col, (x, y)
#				overlap = self._get_region_overlap( (x, y), br, width, height)
#				#print "\t", overlap
#				regions.append( (row, col, line_value * (overlap / line_area)) )
#		return regions
#
#	def _get_region(self, pos, width, height):
#		row = int(pos[1]) / height
#		col = int(pos[0]) / width
#		return (row, col)
#
#	def _get_region_overlap(self, pos1, pos2, width, height):
#		'''
#		:param pos1: (x, y) upper left corner of rect
#		:param pos2: (x, y) bottom right corner of rect
#		:param width: width of tesselating rectangular regions
#		:param height: height of tesselating rectangular regions
#		return the overlap area of the region contain pos1 with rectangle (pos1, pos2)
#		'''
#		w = min(width - (pos1[0] % width), pos2[0] - pos1[0])
#		h = min(height - (pos1[1] % height), pos2[1] - pos1[1])
#		return w * h
#
#	def print_matches(self, matches):
#		print
#		print "** Text Line Matches **"
#		for match in matches:
#			op = match[0]
#			print
#			print "\t%s" % self.get_op(op)
#			for line in match[1:]:
#				print "\t%s" % str(line)
#		print
#
#	def _norm_edit_dist(self, str1, str2):
#		edit_dist = Levenshtein.distance(str1, str2)
#		norm = edit_dist / float(max(len(str1), len(str2)))
#		return norm
#		
#	def merge(self):
#		'''
#		:return: list of TextLine - lines1, lines2 merged into one list
#		'''
#		matches = self.get_matches()
#		merged_list = list()
#		for match in matches:
#			#print
#			#print match
#			op = match[0]
#			if op == self.PERFECT:
#				line1 = match[1]
#				line2 = match[2]
#				line1.aggregate(line2)
#				#print "\t", line1
#				merged_list.append(line1)
#			if op == self.PARTIAL1:
#				#print "Partial 1"
#				line1 = match[1]
#				prefix = match[2]
#				suffix = match[3]
#				line1.aggregate_partial(prefix, suffix)
#				merged_list.append(line1)
#			if op == self.PARTIAL2:
#				#print "Partial 2"
#				line2 = match[1]
#				prefix = match[2]
#				suffix = match[3]
#				prefix.aggregate_as_prefix(line2)
#				suffix.aggregate_as_suffix(line2)
#				merged_list.append(prefix)
#				merged_list.append(suffix)
#		for line in itertools.chain(self.first.lines, self.second.lines):
#			if not line.matched:
#				merged_list.append(line)
#		return merged_list
#
#	def push_away(self, perc):
#		'''
#		Modifies both sequences.  
#		If everything matches, they can't get pushed apart
#		'''
#		matches = self.get_matches()
#		self._push_away_helper(self.first.lines, perc)
#		self._push_away_helper(self.second.lines, perc)
#
#	def _push_away_helper(self, lines, perc):
#		matched_weight = 0
#		unmatched_weight = 0
#		for line in lines:
#			if line.matched:
#				matched_weight += line.match_value()
#			else:
#				unmatched_weight += line.match_value()
#		if unmatched_weight == 0:
#			# cannot push apart because everything matched
#			return
#		total_weight = matched_weight + unmatched_weight
#		redistribute_weight = matched_weight * perc
#
#		#print "\nTotal Weight: %.2f" % total_weight
#		#print "\tMatched Weight: %.2f" % matched_weight
#		#print "\tUnMatched Weight: %.2f" % unmatched_weight
#		#print "\tRedistributed Weight: %.2f" % redistribute_weight
#		for line in lines:
#			if line.matched:
#				line.count *= (1 - perc)
#			else:
#				# rich get richer scheme
#				line.count += redistribute_weight / unmatched_weight
#
#	def get_match_vector(self):
#		self.get_matches()
#		return map(lambda line: 1 if line.matched else 0, self.first.lines)
#
