from music21 import *
from Markov import *
from tail_recursion import *
import random
import copy
import collections
MeasureTuple = collections.namedtuple('MeasureTuple', 'm_stream k_object')
Condition = collections.namedtuple('Condition', 'pos property')
MeasureState = collections.namedtuple('MeasureState', 'sd fb tonic form_function')
chamb = corpus.corpora.LocalCorpus('chambonnieres')
chamb1Piece = chamb.search('02')[0].parse()
chamb1Corpus = chamb.search('02')

testKey = key.Key('a')

import numpy as np

def filter_measure_same_pitch(s):
	m = filterMeasure(s)
	for elem in m.recurse().notes:
		elem.pitch = pitch.Pitch('C-4')
	return m


#Filters a measure to return just note, rest, and voice objects
def filterMeasure (s):
	newStream = stream.Measure()
	for elem in s:
		if isinstance (elem, note.Note) or isinstance (elem, note.Rest) or isinstance (elem, stream.Voice):
			# newStream.insert(0, elem)
			newStream.insert(elem)
	newStream.number = s.number
	return newStream

# returns a measure containing just a downbeat
def filterDownbeat (s):
	newStream = stream.Measure(id='2')
	for elem in s.getElementsByOffset(0.0, 2.0):
		if isinstance (elem, note.Note) or isinstance (elem, note.Rest):
			newStream.insert(0,elem)
		elif isinstance (elem, stream.Voice):
			voiceStream = stream.Voice(id=elem.id)
			for voiceElem in elem.getElementsByOffset(0.0, 2.0):
				voiceStream.insert(0, voiceElem)
			newStream.insert(0, voiceStream)

	return newStream

# Returns a single chord to be analyzed by figured bass
# Takes a measure, and a desired offset
def beatToChord (b, o):
	beatChord = b.chordify().recurse().getElementsByClass('Chord').getElementsByOffset(o)
	return beatChord


def getFigures (chordA):
	fb = ""
	allIntervals = chordA.annotateIntervals(returnList=True)
	if '6' in allIntervals:
		fb = "6"
	else:
		fb = "5"
	return fb

def getLocalTonic (keyMain, keyLocal):
	# Figure out the interval 
	keyLocalTonicPitch = keyLocal.pitchFromDegree(1)
	localTonic = keyMain.getScaleDegreeAndAccidentalFromPitch(keyLocalTonicPitch)
	return localTonic

def measurePlusDownbeat (measureA, measureB):
	newScore = stream.Score()
	staff1 = stream.PartStaff(id="rightHand")
	staff2 = stream.PartStaff(id="leftHand")
	for elem in measureA.getElementsByClass('PartStaff')[0]:
		staff1.append(elem)
	for elem in measureA.getElementsByClass('PartStaff')[1]:
		staff2.append(elem)
	
	staff1.append(filterDownbeat(measureB.recurse().getElementsByClass('Measure')[0]))
	staff2.append(filterDownbeat(measureB.recurse().getElementsByClass('Measure')[1]))
	newScore.insert(0, staff1)
	newScore.insert(0, staff2)

	return newScore

