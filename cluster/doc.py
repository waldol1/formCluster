
import Image
import ImageDraw
import ImageFont
import json
import string
import utils
import os

import components
import profiles
import lines
import text

# do lazy loading of documents.  It's a good thing
LAZY = True
# prefix/suffix matching for edit distance in text lines
ALLOW_PARTIAL_MATCHES = False
# set true to print a bunch of extra info
DEBUG = False

# the file extensions of the files that compose a single document
#_file_extensions = [".jpg", ".xml", "_line.xml", "_FormType.txt", "_endpoints.xml"]

# use weight decay when aggregating two document together - eventually phases out infrequent features
DECAY = True
# magnitude of the decay
_line_decay_amount = 1.0 / 10 if DECAY else 0
_text_decay_amount = 1.0 / 15 if DECAY else 0

# used to determine grid line offset tolerance when matching
_line_thresh_mult = 0.05
_text_line_thresh_mult = 0.15

ROWS = 4
COLS = 4

def get_doc(_dir, source_file):
	document = Document(os.path.basename(source_file), os.path.join(_dir, source_file))
	return document

def get_docs(_dir, pr=True):
	'''
	returns (list(Document), int) - the list of Documents loaded and the
		number of incomplete documents.
		_dir - str the directory to load from.  Subdirectories are not considered
		pr - boolean to print or not
	'''
	docs = []
	num_loaded = 0
	num_exceptions = 0
	if pr:
		print "Loading Docs from:", _dir
	for f in os.listdir(_dir):
		if f.endswith(".txt"):
			try:
				docs.append(get_doc(_dir, f))
				num_loaded += 1
				if pr and num_loaded % 10 == 0:
					print "\tLoaded %d documents" % num_loaded
			except:
				num_exceptions += 1
	if pr:
		print "\t%d Docs read" % num_loaded
		if num_exceptions:
			print "\t%d Docs could not be read" % num_exceptions
	return docs, num_exceptions
	

def get_docs_nested(data_dir, pr=True):
	'''
	returns (list(Document), int) - the list of Documents loaded and the
		number of incomplete documents.
		data_dir - str the top directory to load from.  All documents two 
			directories down are loaded.
		pr - boolean to print or not
	'''
	all_docs = []
	total_exceptions = 0
	for _dir in os.listdir(data_dir):
		r_dir = os.path.join(data_dir, _dir)
		docs, num_exceptions = get_docs(r_dir, pr)
		all_docs += docs
		total_exceptions += num_exceptions
	if pr:
		print "Finished loading all documents"
		print "%d Total docs read" % len(all_docs)
		if total_exceptions:
			print "%d Toal docs could not be read" % total_exceptions
	return all_docs



