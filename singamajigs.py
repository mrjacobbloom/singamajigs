import json
import random
import midi
import math
import random

class _NoteInstance:
    def __init__(self, songIndex, noteIndex, noteObj):
        self.songIndex = songIndex
        self.noteIndex = noteIndex
        self.noteObj = noteObj
        self.pitch = noteObj['pitch']
        

class _Globals:
    # enum the costs
    COSTS = {
        'SAME': 0, # same jig plays multiple notes in a row
        'DIFF': 1, # different jig already in set plays the next note
        'ADD':  10, # add a new jig to the set
        'OCT':  4  # extra cost incurred if the note is in the wrong octave
    }
    
    def sort(self, poss):
        return poss.cost
    
    noteNames = ['c', 'db', 'd', 'eb', 'e', 'f', 'gb', 'g', 'ab', 'a', 'bb', 'b']
    # adapted from https://github.com/danigb/tonal/blob/master/packages/note/index.js#L328
    def midiToNote(self, midiNote):
        return (self.noteNames[midiNote % 12], math.floor(midiNote / 12) - 1)

    BEAM_WIDTH = 80 # number of best possibilities to keep each round
    singamajig_data = json.load(open('singamajig_data.json'))
    # database of all the notes in all the songs, categorized by note name
    songs_by_note = {'spoken': []}
    for noteName in noteNames:
        songs_by_note[noteName] = []
    for songIndex in xrange(0, len(singamajig_data)):
        notes = singamajig_data[songIndex]['notes']
        for noteIndex in xrange(0, len(notes)):
            noteObj = notes[noteIndex]
            note = noteObj['pitch']
            songs_by_note[note].append(_NoteInstance(songIndex, noteIndex, noteObj))
    
    allSingamajigs = []
    def initJigs(self):
        # instantiate one Singamajig object per Singamajig model
        # (since they don't track their own state it's fine lol)
        for songIndex in xrange(0, len(self.singamajig_data)):
            self.allSingamajigs.append(_Singamajig(songIndex))

class _Singamajig:
    globals = _Globals()
    def __init__(self, songIndex):
        self.songIndex = songIndex
        self.songData = self.globals.singamajig_data[songIndex]
        self.notes = self.songData['notes']
    
    def getNextIndex(self, prevIndex):
        return (prevIndex + 1) % len(self.notes)
    
    def getNote(self, noteNum):
        noteNum = noteNum % len(self.notes)
        return self.notes[noteNum]
_Globals().initJigs();

class _ScoreState:
    globals = _Globals()
    def __init__(self, singamajigIndex, songIndex, noteIndex):
        self.singamajigIndex = singamajigIndex
        self.songIndex = songIndex
        self.noteIndex = noteIndex
        self.song = self.globals.singamajig_data[self.songIndex]
        self.noteObj = self.song['notes'][self.noteIndex]
    def __str__(self):
        return "\"%s\" [id %d] - %d:%s%d \"%s\"" % (
            self.song['title'],
            self.singamajigIndex,
            self.noteIndex,
            self.noteObj['pitch'],
            self.noteObj['octave'],
            self.noteObj['syllable']
        )

class _State:
    def __init__(self, singamajig, singamajigIndex, noteIndex):
        self.singamajig = singamajig
        self.singamajigIndex = singamajigIndex
        self.noteIndex = noteIndex
        
    def toScoreState(self):
        return _ScoreState(
            self.singamajigIndex,
            self.singamajig.songIndex,
            self.noteIndex
        )