def make_transition_possibilities (corp, desiredMode):
	courantePossibilities = {}
	couranteCorpus = corp.search('courante')
	couranteList = []
	for c in couranteCorpus:
		# Parse the piece and get its main key
		courante = c.parse()
		mainKeyMode = courante.analyze('key').mode
		if mainKeyMode == desiredMode:
			couranteList.append(c)	
	for c in couranteList:
		courante = c.parse()
		mainKey = courante.analyze('key')
		# Loop through each measure in the piece
		mNumber = len(courante.parts[0].getElementsByClass('Measure'))
		for m in range(1, mNumber):
			print (m)
			# If its not the first measure, then we get the "local" tonic of the bar
			# Do this by analyzing the key of the previous bar up until the downbeat.
			if m > 1:
				mPrevious = measurePlusDownbeat(courante.measure(m-1), courante.measure(m))
				localStartKey = mPrevious.analyze('key')
				mCurrentTonic = getLocalTonic(mainKey, localStartKey)
			else:	
				mCurrentTonic = (1, None)
			# Now get the current measure's starting SD and figures
			mCurrent = courante.measure(m).recurse().notes
			mCurrentDownBeat = mCurrent.getElementsByOffset(0.0)
			mCurrentDownBeatPitches = mCurrentDownBeat.pitches
			mCurrentSD = mainKey.getScaleDegreeAndAccidentalFromPitch(min(mCurrentDownBeatPitches))
			mCurrentFB = getFigures(beatToChord(courante.measure(m), 0.0)[0])
			
			# Get the barlines to check if it's a final bar
			barlines = courante.measure(m).recurse().getElementsByClass('Barline')
			if barlines and (barlines[0].style == 'final'):
				mNextSD = None
				mNextFB = None
				mNextTonic = None
				mCurrentFunction = "Closing"
				mNextFunction = "END"
				
			# Otherwise, get the next bar too, and check its bar lines
			else:	
				mNext = courante.measure(m+1).recurse().notes
				barlinesNext = courante.measure(m+1).recurse().getElementsByClass('Barline')
				barlinesNextNext = courante.measure(m+2).recurse().getElementsByClass('Barline')
				mNextBeat = mNext.getElementsByOffset(0.0)
				mNextBeatPitches = mNextBeat.pitches
				mNextSD = mainKey.getScaleDegreeAndAccidentalFromPitch(min(mNextBeatPitches))
				mNextFB = getFigures(beatToChord(courante.measure(m+1), 0.0)[0])
				mCurrentPlusDownBeat = measurePlusDownbeat(courante.measure(m), courante.measure(m+1))
				localEndKey = mCurrentPlusDownBeat.analyze('key')
				mNextTonic = getLocalTonic(mainKey, localEndKey)
				if barlinesNext:
					mNextFunction = "Closing"
					mCurrentFunction = "Cad"
				else:
					if barlinesNextNext:
						mNextFunction = "Cad"
					else: 
						mNextFunction = None
					if barlines and (barlines[0].style == 'double'):
						mCurrentFunction = "Closing"
					# Set the function to "Opening" if it's the first bar
					elif m == 1:
						mCurrentFunction = "Opening"
					else:
						mCurrentFunction = None
						
			# Assemble the key for the dictionary entry
			dictKey = MeasureState(mCurrentSD, mCurrentFB, mCurrentTonic, mCurrentFunction)
			if dictKey in courantePossibilities:
				courantePossibilities[dictKey].append(MeasureState(mNextSD, mNextFB, mNextTonic, mNextFunction))
			else:
				courantePossibilities[dictKey] = [MeasureState(mNextSD, mNextFB, mNextTonic, mNextFunction)]
			courantePossibilities[MeasureState(None, None, None, "END")] = [MeasureState(None, None, None, None)]
			courantePossibilities[MeasureState(None, None, None, None)] = [MeasureState(None, None, None, None)]
	return courantePossibilities

def convert_Unpitched (n):
	nr = note.Unpitched()
	nr.quarterLength = n.quarterLength
	return nr


def ps_rhythms(s):
	""" Takes a PartStaff and returns a percussion Part"""
	newPart = stream.PartStaff()
	perc = clef.PercussionClef()
	ts = s.recurse().getElementsByClass(meter.TimeSignature)[0]
	sl = layout.StaffLayout(distance=3, staffNumber=1, staffLines=1)
	m = s.getElementsByClass('Measure')[0]
	tempMeasure = filter_measure_same_pitch(m)
	tempMeasure.insert(0, sl)
	tempMeasure.insert(0, perc)
	tempMeasure.insert(0, ts)
	tempMeasure.number = m.number
	newPart.append(tempMeasure)
	for m in s.getElementsByClass('Measure')[1:]:
		'''
		tempMeasure = stream.Measure()
		print (m)
		for el in m.recurse().notesAndRests:
			tempMeasure.append(el)
		newPart.append(tempMeasure)
		'''
		tempMeasure = filter_measure_same_pitch(m)
		tempMeasure.number = m.number
		newPart.append(tempMeasure)
	return newPart


def score_rhythms(s):
	out = copy.deepcopy(s)
	treble_ps = out.getElementsByClass('PartStaff')[0]
	rhythm_ps = ps_rhythms(treble_ps)
	bass_ps = out.getElementsByClass('PartStaff')[1]
	out.remove(treble_ps)
	out.remove(bass_ps)
	out.insert(rhythm_ps)
	out.insert(bass_ps)
	return out