class Document:
	'''
	Represents an element in our clustering scheme.  Composed of a single document
		digital image and all extracted features (contained in various files).
	Currently we use Text Lines, Horizontal Grid Lines, Vertical Grid Lines, and
		image dimensions as features
	'''

	def __init__(self, _id, f=None):
		'''
		_id - a unique id for the document
		f - str filename of the feature file.  Use None for self.copy()
		_original - boolean used by copy() to avoid reloading from files
		'''
		self._id = _id
		self.source_file = f
		self.loaded = False
		if not LAZY and self.source_file:
			self.load()
	
	def copy(self, new_id):
		''' Make a deep copy of a document with a new_id '''
		self._load_check()
		cpy = Document(new_id)
		cpy.loaded = True  # makes sure we never load data from files

		cpy.label = self.label
		cpy.text_lines = map(lambda line: line.copy(), self.text_lines)
		cpy.h_lines = map(lambda line: line.copy(), self.h_lines)
		cpy.v_lines = map(lambda line: line.copy(), self.v_lines)
		cpy.size = self.size

		return cpy

	def display(self):
		''' print out all of the text lines '''
		self._load_check()
		print "Document %s" % self._id
		for line in self.textLines:
			print line
		print
	
        def _load_check(self):
		if not self.loaded:
			self.load()

	def load(self):
		lines = open(self.source_file, 'r').readlines()

		#self.label = lines[0] 
		# forgot to get the basename in the file in extraction script
		self._id = os.path.basename(lines[0].strip())

		self.label = lines[1].strip()

		size_line = lines[2]
		tokens = size_line.split()
		self.size = ( int(tokens[0]), int(tokens[1]) )

		self.text_lines = list()
		for x, line in enumerate(lines[4:], start=4):
			line = line.strip()
			if line == "":
				break
			tokens = line.split()
			text = " ".join(tokens[4:])
			pos = ( int(tokens[0]), int(tokens[1]) )
			size = ( int(tokens[2]), int(tokens[3]) )
			self.text_lines.append(components.TextLine(text, pos, size))
		x += 1


		self.h_lines = list()
		self.v_lines = list()
		orien = components.Line.HORIZONTAL
		l = self.h_lines
		for line in lines[x:]:
			line = line.strip()
			if line == "":
				orien = components.Line.VERTICAL
				l = self.v_lines
				continue
			tokens = line.split()
			pos = ( int(tokens[0]), int(tokens[1]) )
			length = int(tokens[2])
			thick = int(tokens[3])
			l.append(components.Line(orien, pos, length, thick))
		self.loaded = True


	_sim_names = ['text_line', 'h_line', 'v_line']
	def similarity_vector(self, other):
		''' returns a similarity vector '''
		region_sims_by_name = self.similarity_mats_by_name(other)
		global_scores_by_name = self.similarities_by_name(other)
		vector = list()
		for name in self._sim_names:
			vector.append(global_scores_by_name[name])
		for name in self._sim_names:
			mat = region_sims_by_name[name]
			for row in mat:
				for val in row:
					vector.append(val)
		return vector

	def get_initial_vector_weights(self, other):
		''' 
		:param other: needed, but doesn't affect the weights returned
		returns inital weights for use in the NNs 
		'''
		region_weights_by_name = self.similarity_weights_by_name(other)
		vector = list()

		# for the global scores
		for name in self._sim_names:
			vector.append(1)
		for name in self._sim_names:
			mat = region_weights_by_name[name]
			for row in mat:
				for val in row:
					vector.append(val)
		return vector
		

	def similarity(self, other):
		''' alias for global_similarity '''
		return self.global_similarity(other)

	def global_similarity(self, other):
		''' return the harmonic mean of the different similarity metrics between self and other '''
		sims = self.similarities_by_name(other).values()
		return utils.harmonic_mean_list(sims)
                    
	def similarities_by_name(self, other):
		''' return dict {name_of_sim_metric : sim_val} '''
		sims = dict()
		funs = self.similarity_functions()
		for fun in funs:
			sims[fun] = funs[fun](other)
		return sims

	def similarity_mats_by_name(self, other):
		''' return dict {name_of_sim_metric : sim_mat} '''
		sims = dict()
		funs = self.similarity_mat_functions()
		for fun in funs:
			sims[fun] = funs[fun](other)
		return sims

	def similarity_weights_by_name(self, other):
		''' return dict {name_of_sim_metric : weight_mat} '''
		sims = dict()
		funs = self.similarity_weight_functions()
		for fun in funs:
			sims[fun] = funs[fun](other)
		return sims

	def similarity_mats_weights_by_name(self, other):
		''' return dict {name_of_sim_metric : weight_mat} '''
		sims = dict()
		funs = self.similarity_mat_weight_functions()
		for fun in funs:
			sims[fun] = funs[fun](other)
		return sims

	def similarity_functions(self):
		''' return dict {name_of_sim_metric : sim_function(other) } '''
		funs = dict()
		funs['text_line'] = (lambda other: self.text_line_similarity(other))
		funs['h_line'] = (lambda other: self.h_line_similarity(other))
		funs['v_line'] = (lambda other: self.v_line_similarity(other))
		return funs

	def similarity_mat_functions(self):
		''' return dict {name_of_sim_metric : sim_function(other) } '''
		funs = dict()
		funs['text_line'] = (lambda other: self.text_line_similarity_mat(other)[0])
		funs['h_line'] = (lambda other: self.h_line_similarity_mat(other)[0])
		funs['v_line'] = (lambda other: self.v_line_similarity_mat(other)[0])
		return funs

	def similarity_mat_weight_functions(self):
		''' return dict {name_of_sim_metric : sim_function(other) } '''
		funs = dict()
		funs['text_line'] = (lambda other: self.text_line_similarity_mat(other))
		funs['h_line'] = (lambda other: self.h_line_similarity_mat(other))
		funs['v_line'] = (lambda other: self.v_line_similarity_mat(other))
		return funs

	def similarity_weight_functions(self):
		''' return dict {name_of_sim_metric : sim_function(other) } '''
		funs = dict()
		funs['text_line'] = (lambda other: self.text_line_similarity_mat(other)[1])
		funs['h_line'] = (lambda other: self.h_line_similarity_mat(other)[1])
		funs['v_line'] = (lambda other: self.v_line_similarity_mat(other)[1])
		return funs

	def similarity_function_names(self):
		''' return a list of the sim function names '''
		return ['text_line', 'h_line', 'v_line']

	def text_line_similarity(self, other):
		''' return the text line similarity '''
		self._load_check()
		other._load_check()
		thresh_dist = _text_line_thresh_mult * max(max(self.size), max(other.size))  # % of largest dimension

		matcher = text.TextLineMatcher(self.text_lines, other.text_lines, thresh_dist, ALLOW_PARTIAL_MATCHES)
		#sim_mat = matcher.similarity_by_region(ROWS, COLS, self.size)
		#utils.print_mat(utils.apply_mat(sim_mat, lambda x: "%.3f" % x))

		return matcher.similarity()

	def line_similarity(self, other):
		''' Combined horizontal and vertical line similarity (harmonic mean) [0-1] '''
		h_sim = self.h_line_similarity(other)
		v_sim = self.v_line_similarity(other)
		return utils.harmonic_mean(h_sim, v_sim)

	def h_line_similarity(self, other):
		''' return horizontal line similarity score [0-1] '''
		self._load_check()
		other._load_check()

		h_thresh_dist = _line_thresh_mult * max(self.size[0], other.size[0]) 
		h_matcher = lines.LMatcher(self.h_lines, other.h_lines, h_thresh_dist, self.size)
		#matches = h_matcher.get_matches()

		#sim_mat = h_matcher.similarity_by_region(ROWS, COLS, self.size)
		#utils.print_mat(utils.apply_mat(sim_mat, lambda x: "%.3f" % x))

		return h_matcher.similarity()

	def v_line_similarity(self, other):
		''' return vertical line similarity score [0-1] '''
		self._load_check()
		other._load_check()

		v_thresh_dist = _line_thresh_mult * max(self.size[1], other.size[1]) 
		v_matcher = lines.LMatcher(self.v_lines, other.v_lines, v_thresh_dist, self.size)

		#sim_mat = v_matcher.similarity_by_region(ROWS, COLS, self.size)
		#utils.print_mat(utils.apply_mat(sim_mat, lambda x: "%.3f" % x))

		return v_matcher.similarity()

	def text_line_similarity_mat(self, other):
		''' return the text line similarity matrix and weight mat'''
		self._load_check()
		other._load_check()
		thresh_dist = _text_line_thresh_mult * max(max(self.size), max(other.size))  # % of largest dimension

		matcher = text.TextLineMatcher(self.text_lines, other.text_lines, thresh_dist, ALLOW_PARTIAL_MATCHES)
		sim_mat, weight_mat = matcher.similarity_by_region(ROWS, COLS, self.size)
		#utils.print_mat(utils.apply_mat(sim_mat, lambda x: "%.3f" % x))

		return sim_mat, weight_mat

	def h_line_similarity_mat(self, other):
		''' return horizontal line similarity matrix and weight mat'''
		self._load_check()
		other._load_check()

		h_thresh_dist = _line_thresh_mult * max(self.size[0], other.size[0]) 
		h_matcher = lines.LMatcher(self.h_lines, other.h_lines, h_thresh_dist, self.size)

		sim_mat, weight_mat = h_matcher.similarity_by_region(ROWS, COLS, self.size)
		#utils.print_mat(utils.apply_mat(sim_mat, lambda x: "%.3f" % x))
		return sim_mat, weight_mat

	def v_line_similarity_mat(self, other):
		''' return vertical line similarity matrix and weight mat'''
		self._load_check()
		other._load_check()

		v_thresh_dist = _line_thresh_mult * max(self.size[1], other.size[1]) 
		v_matcher = lines.LMatcher(self.v_lines, other.v_lines, v_thresh_dist, self.size)

		sim_mat, weight_mat = v_matcher.similarity_by_region(ROWS, COLS, self.size)
		#utils.print_mat(utils.apply_mat(sim_mat, lambda x: "%.3f" % x))
		return sim_mat, weight_mat

	def clear_text_matches(self):
		''' reset the matched tag on all of the text lines '''
		for line in self.text_lines:
			line.matched = False

	def _aggregate_text(self, other):
		''' Take the text lines of other and merge them into this Document's text lines '''
		thresh_dist = _text_line_thresh_mult * max(max(self.size), max(other.size))  # % of largest dimension
		matcher = text.TextLineMatcher(self.text_lines, other.text_lines, thresh_dist, ALLOW_PARTIAL_MATCHES)

		#print "BEFORE", id(self)
		#for line in self.text_lines:
		#	print line
		self.text_lines = matcher.merge()
		#print "\nAFTER", id(self)
		#for line in self.text_lines:
		#	print line

	def _aggregate_h_lines(self, other):
		''' Take the horizontal lines of other and merge them into this Document's text lines '''
		h_thresh_dist = _line_thresh_mult * max(self.size[0], other.size[0]) 
		h_matcher = lines.LMatcher(self.h_lines, other.h_lines, h_thresh_dist, self.size)
		#ops = h_matcher.get_operations()
		#h_matcher.print_ops(ops)
		self.h_lines = h_matcher.get_merged_lines()

	def _aggregate_v_lines(self, other):
		''' Take the vertical lines of other and merge them into this Document's text lines '''
		v_thresh_dist = _line_thresh_mult * max(self.size[1], other.size[1]) 
		v_matcher = lines.LMatcher(self.v_lines, other.v_lines, v_thresh_dist, self.size)
		self.v_lines = v_matcher.get_merged_lines()
		
	def aggregate(self, other):
		'''
		Merge other into self
		Does not modify other, but self is modified
		'''
		self._load_check()
		other._load_check()

		self.size = (max(self.size[0], other.size[0]), max(self.size[1], other.size[1]))

		self._aggregate_text(other)
		self._aggregate_h_lines(other)
		self._aggregate_v_lines(other)

		self.prune()

	def prune(self):
		'''
		Decrements each text/horz/vert line by the parameterized amount.  Remove lines
			that have counts below 0
		'''
		self._prune_text(0, _text_decay_amount)
		self._prune_h_lines(0, _line_decay_amount)
		self._prune_v_lines(0, _line_decay_amount)

	def final_prune(self):
		'''
		When clustering is done, remove text/horz/vert lines that have realatively very low
			counts
		'''
		get_prune_val = lambda lines: max(map(lambda line: line.count, lines)) / 10.0
		if self.text_lines:
			self._prune_text(get_prune_val(self.text_lines), _text_decay_amount)
		if self.h_lines:
			self._prune_h_lines(get_prune_val(self.h_lines), _line_decay_amount)
		if self.v_lines:
			self._prune_v_lines(get_prune_val(self.v_lines), _line_decay_amount)

	def _prune_text(self, thresh, amount):
		map(lambda line: line.decay(amount), self.text_lines)
		self.text_lines = filter(lambda line: line.count > thresh, self.text_lines)

	def _prune_h_lines(self, thresh, amount):
		map(lambda line: line.decay(amount), self.h_lines)
		tmp = filter(lambda line: line.count > thresh, self.h_lines)
		#if not tmp:
		#	print self.h_lines
		self.h_lines = tmp

	def _prune_v_lines(self, thresh, amount):
		map(lambda line: line.decay(amount), self.v_lines)
		tmp = filter(lambda line: line.count > thresh, self.v_lines)
		#if not tmp:
		#	print self.v_lines
		self.v_lines = tmp

	def draw(self, colortext=False):
		'''
		:param colortext: True for drawing each text line a different color, False for all black
		:return Image:
		'''
		self._load_check()
		im = Image.new('RGB', self.size, 'white')
		draw = ImageDraw.Draw(im)
		colors = utils.colors
		idx = 0
		for line in self.h_lines:
			color = 'orange' if line.matched else 'red'
			draw.line( (utils.tup_int(line.pos), utils.tup_int( (line.pos[0] + line.length, line.pos[1]) )) ,
						width=int(line.thickness * 2), fill=color)
			draw.text( utils.tup_int(line.pos), "%.2f" % line.count, fill="black")
		for line in self.v_lines:
			color = 'purple' if line.matched else 'blue'
			draw.line( (utils.tup_int(line.pos), utils.tup_int( (line.pos[0], line.pos[1] + line.length) )) ,
						width=int(line.thickness * 2), fill=color)
			draw.text( utils.tup_int(line.pos), "%.2f" % line.count, fill="black")
		for line in self.text_lines:
			fill = colors[idx % len(colors)] if colortext else "black"
			draw.text(line.pos, line.text, font=utils.get_font(line.text, line.size[0]), fill=fill)
			draw.text( line.pos, "%.2f" % line.count, fill="blue")
			idx += 1

		return im
		
