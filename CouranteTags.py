from music21 import *
import MarkovCourantes as mk
import collections
import numpy as np 
import pandas as pd 
import os
import copy
import random

chamb = corpus.corpora.LocalCorpus('chambonnieres')
chamb1Piece = chamb.search('02')[0].parse()
chamb1Corpus = chamb.search('02')

''' Some things to do:
1) CHECK! Make sure that I'm not duplicating tags (probably means creating a list of all used tags)
2) CHECK! Create an error message if a start tag doesn't have a matching end tag
3) CHECK! Verify that concatenating excerpts in different keys will produce key signature changes to match
4) CHECK! Create a function to annotate an excerpt with different kinds of information (tag set, origin piece, measure and bar numbers etc.)
5) Function to select tags from a given piece
'''

plist = ['02Courante']
klist = [key.Key('a')]

tags_best = ['tpro', 'cad', 'att', 'tail', 'ptc', 'ttc']

# Closing tag needs to be last in a group of tags
Cell = collections.namedtuple('Cell', 'piece measure beat')
Excerpt = collections.namedtuple("Excerpt", 'piece m_start b_start m_end b_end t_list segue_to segue_from', defaults= (None, None))
M21Excerpt = collections.namedtuple("M21Excerpt", 'm21_stream ex_info')
# tags is a dictionary. The key is the name of the tag. Each value is a list of excerpts.
# tag name is a frozenset of the various tags
# Excerpt is a namedtuple, with m_start, b_start, m_end, b_end, segue_to, segue_from 
# The segues are also tags
# tags = {: [Excerpt(6, 1, 7, 2), Excerpt(8, 2.5, 9. 2.5)]}


def write_scores(slist, d):
	''' Writes a list of scores to disk. 
	Takes a list of tuples of scores and filenames'''
	for el in slist:
		el[0].write("xml", "{directory}/{fname}.xml".format(directory=d, fname=el[1]))

def practice_scores(plist, klist, corp, bass=True, randb=True, t_map=None):
	''' Generates scores and filenames. Takes a list of piecenames, and a list of keys, and a corpus,
	and returns a list of tuples of scores and filenames. '''
	slist = []
	for p in plist:
		s_original = corp.search(p)[0].parse()
		old_k = s_original.analyze('key')
		for k in klist:
			if old_k != k:
				s = transpose_stream(copy.deepcopy(s_original), old_k, k)
			else:
				s = copy.deepcopy(s_original)
			fname = p + "." + str(k)
			if bass:
				sbass = mk.score_bass(s)
				if t_map:
					fname = fname + ".annotated"
					tag_lyrics_bass(sbass, p, t_map)
				fname = fname + "." + "bass"
				slist.append((sbass, fname))
			if randb:
				srandb = mk.score_rhythm_and_bass(s)
				if t_map:
					fname = fname + ".annotated"
					tag_lyrics_bass(srandb, p, t_map)
				fname = fname + "." + "randb"
				slist.append((srandb, fname))
	return slist

def practice_tags( t_dict, klist, corp, t_map=None, piece= None, n=None, t_list=None, from_piece = False):
	''' Generates scores and filenames for practicing with tags.
	
	Takes a list of pieces'''
	slist = []
	filename = "tags"
	if piece:
		tags = choose_tags_from_piece (t_map, piece, n, t_list)
		# exs = tags_to_excerpts (tags, t_dict, piece)
		filename = filename + "." + piece
	else:
		tags = random_tags(t_dict, n, t_list)
		filename = filename + ".random"
	if from_piece:
		exs = choose_exs (t_dict, tags, piece)
		filename = filename + ".samepiece"
	else:
		exs = choose_exs (t_dict, tags)
	for ex in exs:
		print (ex)
	m21exs = create_m21excerpts (exs, corp)
	for k in klist:
		ex_out_list = []
		for m21ex in m21exs:
			ex_out = transpose_excerpt (m21ex, k, corp)
			ex_out_list.append(ex_out) 
		for ex in ex_out_list:
			print(ex)
		fname = filename + "." + str(k)
		s = excerpts_to_score (ex_out_list, fname)
		slist.append((s, fname))
	return slist

def dispositio_scores(t_map, corp):
	pieces = corp.search('')
	out = []
	for p in pieces:
		piece_name = os.path.splitext(os.path.basename(p.sourcePath))[0]
		print(piece_name)
		score = p.parse()
		disp_map = dispositio_map(piece_name, t_map)
		tag_lyrics(score, piece_name, disp_map)
		out_name = piece_name + "Dispositio"
		out.append((score, out_name))
	return out


	