def score_left_hand(s):
	out = copy.deepcopy(s)
	out.remove(out.getElementsByClass('PartStaff')[0])
	return out

def score_bass(s):
	out = copy.deepcopy(s)
	out.remove(out.getElementsByClass('PartStaff')[0])
	out = out.chordify()
	chords = out.recurse().getElementsByClass('Chord')
	for c in range(len(chords)):
		
		thisChord = chords[c]
		lowestNote = note.Note(thisChord.bass())
		lowestNote.quarterLength = thisChord.quarterLength

		if thisChord[0].tie:
			
			if thisChord[0].tie.type == 'start':
				lowestNote.tie = tie.Tie('start')
			elif thisChord[0].tie.type == 'continue':
				lowestNote.tie = tie.Tie('continue')
			elif thisChord[0].tie.type == 'stop':
				lowestNote.tie = tie.Tie('stop')
		lowestNote.quarterLength = thisChord.quarterLength
		thisChord.activeSite.replace(thisChord, lowestNote)
	
	return out.stripTies(retainContainers=True)

def score_rhythm_and_bass(s):
	out = copy.deepcopy(s)
	treble_ps = out.getElementsByClass('PartStaff')[0]
	rhythm_ps = ps_rhythms(out.getElementsByClass('PartStaff')[0])
	lh = out.getElementsByClass('PartStaff')[1]
	bass = copy.deepcopy(s).getElementsByClass('PartStaff')[1].chordify()
	chords = bass.recurse().getElementsByClass('Chord')
	for c in range(len(chords)):
		
		thisChord = chords[c]
		lowestNote = note.Note(thisChord.bass())
		lowestNote.quarterLength = thisChord.quarterLength

		if thisChord[0].tie:
			
			if thisChord[0].tie.type == 'start':
				lowestNote.tie = tie.Tie('start')
			elif thisChord[0].tie.type == 'continue':
				lowestNote.tie = tie.Tie('continue')
			elif thisChord[0].tie.type == 'stop':
				lowestNote.tie = tie.Tie('stop')
		lowestNote.quarterLength = thisChord.quarterLength
		thisChord.activeSite.replace(thisChord, lowestNote)

	out.remove(treble_ps)
	out.remove(lh)
	out.insert(rhythm_ps)
	out.insert(bass.stripTies(retainContainers=True))
	return out

def score_bass_rhythm(s):
	out = copy.deepcopy(s)
	rhythm_ps = ps_rhythms(out.getElementsByClass('PartStaff')[0])
	out.replace(out.getElementsByClass('PartStaff')[0], rhythm_ps)
	left_hand = out
	return out

def scoreGoals():
	return None