class _Possibility:
    globals = _Globals()
    # store a reference to the previous possibility instead of duplicating everything?
    
    cost = 0 # cost of previous possibility plus next possibility
    currentJig = None # the Singamajig that plays the note
    previousPoss = None # so we can reconstruct the score when done
    
    def __init__(self):
        self.states = [] # a list of _State objects
    
    def add(self, jig, noteIndex, octave):
        self.currentJig = len(self.states)
        self.states.append(_State(jig, len(self.states), noteIndex))
        self.cost += self.globals.COSTS['ADD']
        if jig.getNote(noteIndex)['octave'] != octave:
            self.cost += self.globals.COSTS['OCT']
    
    def advance(self, jigIndex, octave):
        state = self.states[jigIndex]
        state.noteIndex = state.singamajig.getNextIndex(state.noteIndex)
        if jigIndex == self.currentJig:
            self.cost += self.globals.COSTS['SAME']
        else:
            self.cost += self.globals.COSTS['DIFF']
            self.currentJig = jigIndex
        if state.singamajig.getNote(state.noteIndex)['octave'] != octave:
            self.cost += self.globals.COSTS['OCT']
    
    def getAdvanceableJigIndexes(self, note):
        matchingJigs = []
        for state in self.states:
            nextNote = state.singamajig.getNote(state.noteIndex + 1)['pitch']
            if nextNote == note:
                matchingJigs.append(state.singamajigIndex)
        return matchingJigs
    
    # I don't understand deepcopy very well so we'll do this manually
    def copy(self):
        newPoss = _Possibility()
        for state in self.states:
            newPoss.states.append(_State(
                state.singamajig,
                state.singamajigIndex,
                state.noteIndex
            ))
        newPoss.cost = self.cost
        newPoss.currentJig = self.currentJig
        newPoss.previousPoss = self
        return newPoss
    
    def getScoreState(self):
        if not self.currentJig == None:
            return self.states[self.currentJig].toScoreState()
        else:
            return None

def get_possibilities(prevPossibilities, midiNote, isOn):
    globals = _Globals()
    possibilities = [] # possibilities for the current round
    maxCost = -1;
    costsThisRound = 0;
    (melody_pitch, melody_octave) = globals.midiToNote(midiNote)
    
    for prevPoss in prevPossibilities:
        nexts = prevPoss.getAdvanceableJigIndexes(melody_pitch)
        for nextJig in nexts:
            newPoss = prevPoss.copy()
            newPoss.advance(nextJig, melody_octave)
            if costsThisRound < globals.BEAM_WIDTH:
                possibilities.append(newPoss)
                if newPoss.cost > maxCost:
                    maxCost = newPoss.cost
                    costsThisRound += 1
            elif newPoss.cost <= maxCost:
                possibilities.append(newPoss)
        for noteInstance in globals.songs_by_note[melody_pitch]:
            newPoss = prevPoss.copy()
            jig = globals.allSingamajigs[noteInstance.songIndex]
            newPoss.add(jig, noteInstance.noteIndex, melody_octave)
            if costsThisRound < globals.BEAM_WIDTH:
                possibilities.append(newPoss)
                if newPoss.cost > maxCost:
                    maxCost = newPoss.cost
                    costsThisRound += 1
            elif newPoss.cost <= maxCost:
                possibilities.append(newPoss)
        
        # ok now it's beam time
        # select the cheapest possibilities before moving on to the next round
        random.shuffle(possibilities)
        possibilities.sort(key=globals.sort)
        return possibilities[:globals.BEAM_WIDTH]

def midi_to_score(filename):
    pattern = midi.read_midifile(filename)
    track = pattern[0] # @todo: support multiple tracks
    possibilities = [_Possibility()]
    for event in track:
        midiNote = event.data[0] if len(event.data) else None
        if isinstance(event, midi.NoteOnEvent):
            if event.data[1] > 0:
                possibilities = get_possibilities(possibilities, midiNote, True)
            else:
                None
                #possibilities = get_possibilities(possibilities, midiNote, False)
        elif isinstance(event, midi.NoteOffEvent):
            None
            #possibilities = get_possibilities(possibilities, midiNote, False)
    
    if(len(possibilities) == 0):
        return None
    
    currentPossibility = possibilities[0]
    # reconstruct the possibility into a consumable format
    score = []
    while not currentPossibility == None:
        scoreState = currentPossibility.getScoreState()
        if not scoreState == None:
            score.insert(0, str(scoreState))
        currentPossibility = currentPossibility.previousPoss
    return (score, possibilities[0].cost)
