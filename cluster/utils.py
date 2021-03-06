
import os
import math
import string
import operator
import ImageFont
import collections
import Levenshtein
import cPickle
import networkx as nx
import numpy

colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255),
			 (255, 255, 0), (255, 0, 255), (0, 255, 255),
			 (128, 0, 0), (0, 128, 0), (0, 0, 128),
			 (128, 128, 0), (128, 0, 128), (0, 128, 128)]


def are_overlapping(ranges):
	'''
	:param ranges: list(tuple(a, b)) where a and b are inclusive interval endpoints
	:return: True if the ranges completely overlap
	'''
	ranges.sort()
	r_tot = ranges[0]
	for idx in xrange(1,len(ranges)):
		r = ranges[idx]
		if r[0] > r_tot[1]:
			return False
		r_tot = (min(r_tot[0], r[0]), max(r_tot[1], r[1]))
	return True


def range_contains(r1, r2):
	'''
	:param r1: tuple(a, b) where a and b are inclusive interval endpoints
	:param r2: tuple(a, b) where a and b are inclusive interval endpoints
	:return: True if r1 is contained in r2
	'''
	return r1[0] >= r2[0] and r1[1] <= r2[1] 


def overlap_len(r1, r2):
	'''
	Assumes one line is not contained in the other
	:param r1: tuple(a, b) where a and b are inclusive interval endpoints
	:param r2: tuple(a, b) where a and b are inclusive interval endpoints
	:return: length of the overlapping interval.  0 if not overlapping
	'''
	if r2[0] < r1[0]:
		r1, r2 = r2, r1
	return max(0, r1[1] - r2[0]) 


def gap_len(r1, r2):
	'''
	:param r1: tuple(a, b) where a and b are inclusive interval endpoints
	:param r2: tuple(a, b) where a and b are inclusive interval endpoints
	:return: length of the gap between the intervals.  0 if overlapping
	'''
	if r2[0] < r1[0]:
		r1, r2 = r2, r1
	return max(0, r2[0] - r1[1]) 


def tup_scale(tup, scale):
	'''
	:param tup: tuple of num
	:param scale: num to scale tup by
	'''
	return tuple(t * scale for t in tup)

def tup_int(tup):
	return tuple(int(t) for t in tup)


def tup_diff(tup1, tup2):
	'''
	:param tup1/2: tuples to be subtracted (same length)
	'''
	return tuple(t1 - t2 for t1, t2 in zip(tup1, tup2))


def tup_sum(tups):
	'''
	:param tups: list of tuple - all tuples must be same length
	'''
	return tuple(sum(t) for t in zip(*tups))

def tup_avg(tups, weights=None):
	'''
	:param tups: list of tuple - all tuples must be same length
	:param weights: list of int - optional weights for the average
	'''
	if weights is None:
		weights = [1] * len(tups)
	total_weight = float(sum(weights))
	return tuple(sum(map(lambda val, w: val * w, t, weights)) / total_weight for t in zip(*tups))


def norm_list(l):
	s = float(sum(l))
	return [x / s for x in l]

def norm_mat(m):
	s = float(sum(map(sum, m)))
	return [ [row[x] / s for x in xrange(len(row))] for row in m]

def e_dist(p1, p2):
	return math.sqrt(e_dist_sqr(p1, p2))