def analyze_piece(c):
	courante_analysis = []
	courante = c.parse()
	mainKey = courante.analyze('key')
	# Loop through each measure in the piece
	mNumber = len(courante.parts[0].getElementsByClass('Measure'))
	for m in range(1, mNumber):
		# If its not the first measure, then we get the "local" tonic of the bar
		# Do this by analyzing the key of the previous bar up until the downbeat.
		if m > 1:
			mPrevious = measurePlusDownbeat(courante.measure(m-1), courante.measure(m))
			localStartKey = mPrevious.analyze('key')
			mCurrentTonic = getLocalTonic(mainKey, localStartKey)
		else:	
			mCurrentTonic = (1, None)
		# Now get the current measure's starting SD and figures
		mCurrent = courante.measure(m).recurse().notes
		mCurrentDownBeat = mCurrent.getElementsByOffset(0.0)
		mCurrentDownBeatPitches = mCurrentDownBeat.pitches
		mCurrentSD = mainKey.getScaleDegreeAndAccidentalFromPitch(min(mCurrentDownBeatPitches))
		mCurrentFB = getFigures(beatToChord(courante.measure(m), 0)[0])
		
		# Get the barlines to check if it's a final bar
		barlines = courante.measure(m).recurse().getElementsByClass('Barline')
		if barlines and (barlines[0].style == 'final'):
			mNextSD = None
			mNextFB = None
			mNextTonic = None
			mCurrentFunction = "Closing"
			mNextFunction = "END"
			
		# Otherwise, get the next bar too, and check its bar lines
		else:	
			mNext = courante.measure(m+1).recurse().notes
			barlinesNext = courante.measure(m+1).recurse().getElementsByClass('Barline')
			barlinesNextNext = courante.measure(m+2).recurse().getElementsByClass('Barline')
			mNextBeat = mNext.getElementsByOffset(0.0)
			mNextBeatPitches = mNextBeat.pitches
			mNextSD = mainKey.getScaleDegreeAndAccidentalFromPitch(min(mNextBeatPitches))
			mNextFB = getFigures(beatToChord(courante.measure(m+1), 0)[0])
			mCurrentPlusDownBeat = measurePlusDownbeat(courante.measure(m), courante.measure(m+1))
			localEndKey = mCurrentPlusDownBeat.analyze('key')
			mNextTonic = getLocalTonic(mainKey, localEndKey)
			if barlinesNext:
				mNextFunction = "Closing"
				mCurrentFunction = "Cad"
			else:
				if barlinesNextNext:
					mNextFunction = "Cad"
				else: 
					mNextFunction = None
				if barlines and (barlines[0].style == 'double'):
					mCurrentFunction = "Closing"
					

				# Set the function to "Opening" if it's the first bar
				elif m == 1:
					mCurrentFunction = "Opening"
				else:
					mCurrentFunction = None
					
		# Assemble the key for the dictionary entry
		dictKey = MeasureState(mCurrentSD, mCurrentFB, mCurrentTonic, mCurrentFunction)
		dictKey2 = MeasureState(mNextSD, mNextFB, mNextTonic, mNextFunction)
		courante_analysis.append((dictKey, dictKey2))
	return courante_analysis

def alternative_piece(piece, modules_original, k1):
	piece_analysis = analyze_piece(piece)
	modules = copy.deepcopy(modules_original)
	new_piece = stream.Score(id='courante')
	staff1 = stream.PartStaff(id="rightHand")
	staff2 = stream.PartStaff(id="leftHand")
	m_count = 1
	state1 = piece_analysis[0][0]
	state2 = piece_analysis[0][1]
	m_original = random.choice(modules[state1][state2])
	modules[state1][state2].remove(m_original)
	m = transpose_measure(m_original, k1)
	for el in m.recurse().getElementsByClass('Measure'):
		el.number = m_count
	# Setting up the structure of each PartStaff by copying the structure of the
	# first measure
	for elem in m.getElementsByClass('PartStaff')[0]:
		elem.keySignature = k1
		staff1.append(elem)
	for elem in m.getElementsByClass('PartStaff')[1]:
		elem.keySignature = k1
		staff2.append(elem)

	for elem in piece_analysis[1:]:
		m_count = m_count + 1
		state1 = elem[0]
		state2 = elem[1]
		m_original = random.choice(modules[state1][state2])
		modules[state1][state2].remove(m_original)
		m = transpose_measure(m_original, k1)
		for el in m.recurse().getElementsByClass('Measure'):
			el.number = m_count
		staff1.append(filterMeasure(m.recurse().getElementsByClass('Measure')[0]))
		staff2.append(filterMeasure(m.recurse().getElementsByClass('Measure')[1]))
	new_piece.insert(0, staff1)
	new_piece.insert(0, staff2)
	return new_piece