def closest(n_list, b): 
    return min(n_list, key = lambda i: abs(i.beat-b))

def closest_bass(s, m , b):
	try:	
		options = s.measure(m).getElementsByClass('PartStaff')[-1].recurse().notesAndRests
	except:
		options = s.measure(m).recurse().notesAndRests
	return closest(options, b)

def add_voice(s):
	try:
		ps = s.getElementsByClass('PartStaff')[-1]
	except:
		ps = s
	ms = ps.getElementsByClass('Measure')[1:]
	for m in ms:
		m_notes = m.notesAndRests
		m_notes_list = []
		for x in m_notes:
			m_notes_list.append(x.offset)
			m_notes_list.append(x)

		v1 = stream.Voice(id='1')
		v1.insert(m_notes_list)
		m.remove(list(m_notes))
		v2 = stream.Voice(id='2')
		v2.style.hideObjectOnPrint = True
		for i in range(6):
			n = note.Rest(quarterLength = 1)
			n.style.hideObjectOnPrint = True
			v2.insert(i, n)
		m.insert(v1)
		m.insert(v2)
	return s

def tag_lyrics_bass(s, piece, t_map):
	''' takes a stream and and a tag map, and annotates the stream with tag information '''
	class_filter = [layout.SystemLayout, layout.PageLayout]
	layout_trash = list(s.recurse().getElementsByClass(class_filter))
	s.remove(layout_trash, recurse=True)
	working_tags = {}
	lyric_dict = {1: 'blue', 2: 'purple', 3: 'green', 4:'black'}
	available_numbers = [1, 2, 3, 4]
	add_voice(s)
	for m in t_map[piece]:
		for b in t_map[piece][m]:
			for t in t_map[piece][m][b]:
				if t[0] == "start":
					b_note = closest_bass(s, m, b)
					n_note = b_note.next('GeneralNote')
					if b_note.offset == n_note.offset:
						n_note = n_note.next('GeneralNote')
					lyric_num = min(available_numbers)
					t_text = " ".join(t[1])
					# first check if the note already has lyrics
					try:
						l = [x for x in b_note.lyrics if x.number == lyric_num][0]
						print (l)
						l.text = l.text + " " + "["
						working_tags[t[1]] = lyric_num
						available_numbers.remove(lyric_num)
					except:
						to_add1 = note.Lyric(number = lyric_num, text = "[")
						to_add1.style.color = lyric_dict[lyric_num]
						b_note.lyrics.append(to_add1)
						working_tags[t[1]] = lyric_num
						available_numbers.remove(lyric_num)
					to_add2 = note.Lyric(number = lyric_num, text = t_text)
					to_add2.style.color = lyric_dict[lyric_num]
					n_note.lyrics.append(to_add2)

				if t[0] == "end":
					lyric_text = ']'
					b_note = closest_bass(s, m, b)
					lyric_num = working_tags[t[1]]
					to_add = note.Lyric(number = lyric_num, text = lyric_text, syllabic='end')
					to_add.style.color = lyric_dict[lyric_num]
					b_note.lyrics.append(to_add)
					del working_tags[t[1]] 
					available_numbers.append(lyric_num)	
	return 

def dispositio_map (piece, t_map):
	disp_map = {}
	mod_set = {'dom', 'sub', 'maj', 'min', 'super', 'subt', '→', '←', 'med'}
	disp_map[piece] = {}
	for m in t_map[piece]:
		disp_map[piece][m] = {}
		for b in t_map[piece][m]:
			disp_map[piece][m][b] = []
			for t in t_map[piece][m][b]:
				mod_t = [x for x in mod_set if x in t[1]]
				if mod_t:
					print('keep', m, b, t) 
					disp_t = (t[0], mod_t)
					disp_map[piece][m][b].append(disp_t)
	return disp_map
	


