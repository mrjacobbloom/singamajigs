import json
import random
import copy

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
        'ADD':  6, # add a new jig to the set
        'OCT':  2  # extra cost incurred if the note is in the wrong octave
    }
    
    SHARPS = {
        'c#': 'db',
        'd#': 'eb',
        'e#': 'f', # trust no one
        'f#': 'gb',
        'g#': 'ab',
        'a#': 'bb',
        'b#': 'c'
    }
    
    def sort(self, poss):
        return poss.cost

    BEAM_WIDTH = 10 # number of best possibilities to keep each round
    singamajig_data = json.load(open('singamajig_data.json'))
    # database of all the notes in all the songs, categorized by note name
    songs_by_note = {}
    for songIndex in xrange(0, len(singamajig_data)):
        notes = singamajig_data[songIndex]['notes']
        for noteIndex in xrange(0, len(notes)):
            noteObj = notes[noteIndex]
            note = noteObj['pitch']
            if not note in songs_by_note:
                songs_by_note[note] = []
            songs_by_note[note].append(_NoteInstance(songIndex, noteIndex, noteObj))

class _Singamajig:
    _globals = _Globals()
    def __init__(self, songIndex):
        self.songIndex = songIndex
        self.songData = self._globals.singamajig_data[songIndex]
        self.notes = self.songData['notes']
    
    def getNextIndex(self, prevIndex):
        return (prevIndex + 1) % len(self.notes)
    
    def getNote(self, noteNum):
        noteNum = noteNum % len(self.notes)
        return self.notes[noteNum]
    
    def __deepcopy__(self, memo): # override this so they never get duplicated
        memo[id(self)] = self
        return self

class _ScoreState:
    _globals = _Globals()
    def __init__(self, singamajigIndex, songIndex, noteIndex):
        self.singamajigIndex = singamajigIndex
        self.songIndex = songIndex
        self.noteIndex = noteIndex
        self.song = self._globals.singamajig_data[self.songIndex]
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
    _globals = _Globals()
    # store a reference to the previous possibility instead of duplicating everything?
    
    states = [] # a list of state dicts: (singamajig, noteIndex)
    cost = 0 # cost of previous possibility plus next possibility
    currentJig = None # the Singamajig that plays the note
    previousPoss = None # so we can reconstruct the score when done
    
    def add(self, jig, noteIndex):
        self.currentJig = len(self.states)
        self.states.append(_State(jig, len(self.states), noteIndex))
        print(jig.getNote(noteIndex)['pitch'])
        self.cost += self._globals.COSTS['ADD']
    
    def advance(self, jigIndex):
        state = self.states[jigIndex]
        state.noteIndex = state.singamajig.getNextIndex(state.noteIndex)
        if jigIndex == self.currentJig:
            self.cost += self._globals.COSTS['SAME']
        else:
            self.cost += self._globals.COSTS['DIFF']
            self.currentJig = jigIndex
    
    def getAdvanceableJigIndexes(self, note):
        matchingJigs = []
        for state in self.states:
            nextNote = state.singamajig.getNote(state.noteIndex + 1)['pitch']
            if nextNote == note:
                matchingJigs.append(state.singamajigIndex)
        return matchingJigs
    
    def getScoreState(self):
        if not self.currentJig == None:
            return self.states[self.currentJig].toScoreState()
        else:
            return None

def singamajigs(melody):
    _globals = _Globals()
    prevPossibilities = [_Possibility()]
    
    # instantiate one SIngamajig object per song
    # (since they don't track their own state it's fine lol)
    allSingamajigs = []
    for songIndex in xrange(0, len(_globals.singamajig_data)):
        allSingamajigs.append(_Singamajig(songIndex))
    
    for melody_note in melody:
        possibilities = [] # possibilities for the current round
        melody_note = melody_note.lower()
        melody_pitch = melody_note[:-1]
        melody_octave = melody_note[-1]
        if '#' in melody_pitch and melody_pitch in _globals.SHARPS:
            melody_pitch = _globals.SHARPS[melody_pitch]
        
        # catch it now if there are no singamajigs that sing the note
        if not melody_pitch in _globals.songs_by_note:
            return None
        for prevPoss in prevPossibilities:
            nexts = prevPoss.getAdvanceableJigIndexes(melody_pitch)
            for nextJig in nexts:
                newPoss = copy.deepcopy(prevPoss)
                newPoss.previousPoss = prevPoss
                newPoss.advance(nextJig)
                possibilities.append(newPoss)
            for noteInstance in _globals.songs_by_note[melody_pitch]:
                newPoss = copy.deepcopy(prevPoss)
                newPoss.previousPoss = prevPoss
                jig = allSingamajigs[noteInstance.songIndex]
                newPoss.add(jig, noteInstance.noteIndex)
                possibilities.append(newPoss)
        
        # ok now it's beam time
        # select the cheapest possibilities before moving on to the next round
        possibilities.sort(key=_globals.sort)
        prevPossibilities = possibilities[:_globals.BEAM_WIDTH]
        for poss in prevPossibilities: print(poss.cost);
    if(len(prevPossibilities) == 0):
        return None
    
    currentPossibility = prevPossibilities[0]
    # reconstruct the possibility into a consumable format
    score = []
    while not currentPossibility == None:
        scoreState = currentPossibility.getScoreState()
        if not scoreState == None:
            score.insert(0, str(scoreState))
        currentPossibility = currentPossibility.previousPoss
    return score