def makeModules (corp, desired_mode):
	couranteModules = {}
	couranteCorpus = corp.search('courante')
	for c in couranteCorpus:
		# Parse the piece and get its main key
		courante = c.parse()
		mainKey = courante.analyze('key')
		if mainKey.mode == desired_mode:
			# Loop through each measure in the piece
			mNumber = len(courante.parts[0].getElementsByClass('Measure'))
			for m in range(1, mNumber):
				# If its not the first measure, then we get the "local" tonic of the bar
				# Do this by analyzing the key of the previous bar up until the downbeat.
				if m > 1:
					mPrevious = measurePlusDownbeat(courante.measure(m-1), courante.measure(m))
					localStartKey = mPrevious.analyze('key')
					mCurrentTonic = getLocalTonic(mainKey, localStartKey)
				else:	
					mCurrentTonic = (1, None)
				# Now get the current measure's starting SD and figures
				mCurrent = courante.measure(m).recurse().notes
				mCurrentDownBeat = mCurrent.getElementsByOffset(0.0)
				mCurrentDownBeatPitches = mCurrentDownBeat.pitches
				mCurrentSD = mainKey.getScaleDegreeAndAccidentalFromPitch(min(mCurrentDownBeatPitches))
				mCurrentFB = getFigures(beatToChord(courante.measure(m), 0)[0])
				
				# Get the barlines to check if it's a final bar
				barlines = courante.measure(m).recurse().getElementsByClass('Barline')
				if barlines and (barlines[0].style == 'final'):
					mNextSD = None
					mNextFB = None
					mNextTonic = None
					mCurrentFunction = "Closing"
					mNextFunction = "END"
					
				# Otherwise, get the next bar too, and check its bar lines
				else:	
					mNext = courante.measure(m+1).recurse().notes
					barlinesNext = courante.measure(m+1).recurse().getElementsByClass('Barline')
					barlinesNextNext = courante.measure(m+2).recurse().getElementsByClass('Barline')
					mNextBeat = mNext.getElementsByOffset(0.0)
					mNextBeatPitches = mNextBeat.pitches
					mNextSD = mainKey.getScaleDegreeAndAccidentalFromPitch(min(mNextBeatPitches))
					mNextFB = getFigures(beatToChord(courante.measure(m+1), 0)[0])
					mCurrentPlusDownBeat = measurePlusDownbeat(courante.measure(m), courante.measure(m+1))
					localEndKey = mCurrentPlusDownBeat.analyze('key')
					mNextTonic = getLocalTonic(mainKey, localEndKey)
					if barlinesNext:
						mNextFunction = "Closing"
						mCurrentFunction = "Cad"
					else:
						if barlinesNextNext:
							mNextFunction = "Cad"
						else: 
							mNextFunction = None
						if barlines and (barlines[0].style == 'double'):
							mCurrentFunction = "Closing"
							

						# Set the function to "Opening" if it's the first bar
						elif m == 1:
							mCurrentFunction = "Opening"
						else:
							mCurrentFunction = None
							
				# Assemble the key for the dictionary entry
				dictKey = MeasureState(mCurrentSD, mCurrentFB, mCurrentTonic, mCurrentFunction)
				dictKey2 = MeasureState(mNextSD, mNextFB, mNextTonic, mNextFunction)
				if dictKey in couranteModules:
					if dictKey2 in couranteModules[dictKey]:
						couranteModules[dictKey][dictKey2].append(MeasureTuple(m_stream = courante.measure(m), k_object = mainKey))
					else:
						couranteModules[dictKey][dictKey2] = [MeasureTuple(m_stream = courante.measure(m), k_object = mainKey)]
					
				else:
					couranteModules[dictKey] = {}
					couranteModules[dictKey][dictKey2] = [MeasureTuple(m_stream = courante.measure(m), k_object = mainKey)]
				
	return couranteModules

@tail_recursive
def make_reprise (chain, modules_stable, modules_reprise, k1, origin_state, conditions):
	modules = copy.deepcopy(modules_reprise)
	state2 = origin_state
	mList = []
	for i in range(4):
		state1 = state2
		state2 = chain.next_state(state1)
		# Try to get a bar, but reset the dictionary if necessary
	
		try:
			m_original = random.choice(modules[state1][state2])
		except IndexError:
			recurse (chain, modules_stable, modules_reprise, k1, origin_state, conditions) 
			'''
			print ("First section:", modules[state1][state2], " : ", modules_stable[state1][state2])
			modules[state1][state2] = modules_stable[state1][state2]
			print(state1)
			print(state2)
			print (modules[state1][state2])
			m_original = random.choice(modules[state1][state2])
			'''
		# Destructively remove the bar just used
		modules[state1][state2].remove(m_original)
		m = transpose_measure(m_original, k1)
		mList.append(m)
		if state2.form_function == "Closing":
			#print("First section")
			recurse (chain, modules_stable, modules_reprise, k1, origin_state, conditions) 
	for i in range (6):
		state1 = state2
		state2 = chain.steer_state(state1, conditions)
		# Try to get a bar, but reset the dictionary if necessary
		
		try:
			m_original = random.choice(modules[state1][state2])
		except IndexError:
			recurse (chain, modules_stable, modules_reprise, k1, origin_state, conditions) 
			'''
			print ("Second section:", modules[state1][state2], " : ", modules_stable[state1][state2])
			modules[state1][state2] = modules_stable[state1][state2]
			print(state1)
			print (modules[state1][state2])
			m_original = random.choice(modules[state1][state2])
			'''
		# Destructively remove the bar just used
		modules[state1][state2].remove(m_original)
		m = transpose_measure(m_original, k1)
		mList.append(m)
		if (all ((state1[condition.pos] == condition.property ) for condition in conditions)):
			#print("Second section")
			#print(mList)
			return (mList, state2, modules)
		elif state1.form_function == "Closing":
			recurse (chain, modules_stable, modules_reprise, k1, origin_state, conditions) 
	if state1.form_function != "Closing":
		recurse (chain, modules_stable, modules_reprise, k1, origin_state, conditions) 
	else:
		return (mList, state2, modules)