def e_dist_sqr(p1, p2):
	return (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 

def manhattan_dist(p1, p2):
	return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

def bhattacharyya_coeff(dist1, dist2):
	return sum(map(lambda p, q: math.sqrt(p * q), dist1, dist2))

def advance_to_blank(f):
	line = f.readline().strip()
	while line:
		line = f.readline().strip()
		

def ratio(num1, num2):
	'''
	Returns the ratio of two numbers, giving the smaller ratio
	'''
	return min(float(num1) / num2, float(num2) / num1)


def argmax(l):
	return l.index(max(l))


def harmonic_mean(x, y, beta=1.0):
	'''
	beta > 1 biases mean toward y
	beta < 1 biases mean toward x
	'''
	if x == y == 0:
		return 0
	return ((1 + beta) * x * y) / float((beta * x) + y)


def harmonic_mean_list(l):
	'''
	:param l: list of nums
	'''
	if not l:
		return 0.0
	prod = float(reduce(lambda x, y: x * y, l))
	if prod == 0:
		return prod
	denum = sum(map(lambda x: prod / x, l))
	return len(l) * prod / denum


def avg(l):
	return float((sum(l)) / len(l)) if len(l) else float('nan')


def wavg(l, w):
	'''
	:param l: list of num to be averaged
	:param w: list of num weights
	'''
	return float(sum(map(lambda val, w: val * w, l, w))) / sum(w) if len(l) else float('nan')


def stddev(l, mean=None):
	if mean is None:
		mean = avg(l)
	var = sum(map(lambda x: (x - mean) ** 2, l)) / len(l)
	return math.sqrt(var)

def median(l):
	return numpy.median(numpy.array(l))
	

def levenstein(i, j, s, t):
	return 0 if s[i] == t[j] else 1


def close_match(str1, str2, threshold):
	if str1 == str2:
		return True
	norm = float(len(str1) + len(str2))
	min_dist = abs(len(str1) - len(str2)) / norm 
	if min_dist < threshold:
		#dist = edit_distance(str1, str2, 1, levenstein)
		dist = Levenshtein.distance(str1, str2)
		return ((dist <= 1) or (dist / norm) < threshold)
	return False


def apply_mat(mat, func):
	new_mat = []
	for row in mat:
		new_mat.append(map(func, row))
	return new_mat


def format_as_mat(mat):
	'''
	:param mat: {<set x> : {<set y> : <any> } }
	'''
	new_mat = []
	for x in sorted(mat.keys()):
		row = []
		for y in sorted(mat[x].keys()):
			row.append(mat[x][y])
		new_mat.append(row)
	return new_mat


def pairwise(args, func, symmetric=True):
	mat = []
	for x, arg1 in enumerate(args):
		row = []
		for y, arg2 in enumerate(args):
			if symmetric and y < x:
				val = mat[y][x]
			else:
				val = func(arg1, arg2)
			row.append(val)
		mat.append(row)
	return mat


def insert_indices(mat, row_start=0, col_start=0):
	row0 = range(col_start, len(mat[0]) + col_start)
	row0.insert(0, " ")
	for x,row in enumerate(mat, row_start):
		row.insert(0, x)
	mat.insert(0, row0)

def print_mat(mat):
	max_lens = [max([len(str(r[i])) for r in mat])
					 for i in range(len(mat[0]))]

	print "\n".join(["".join([string.rjust(str(e), l + 2)
							for e, l in zip(r, max_lens)]) for r in mat])

def split_mat(mat, row_len):
	mats = []
	total_row_length = len(mat[0])
	start = 0
	end = row_len
	while start < total_row_length:
		new_mat = []
		for row in mat:
			new_row = row[start:end]
			new_mat.append(new_row)
		mats.append(new_mat)
		start += row_len
		end += row_len
	return mats

def mult_mats(mats):
	rows = len(mats[0])
	cols = len(mats[0][0])
	mult_mat = [[1] * cols for x in xrange(rows)]
	for mat in mats:
		assert len(mat) == rows
		assert len(mat[0]) == cols
		for r in xrange(rows):
			for c in xrange(cols):
				val = mat[r][c]
				mult_mat[r][c] *= val
	return mult_mat
	

def avg_mats(mats):
	rows = len(mats[0])
	cols = len(mats[0][0])
	avg_mat = [[0] * cols for x in xrange(rows)]
	for mat in mats:
		assert len(mat) == rows
		assert len(mat[0]) == cols
		for r in xrange(rows):
			for c in xrange(cols):
				val = mat[r][c]
				avg_mat[r][c] += val
	for r in xrange(rows):
		for c in xrange(cols):
			avg_mat[r][c] /= len(mats)
	return avg_mat

def wavg_mats(mats, weights):
	rows = len(mats[0])
	cols = len(mats[0][0])
	avg_mat = [[0] * cols for x in xrange(rows)]
	norm = float(sum(weights))
	for mat, weight in zip(mats, weights):
		assert len(mat) == rows
		assert len(mat[0]) == cols
		for r in xrange(rows):
			for c in xrange(cols):
				val = mat[r][c]
				avg_mat[r][c] += val * weight
	for r in xrange(rows):
		for c in xrange(cols):
			avg_mat[r][c] /= (len(mats) * norm)
	return avg_mat

def mat_sum(mat):
	return sum(map(sum, mat))

def avg_val_mat(mat):
	return mat_sum(mat) / float(len(mat) * len(mat[0]))

# Operations include skip or match
def edit_distance(s, t, id_cost, match_f):
	'''
	:param s: sequence 1
	:param t: sequence 2
	:param id_cost: num Cost of an Insertion or Deletion operation
	:param match_f: func (idx1, idx2, s, t) -> num  Cost of matching
	:return: Edit distance between s and t
	'''
	l1 = len(s) + 1 # height
	l2 = len(t) + 1 # width
	d = [ [x * id_cost for x in xrange(l2)] ]

	for i in xrange(1, l1):
		d.append([i * id_cost])
		for j in xrange(1, l2):
			_del = d[i-1][j] + id_cost
			_ins = d[i][j-1] + id_cost
			_match = match_f(i-1, j-1, s, t) + d[i-1][j-1]
			d[i].append(min(_del, _ins, _match))
	i = l1 - 1
	j = l2 - 1
	final_val =  d[l1 - 1][l2 - 1] 
	return final_val

def flatten(mat):
	return [cell for row in mat for cell in row]

def get_font(text, width):
	'''
	For the given text/size combo returns a matching font
	:param text: str
	:param width: int
	'''
	#_font_path = "/home/chris/formCluster/cluster/LiberationMono-Bold.tff"
	_font_path = "LiberationMono-Bold.ttf"
	fontsize = 1
	font = ImageFont.truetype(_font_path, fontsize)
	while font.getsize(text)[0] < width:
		fontsize += 1
		font = ImageFont.truetype(_font_path, fontsize)
	return font

def get_sorted_edges(sim_mat):
	edges = list()
	for x in xrange(len(sim_mat)):
		for y in xrange(len(sim_mat)):
			if y >= x:
				continue
			edges.append( (x, y, sim_mat[x][y]) )
	edges.sort(key=lambda tup: tup[2])
	return edges
			

def minimum_spanning_tree(sim_mat):
	'''
	Returns the minimum spanning tree of the similarity matrix
	:return: list( (idx1, idx2, sim) *)
	'''
	edges = get_sorted_edges(sim_mat)
	ccs = {x : x for x in xrange(len(sim_mat))}
	edges_added = list()
	for edge in edges:
		if len(edges_added) == (len(sim_mat) - 1):
			break
		idx1 = edge[0]
		idx2 = edge[1]
		if ccs[idx1] != ccs[idx2]:
			edges_added.append(edge)
			val = ccs[idx2]
			for x in ccs:
				if ccs[x] == val:
					ccs[x] = ccs[idx1]
	return edges_added

def get_ccs(vertices, edges):
	'''
	return: list(list(v1, v2, ...), ...)
	'''
	ccs = list()
	for edge in edges:
		idx1 = edge[0]
		idx2 = edge[1]
		cc1 = None
		cc2 = None
		for cc in ccs:
			if idx1 in cc:
				cc1 = cc
			if idx2 in cc:
				cc2 = cc
		if cc1 is cc2:
			if cc1 is None:
				# new cc
				ccs.append(set([idx1, idx2]))
			else:
				pass
		elif cc1 is None:
			# add leaf
			cc2.add(idx1)
		elif cc2 is None:
			# add leaf
			cc1.add(idx2)
		else:
			# merge
			ccs.remove(cc2)
			cc1.update(cc2)
	for vertex in vertices:
		has_cc = False
		for cc in ccs:
			if vertex in cc:
				has_cc = True
				break
		if not has_cc:
			ccs.append(set([vertex]))
	return ccs

def max_weight_clique(sim_mat, idxs):
	m = 0
	for idx1 in idxs:
		for idx2 in idxs:
			if idx1 != idx2:
				m = max(m, sim_mat[idx1][idx2])
	return m

def find_best_clique(sim_mat, size):
	G = nx.Graph()
	for x in xrange(len(sim_mat)):
		G.add_node(x)
	edges = get_sorted_edges(sim_mat)
	x = 0
	thresh = 0.05
	while thresh <= 1:
		while x < len(edges) and edges[x][2] <= thresh:
			G.add_edge(edges[x][0], edges[x][1])
			x += 1
		max_cliques = nx.find_cliques(G)

		# bucket sort
		by_size = collections.defaultdict(list)
		for clique in max_cliques:
			by_size[len(clique)].append(clique)

		biggest = max(by_size.keys())
		if biggest >= size:
			# do tie breaking
			cliques = by_size[biggest]
			best_clique = None
			best_score = 1000000
			for clique in cliques:
				score = max_weight_clique(sim_mat, clique)
				if score < best_score:
					best_score = score
					best_clique = clique
			return best_clique
		thresh += 0.05

def euclideanDistance(x,y):
    assert(len(x) == len(y))
    
    total = 0.0
    for i in range(len(x)):
        tmp = (x[i] - y[i])
        total += tmp*tmp
        
    return math.sqrt(total)

def save_obj(obj, path):
	'''
	Use Pickle to write obj
	:param obj: object to be saved
	:param path: the path to save obj to
	'''
	try:
		saveFile = open(path, "w")
	except Exception as e:
		print "Error opening save file: %s" % repr(e)
		return
 
	cPickle.dump(obj, saveFile, -1)	

	saveFile.close()

def load_obj(path):
	'''
	Use Pickle to load obj
	:param path: location of the file to load
	'''
	try:
		loadFile = open(path, 'r')
	except Exception as e:
		print "Error opening file: %s" % repr(e)
		return None

	obj = cPickle.load(loadFile)

	loadFile.close()
	return obj

def pad_to_len(s, l):
	return s + (" " * (l - len(s))) if l > len(s) else s

if __name__ == "__main__":
	mat = pairwise(xrange(5), lambda x,y: math.sqrt(x + y))
	insert_indices(mat, row_start=2, col_start=3)
	print_mat(mat)