def tag_lyrics(s, piece, t_map):
	''' takes a stream and and a tag map, and annotates the stream with tag information '''
	class_filter = [layout.SystemLayout, layout.PageLayout]
	layout_trash = list(s.recurse().getElementsByClass(class_filter))
	s.remove(layout_trash, recurse=True)
	working_tags = {}
	lyric_dict = {1: 'blue', 2: 'purple', 3: 'green', 4:'black'}
	available_numbers = [1, 2, 3, 4]
	
	for m in t_map[piece]:
		for b in t_map[piece][m]:
			for t in t_map[piece][m][b]:
				print(t)
				if t[0] == "start":
					b_note = closest_bass(s, m, b)
					n_note = b_note.next('GeneralNote')
					if b_note.offset == n_note.offset:
						n_note = n_note.next('GeneralNote')
					lyric_num = min(available_numbers)
					t_text = " ".join(t[1])
					# first check if the note already has lyrics
					try:
						l = [x for x in b_note.lyrics if x.number == lyric_num][0]
						print (l)
						l.text = l.text + " " + "["
						working_tags[frozenset(t[1])] = lyric_num
						available_numbers.remove(lyric_num)
					except:
						to_add1 = note.Lyric(number = lyric_num, text = "[")
						to_add1.style.color = lyric_dict[lyric_num]
						b_note.lyrics.append(to_add1)
						working_tags[frozenset(t[1])] = lyric_num
						available_numbers.remove(lyric_num)
					to_add2 = note.Lyric(number = lyric_num, text = t_text)
					to_add2.style.color = lyric_dict[lyric_num]
					n_note.lyrics.append(to_add2)

				if t[0] == "end":
					lyric_text = ']'
					b_note = closest_bass(s, m, b)
					lyric_num = working_tags[frozenset(t[1])]
					try:
						l = [x for x in b_note.lyrics if x.number == lyric_num][0]
						l.text = l.text + " " + "]"
					except:
						to_add = note.Lyric(number = lyric_num, text = lyric_text, syllabic='end')
						to_add.style.color = lyric_dict[lyric_num]
						b_note.lyrics.append(to_add)
					del working_tags[frozenset(t[1])] 
					available_numbers.append(lyric_num)	
	return 


def create_exercise (piece, ex):
	return

def transpose_excerpt (ex, to_k, corp):
	''' Function to transpose a musical excerpt to the requested key
	Produces an excerpt 
	'''
	source_piece = ex.ex_info.piece
	source_stream = corp.search(source_piece)[0].parse()
	from_k = source_stream.analyze('key')
	if from_k.mode == to_k.mode:
		pass
	else:
		to_k = to_k.relative
	trans_ex = transpose_stream (ex.m21_stream, from_k, to_k)
	return M21Excerpt(m21_stream=trans_ex, ex_info=ex.ex_info)

def transpose_stream (ex, old_k, new_k):
	''' Function to transpose a stream to a given key 
	Takes a stream and two key objects '''
	tInterval = interval.Interval(old_k.tonic, new_k.tonic)
	#stream_transposed = copy.deepcopy(ex.transpose(tInterval))
	stream_transposed = ex.transpose(tInterval)
	return stream_transposed

def annotate_excerpt (m21ex, ex):
	''' Annotates an excerpt stream with useful information as tempo markings.
	Takes the music21excerpt, the excerpt tuple, and the set of tags'''
	piece_text = ex.piece + ", m." + str(ex.m_start) + "-m." + str(ex.m_end)
	t_text = " ".join(ex.t_list)
	m= m21ex.getElementsByClass('PartStaff')[0].getElementsByClass('Measure')[0]
	complete_text = piece_text + "\n" + t_text
	m.insert(0, tempo.MetronomeMark(complete_text))
	#m.insert(0, tempo.MetronomeMark(t_text))
	#m.insert(0, tempo.MetronomeMark(piece_text))
	
	'''n = m21ex.getElementsByClass('PartStaff')[1].recurse().notesAndRests[0]
	n.lyric = t_text
	n.addLyric(ex.piece, 2)
	'''
	return m21ex


def tags_in_piece (t_map, piece):
	''' Returns a list of tags within a given piece '''
	t_list = []
	for m in t_map[piece]:
		for b in t_map[piece][m]:
			for t in t_map[piece][m][b]:
				if t[0] == "start":
					t_list.append(frozenset(t[1]))
	return t_list

def choose_exs (t_dict, tset_list, piece=None):
	''' Takes a tag_dict and a list of sets of tags, a corpus, and optionally a piece. Returns a list of excerpts '''
	ex_list = []
	temp_dict = copy.deepcopy(t_dict)
	for s in tset_list:
		if piece:
			options = [o for o in temp_dict[s] if o.piece == piece]
		else:
			options = temp_dict[s]
		e = random.choice(options)
		temp_dict[s].remove(e)
		ex_list.append(e) 

	return ex_list

def random_tags(t_dict, n=None, tlist=None):
	tlist_out = []
	if tlist and n:
		for i in range(n):
			t = random.choice(tlist)
			options = [k for k in t_dict.keys() if t.issubset(k)]
			t_choice = random.choice(options)
			tlist_out.append(t_choice)
	elif tlist:
		for t in tlist:
			options = [k for k in t_dict.keys() if t.issubset(k)]
			t_choice = random.choice(options)
			tlist_out.append(t_choice)
	elif n:
		for i in range(n):
			t_choice = random.choice(list(t_dict.keys()))
			tlist_out.append(t_choice)
	else:
		n = random.randint(1, 5)
		for i in range(n):
			t_choice = random.choice(list(t_dict.keys()))
			tlist_out.append(t_choice)
	return tlist_out