def makeCourante (chain, modules_permanent, k1):
	modules = copy.deepcopy(modules_permanent)
	modules_original = copy.deepcopy(modules_permanent)
	piece = stream.Score(id='courante')
	staff1 = stream.PartStaff(id="rightHand")
	staff2 = stream.PartStaff(id="leftHand")
	state1 = ((1, None), '5', (1,None), 'Opening')
	state2 = chain.next_state(state1)
	m_original = random.choice(modules[state1][state2])
	modules[state1][state2].remove(m_original)
	m = transpose_measure(m_original, k1)
	# Setting up the structure of each PartStaff by copying the structure of the
	# first measure
	for elem in m.getElementsByClass('PartStaff')[0]:
		elem.keySignature = k1
		staff1.append(elem)
	for elem in m.getElementsByClass('PartStaff')[1]:
		elem.keySignature = k1
		staff2.append(elem)
	# Setting up the first reprise
	state1 = state2
	conditions = [Condition(pos = 3, property = "Closing"), Condition(pos=2, property=(3, None))]
	first_reprise = make_reprise(chain, modules_original, modules, k1, state1, conditions)
	state1 = first_reprise[1]
	modules = first_reprise[2]
	mList = first_reprise[0]
	m_count = 1
	for m in mList:
		for el in m.recurse().getElementsByClass('Measure'):
			el.number = m_count
		m_count = m_count + 1
	for m in mList:
		staff1.append(filterMeasure(m.recurse().getElementsByClass('Measure')[0]))
		staff2.append(filterMeasure(m.recurse().getElementsByClass('Measure')[1]))

	
	# Second reprise
	conditions = [Condition(pos = 3, property = "Closing"), Condition(pos=0, property=(1, None))]
	second_reprise = make_reprise(chain, modules_original, modules, k1, state1, conditions)
	state1 = second_reprise[1]
	modules = second_reprise[2]
	mList = second_reprise[0]
	for m in mList:
		for el in m.recurse().getElementsByClass('Measure'):
			el.number = m_count
		m_count = m_count + 1
	for m in mList:
		staff1.append(filterMeasure(m.recurse().getElementsByClass('Measure')[0]))
		staff2.append(filterMeasure(m.recurse().getElementsByClass('Measure')[1]))

	piece.insert(0, staff1)
	piece.insert(0, staff2)
	return piece

def transpose_measure (m, k):
	# determine the interval of transposition
	tInterval = interval.Interval(m.k_object.tonic, k.tonic)
	m_transposed = m.m_stream.transpose(tInterval)
	# Here's the MUTATION, removing the dictionary element we've already used!
	# modules[(startSD, function, k1.mode)].remove(mTuple)
	return m_transposed

def makeCatalogue (mList):
	piece = stream.Score(id='courante')
	staff1 = stream.PartStaff(id="rightHand")
	staff2 = stream.PartStaff(id="leftHand")
	for m in mList:
		staff1.append((m[0].recurse().getElementsByClass('Measure')[0]))
		staff2.append((m[0].recurse().getElementsByClass('Measure')[1]))
	piece.insert(0, staff1)
	piece.insert(0, staff2)
	return piece



a = make_transition_possibilities (chamb, 'minor')
b = create_transition_prob(a)
chain = MarkovChain(b)
# m = makeModules(chamb1Corpus, 'minor')
m = makeModules(chamb, 'minor')