def choose_tags_from_piece (t_map, piece, n=None, tlist=None):
	''' 
	Takes a tag_map, and a piece name. Optionally takes a number of tags to choose and a list of tagsets to look for.
	t_list is a list of sets of tags
	First, it creates a list of choices for the chosen tag
	Returns a list of tag_sets that DO appear at some point in the chosen piece.
	'''
	
	
	tag_set_choices = tags_in_piece(t_map, piece)
	print(tag_set_choices)
	tags = []
	if tlist and not n:
		for t in tlist:
			to_check = [ts for ts in tag_set_choices if t.issubset(tag_set_choices)]
			try:
				to_add = random.choice(to_check)
				tags.append(to_add)
				tag_set_choices.remove(to_add)
			except:
				raise Exception ("{tstring} is not in the piece.".format(tstring=t))
	elif tlist and n:
		for i in range(n):
			t = random.choice(tlist)
			to_check = [ts for ts in tag_set_choices if t.issubset(tag_set_choices)]
			try:
				to_add = random.choice(to_check)
				tags.append(to_add)
				tag_set_choices.remove(to_add)
			except:
				raise Exception ("{tstring} is not in the piece.".format(tstring=t))
	elif n:
		for i in range(n):
			t = random.choice(tag_set_choices)
			tags.append(t)
			tag_set_choices.remove(t)
	else:
		n = random.randint(1, 5)
		for i in range(n):
			t = random.choice(tag_set_choices)
			tags.append(t)
			tag_set_choices.remove(t)
	return tags


def excerpts_to_score (excerpts, title):
	''' Function to format a list of excerpts to good presentation
	Takes a list of excerpts and a title'''
	s = copy.deepcopy(excerpts[0].m21_stream)
	for e in excerpts[1:]:
		for ps_score, ps_excerpt in zip(s.getElementsByClass('PartStaff'), e.m21_stream.getElementsByClass('PartStaff')):
			for el in ps_excerpt:
				# print (ps_score, ps_excerpt, el)
				# if el in s.recurse():
				ps_score.append(copy.deepcopy(el))
	s.insert(0, metadata.Metadata())
	s.metadata.title = title
	return s

def add_key(ex, piece_key):
	''' Adds missing key elements to the measure objects in a given excerpt stream '''
	for ps in ex.getElementsByClass('PartStaff'):
		m = ps.getElementsByClass('Measure')[0]
		ks = m.getElementsByClass('Key')
		if not ks:
			m.insert(0, piece_key)
	return ex


def remove_layout (ex):
	''' removes any layout objects from the given stream. Alters stream in-place '''
	for el in ex.recurse():
		if isinstance(el, layout.SystemLayout) or isinstance(el, layout.StaffLayout) or isinstance(el, layout.PageLayout):
			ex.remove(el, recurse = True)
	return ex

def barline_cleanup (ex):
	''' removes any barlines in last bar and adds a final barline at the same spot '''
	for ps in ex.getElementsByClass('PartStaff'):
		m_last = ps.getElementsByClass('Measure')[-1]
		m_last.rightBarline = bar.Barline('final')
	return ex
#old1!!
def barline_cleanup_old (ex):
	''' removes any barlines in last bar and adds a final barline at the same spot '''
	for ps in ex.getElementsByClass('PartStaff'):
		m_last = ps.getElementsByClass('Measure')[-1]
		for elem in m_last:
			if isinstance(elem, bar.Barline):
				m_last.remove(elem)
		m_last.insert(m_last.highestTime, bar.Barline(type='final', location='right'))
	return ex

def excerpt_cleanup (s, b_start, b_end):
	''' Function to clean up an excerpt. Takes a score, a starting beat, and an ending beat, 
	and returns a new score starting and ending on the correct beats. 
	'''
	out = copy.deepcopy(s)
	for ps in out.getElementsByClass('PartStaff'):
		# determine the correct offset for the first complete measure
		m_offset = 6 - ((b_start - 1) * 2)
		for m in ps.getElementsByClass('Measure')[1:]:
			m.offset = m_offset
			m_offset = m_offset + 6.0
	ql_offset = (b_start - 1) * 2
	to_delete = []
	for ps in out.getElementsByClass('PartStaff'):
		# first, let's check that we're dealing with multiple measures
		if len(ps.getElementsByClass('Measure')) > 1:
			# now iterate over notes and rests in measure 0 
			for nr in ps.getElementsByClass('Measure')[0].recurse().notesAndRests:
				if nr.beat < b_start:
					to_delete.append(nr)
				if nr.beat >= b_start:
					nr.offset = ((nr.beat - 1) * 2) - ql_offset 	# correct the offset of the notes
			# now iterate over notes and rests in the last measure
			for nr in ps.getElementsByClass('Measure')[-1].recurse().notesAndRests:
				# print (ex.piece, m_start, m_end)
				if nr.beat > b_end:
					to_delete.append(nr)
		# if it's just one measure, then do something else!
		else:
			for nr in ps.getElementsByClass('Measure')[0].recurse().notesAndRests:
				if nr.beat < b_start:
					to_delete.append(nr)
				if nr.beat > b_end:
					to_delete.append(nr)
	out.remove(to_delete, recurse=True)
	return out

def excerpt_to_m21 (ex, corp, add_key=False):
	''' Takes an excerpt and generates a Music21Excerpt '''
	t_list = ex.t_list
	piece = corp.search(ex.piece)[0].parse()
	piece_key = piece.recurse().getElementsByClass('Key')[0]
	m_start = ex.m_start 
	m_end = ex.m_end 
	excerpt_unclean = piece.measures(m_start, m_end)
	excerpt = excerpt_cleanup(excerpt_unclean, ex.b_start, ex.b_end)
	excerpt = barline_cleanup(remove_layout(excerpt))
	# print(ex)
	if add_key:
		excerpt = add_key(excerpt, piece_key)
	excerpt = annotate_excerpt (excerpt, ex)
	#excerpt = remove_layout(excerpt)
	# excerpt = barline_cleanup(excerpt)
	m21_ex = M21Excerpt(m21_stream=excerpt, ex_info= ex)
	return m21_ex

def create_m21excerpts (ex_list, corp, add_key=False):
	''' takes a list of excerpts and a corpus, and creates a list of tuples of music21 excerpts (scores) 
	and information on those excerpts '''
	m21_ex_list = []	
	for ex in ex_list:
		m21_ex = excerpt_to_m21(ex, corp, add_key)
		m21_ex_list.append(m21_ex)
	return m21_ex_list

def t_set_find_all (t_set, t_dict, t_not = None):
	''' Given a set of tags, find all tag_sets that contain the subset.
		If t_not is given, then don't include tags that include elements of t_not
	'''
	set_list = []
	if not t_not:
		for k in t_dict.keys():
			if t_set.issubset(k):
				set_list.append(k)
	else:
		for k in t_dict.keys():
			if t_set.issubset(k) and not t_not.issubset(k):
				set_list.append(k)
	return set_list

def set_list_to_all_excerpts (s_list, t_dict):
	''' Returns a list of excerpts '''
	ex_list = []
	for s in s_list:
		for ex in t_dict[s]:
			ex_list.append(ex)
	return ex_list





def tagger (csvdir):	
	#Create a dictionary to store tags. Each key is a single tag, and links to a value which is a set of frozensets.
	tags = {}
	# Create a dictionary to store the tag map
	# tag_map = {'02Courante' : [m1, m2, etc.]}		m1 = [b1, 
	# m1 = [b1, b1.5 etc.]
	# bi = [('start', '1to3'),]
	# tag_map ['02Courante'][1][1] = [('start', '1to3'),]
	tag_map = {}
	for entry in os.scandir(csvdir):
		if entry.path.endswith(".csv"):
			df = pd.read_csv(entry.path, index_col='Measure')
			df.columns = [float(col) for col in df]
			#Switch columns and rows for easier indexing
			tag_df = df.transpose()
			# A dictionary of tags currently being worked on
			open_tags = {}
			# Get the name of the piece
			piece = entry.name[:-4]
			# Initialize the tag_map for the piece
			tag_map[piece] = []
			active_tags = []
			for m in tag_df:
				tag_map[piece].append([])
				for b in tag_df.index:
					tag_map[piece][-1].append([])
					tag_cell = tag_df[m][b]
					# Split the tags based on semicolons and whitespace
					# print (tag_cell)
					if not isinstance(tag_cell, float):
						tags_split_tofilter = [w.split(' ') for w in tag_cell.split('; ')]
						tags_split = [list(filter(None, l)) for l in tags_split_tofilter]
						for tag_group in tags_split:
							# Keep track of the tags in order
							tag_list = []

							for t in tag_group:
								# First check if the first character is a '/'
								if t[0] == '/':
									# Now check for a segue
									if t[1] == '/':
										# Figure out which tag to end
										tag = t[2:]
										# Add m_end and b_end to the appropriate open_tags dictionary entry
										open_tags[tag].update({'m_end': m, 'b_end': b})
										# Add the tag to the list so that we can refer to it later
										tag_list = [tag]

									# Deal with segues to a new tag	
									elif t[1] == '>':
										segue_tag = t[2:]
										# Add the 'segue_to' the open_tags dictionary entry
										open_tags[tag].update({'segue_to': segue_tag})
										# Now create an excerpt using info from the open_tags dictionary
										excerpt = Excerpt (piece = piece, m_start = open_tags[tag]['m_start'], b_start = open_tags[tag]['b_start'],
													   		m_end = open_tags[tag]['m_end'], b_end = open_tags[tag]['b_end'],
													   		t_list = open_tags[tag]['t_list'], segue_to = open_tags[tag]['segue_to'] )
										# Create a frozenset of tags to serve as the key for the dictionary
										tag_set = frozenset(open_tags[tag]['t_list'])
										# Add the excerpt to the dictionary. 
										if tag_set in tags:
											tags[tag_set].append(excerpt)
										else:
											tags[tag_set] = [excerpt]
										# Now remove the tag_set from the active tags
										active_tags.remove(tag_set)
										# Add an 'end' tag to the tag_map
										tag_map[piece][-1][-1].append(('end', tag_set))
										# Add a segue tag
										tag_map[piece][-1][-1].append('segue')
										# Remove the tag from the open_tags dictionary
										del open_tags[tag]
										# Add the segue_from to the open_tags dictionary
										if segue_tag not in open_tags:
											open_tags[segue_tag] = {}
										open_tags[segue_tag].update({'segue_from': tag})
										# Reset the tag_list for additional tags
										tag_list = [segue_tag]	
									# Deal with ending a tag without segue
									else:
										tag = t[1:]
										open_tags[tag].update({'m_end': m, 'b_end': b})
										excerpt = Excerpt (piece = piece, m_start = open_tags[tag]['m_start'], b_start = open_tags[tag]['b_start'],
													   		m_end = open_tags[tag]['m_end'], b_end = open_tags[tag]['b_end'],
													   		t_list = open_tags[tag]['t_list'])
										tag_set = frozenset(open_tags[tag]['t_list'])
										if tag_set in tags:
											tags[tag_set].append(excerpt)
										else:
											tags[tag_set] = [excerpt]
										# Now remove the tag_set from the active tags
										active_tags.remove(tag_set)
										# Add an 'end' tag to the tag_map
										tag_map[piece][-1][-1].append(('end', tag_set))
										# Now add any other active tags to the map
										for t in active_tags:
											tag_map[piece][-1][-1].append(t)
										del open_tags[tag]
										tag_list = []
								# If the first character isn't a special character, then just add the tag to the tag list
								else:
									tag = t
									tag_list.append(tag)
							if tag_list:
								if tag_list[0] not in open_tags:
									open_tags[tag_list[0]] = {}
								open_tags[tag_list[0]].update({'t_list': tag_list, 'm_start': m, 'b_start': b})
								# Add the start tags to the tag map
								for t in tag_list:
									tag_map[piece][-1][-1].append(('start', frozenset(tag_list)))
								# Now add any other active tags to the map
								for t in active_tags:
									tag_map[piece][-1][-1].append(t)
								# Now add the new tagset to the list of active tags
								active_tags.append(frozenset(tag_list))

					else:
						for t in active_tags:
							tag_map[piece][-1][-1].append(t)

	return (tags, tag_map)	
						
def tagger2 (csvdir):	
	# implements tag_map as a dictionary of dictionaries!!!
	#Create a dictionary to store tags. Each key is a single tag, and links to a value which is a set of frozensets.
	tags = {}
	'''
	Create a dictionary to store the tag map
	# tag_map = {'02Courante' : 0 : {1 : tags }}
	tag_map['02Courante'] = {0: }
	tag_map['02Courante'][0] = {1: tags, 1.5: tags, etc.}
	# m1 = [b1, b1.5 etc.]
	# bi = [('start', '1to3'),]
	# tag_map ['02Courante'][1][1] = [('start', '1to3'),]
	'''
	tag_map = {}
	unique_tags = []
	for entry in os.scandir(csvdir):
		if entry.path.endswith(".csv"):
			df = pd.read_csv(entry.path, index_col='Measure')
			df.columns = [float(col) for col in df]
			#Switch columns and rows for easier indexing
			tag_df = df.transpose()
			# A dictionary of tags currently being worked on
			open_tags = {}
			# Get the name of the piece
			piece = entry.name[:-4]
			# Initialize the tag_map for the piece
			tag_map[piece] = {}
			active_tags = []
			print (piece)
			for m in tag_df:
				tag_map[piece][m] = {}
				for b in tag_df.index:
					tag_map[piece][m][b] = []
					print(piece, m, b)
					tag_cell = tag_df[m][b]
					# Split the tags based on semicolons and whitespace
					# print (tag_cell)
					if not isinstance(tag_cell, float):
						tags_split_tofilter = [w.split(' ') for w in tag_cell.split('; ')]
						tags_split = [list(filter(None, l)) for l in tags_split_tofilter]
						for tag_group in tags_split:
							# Keep track of the tags in order
							tag_list = []
							# print (tag_group)
							for t in tag_group:
								# First check if the first character is a '/'
								if t[0] == '/':
									# Now check for a segue
									if t[1] == '/':
										# Figure out which tag to end
										tag = t[2:]
										# Add m_end and b_end to the appropriate open_tags dictionary entry
										open_tags[tag].update({'m_end': m, 'b_end': b})
										# Add the tag to the list so that we can refer to it later
										tag_list = [tag]

									# Deal with segues to a new tag	
									elif t[1] == '>':
										segue_tag = t[2:]
										# Add the 'segue_to' the open_tags dictionary entry
										open_tags[tag].update({'segue_to': segue_tag})
										# Now create an excerpt using info from the open_tags dictionary
										excerpt = Excerpt (piece = piece, m_start = open_tags[tag]['m_start'], b_start = open_tags[tag]['b_start'],
													   		m_end = open_tags[tag]['m_end'], b_end = open_tags[tag]['b_end'],
													   		t_list = open_tags[tag]['t_list'], segue_to = open_tags[tag]['segue_to'] )
										# Create a frozenset of tags to serve as the key for the dictionary
										tag_set = frozenset(open_tags[tag]['t_list'])
										# Add the excerpt to the dictionary. 
										if tag_set in tags:
											tags[tag_set].append(excerpt)
										else:
											tags[tag_set] = [excerpt]
										# Now remove the tag_set from the active tags
										active_tags.remove(open_tags[tag]['t_list'])
										# Add an 'end' tag to the tag_map
										tag_map[piece][m][b].append(('end', open_tags[tag]['t_list']))
										# Add a segue tag
										tag_map[piece][m][b].append(('segue',['segue']))
										# Remove the tag from the open_tags dictionary
										del open_tags[tag]
										# Add the segue_from to the open_tags dictionary
										if segue_tag not in open_tags:
											open_tags[segue_tag] = {}
										open_tags[segue_tag].update({'segue_from': tag})
										# Reset the tag_list for additional tags
										tag_list = [segue_tag]	
									# Deal with ending a tag without segue
									else:
										tag = t[1:]
										open_tags[tag].update({'m_end': m, 'b_end': b})
										excerpt = Excerpt (piece = piece, m_start = open_tags[tag]['m_start'], b_start = open_tags[tag]['b_start'],
													   		m_end = open_tags[tag]['m_end'], b_end = open_tags[tag]['b_end'], t_list = open_tags[tag]['t_list'])
										tag_set = frozenset(open_tags[tag]['t_list'])
										if tag_set in tags:
											tags[tag_set].append(excerpt)
										else:
											tags[tag_set] = [excerpt]
										# Now remove the tag_set from the active tags
										active_tags.remove(open_tags[tag]['t_list'])
										# Add an 'end' tag to the tag_map
										tag_map[piece][m][b].append(('end', open_tags[tag]['t_list']))
										# Now add any other active tags to the map
										for t in active_tags:
											tag_map[piece][m][b].append(('continue', t))
										del open_tags[tag]
										tag_list = []
								# If the first character isn't a special character, then just add the tag to the tag list
								else:
									tag = t
									tag_list.append(tag)
								# Add the tag to the list of all unique tags, if it's not already there.
								if tag not in unique_tags:
									unique_tags.append(tag)
							if tag_list:
								if tag_list[0] not in open_tags:
									open_tags[tag_list[0]] = {}
								open_tags[tag_list[0]].update({'t_list': tag_list, 'm_start': m, 'b_start': b})
								# print (str(m), str(b),(open_tags))
								# print(tag_list)
								# Add the start tags to the tag map
								'''
								for t in tag_list:
									tag_map[piece][m][b].append(('start', frozenset(tag_list)))
								'''
								tag_map[piece][m][b].append(('start', tag_list))
								# Now add any other active tags to the map
								for t in active_tags:
									tag_map[piece][m][b].append(('continue', t))
								# Now add the new tagset to the list of active tags
								active_tags.append(tag_list)

					else:
						for t in active_tags:
							tag_map[piece][m][b].append(('continue', t))
			# Raise an exception if there are tags that never ended.
			if active_tags:
				tag_string = ", and ".join([', '.join(t) for t in active_tags])
				raise Exception ("{p} contains the following open tags: {t}".format(p=piece, t=tag_string))
	return (tags, tag_map, unique_tags)	

'''
# test function to create an excerpt stream
def testing(s, b_start, b_end):
	out = copy.deepcopy(s)
	for ps in out.getElementsByClass('PartStaff'):
		m_number = 0
		# determine the correct offset for the first complete measure
		m_offset = 6 - ((b_start - 1) * 2)
		for m in ps.getElementsByClass('Measure'):
			m.number = m_number
			m_number = m_number + 1
			# set the measure offset to 0 for the first measure
			if m.number == 0:
				m.offset = 0
			# and otherwise, set the offset to the correct number and increment
			else:
				m.offset = m_offset
				m_offset = m_offset + 6.0
	m0 = out.measure(0)
	to_delete = []
	# now iterate over notes and rests in measure 0 
	for ps in out.getElementsByClass('PartStaff'):
		for nr in ps.getElementsByClass('Measure')[0].recurse().notesAndRests:
			if nr.beat < b_start:
				to_delete.append(nr)
			if nr.beat >= b_start:
				nr.offset = ((nr.beat - 1) * 2) - 4 	# correct the offset of the notes
	m0.remove(to_delete, recurse=True)

	# now iterate over notes and rests in the last measure
	to_delete = []
	for ps in out.getElementsByClass('PartStaff'):
		for nr in ps.getElementsByClass('Measure')[-1].recurse().notesAndRests:
			if nr.beat > b_end:
				to_delete.append(nr)
	out.remove(to_delete, recurse=True)


	# for m in m0.recurse().getElementsByClass('Measure'):
		# m.padAsAnacrusis(useInitialRests=True)
	return out
'''

'''
t_dict = tagger('Tags')[0]
t_list = ['cad']
t_set = set(t_list)
excerpts = create_excerpts(t_set, t_dict, chamb)
'''

piece = "02Courante"
tags = tagger2('Tags')
t_dict = tags[0]
t_map = tags[1]
import pprint
pp = pprint.PrettyPrinter(indent=4)
# pp.pprint(testtags)
unique = tags[2]
t_list = ['att']
t_set = set(t_list)
s_list = t_set_find_all (t_set, t_dict, {'doux'})
ex_list = set_list_to_all_excerpts (s_list, t_dict)
excerpts = create_m21excerpts(ex_list, chamb)

'''t
2 = choose_tags_from_piece (t_map, piece)
e2 = tags_to_random_excerpts (t2, t_dict)
excerpts2 = create_excerpts(e2, t_dict, chamb)
s2 = excerpts_to_score(excerpts2, "test")

t3 = choose_tags_from_piece (t_map, piece, n=5)
e3 = tags_to_excerpts (t3, t_dict, piece)
excerpts3 = create_excerpts(e3, t_dict, chamb)
s3 = excerpts_to_score(excerpts3, "Courante02")
'''

'''
test1 = excerpts[0][0]
test2 = score_left_hand(test1).getElementsByClass('PartStaff')[0]
test3 = stream.Part()
for elem in test2:
	test3.append(elem)
for m in test3.recurse().getElementsByClass('Measure'):
	m.offset = m.offset + 12
#test1.insert(12,test3)
test4 = stream.Part()
s = converter.parse('tinyNotation: 4/4 C4 D4 E4 F4 G4 A4 B4 c4')
# s2 = s.getElementsByClass('Part')[0]
# test4.insert(0, s)
test1.insert(12, s)
'''

def tags_to_excerpts (t_list, t_dict, piece):
	''' Takes a list of tag sets, a tag dictionary, and the piece. 
	Returns a list of excerpts chosen randomly from the piece corresponding to the tag sets.
	'''
	excerpts = []
	for t in t_list:
		ex_choices = []
		for ex in t_dict[t]:
			if ex.piece == piece:
				if ex not in excerpts:
					ex_choices.append(ex)
		ex_choice = random.choice(ex_choices)
		excerpts.append(ex_choice)
	return excerpts


def tag_to_random_excerpt (t, t_dict):
	''' Chooses one excerpt at random. Takes a tag (t) and a t_dict '''
	ex = random.choice(t_dict[t])
	return ex

def tags_to_random_excerpts (t_list, t_dict):
	''' Returns a list of excerpts, chosen randomly from t_dict '''
	excerpts = [tag_to_random_excerpt(t, t_dict) for t in t_list]
	return excerpts


