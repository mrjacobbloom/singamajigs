import os
import json
import random
import midi
import math
import random
import pytube
import abjad

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
    for songIndex in range(0, len(singamajig_data)):
        notes = singamajig_data[songIndex]['notes']
        for noteIndex in range(0, len(notes)):
            noteObj = notes[noteIndex]
            note = noteObj['pitch']
            songs_by_note[note].append(_NoteInstance(songIndex, noteIndex, noteObj))
    
    allSingamajigs = []
    def initJigs(self):
        # instantiate one Singamajig object per Singamajig model
        # (since they don't track their own state it's fine lol)
        for songIndex in range(0, len(self.singamajig_data)):
            self.allSingamajigs.append(_Singamajig(songIndex))
    
    def lilypondPitch(self, noteObj):
        pc = noteObj['pitch']
        if len(pc) == 2:
            pc = pc[0] + 'f'
        
        if noteObj['octave'] == 3:
            oct =  ''
        elif noteObj['octave'] > 3:
            oct =  '\''*(noteObj['octave'] - 3)
        else:
            oct =  ','*(3 - noteObj['octave'])
        
        return pc + oct
    
    def iToStaff(self, i):
        return 'Staff%d' % (i)

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
    def __init__(self, singamajigIndex, songIndex, noteIndex, beat):
        self.singamajigIndex = singamajigIndex
        self.songIndex = songIndex
        self.noteIndex = noteIndex
        self.song = self.globals.singamajig_data[self.songIndex]
        self.noteObj = self.song['notes'][self.noteIndex]
        self.beat = beat
    def __str__(self):
        return "\"%s\" [id %d | beat %0.2f] - %d:%s%d \"%s\"" % (
            self.song['title'],
            self.singamajigIndex,
            self.beat,
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
        
    def toScoreState(self, beat):
        return _ScoreState(
            self.singamajigIndex,
            self.singamajig.songIndex,
            self.noteIndex,
            beat
        )

class _Possibility:
    globals = _Globals()
    # store a reference to the previous possibility instead of duplicating everything?
    
    cost = 0 # cost of previous possibility plus next possibility
    currentJig = None # the Singamajig that plays the note
    beat = 0
    previousPoss = None # so we can reconstruct the score when done
    
    def __init__(self):
        self.states = [] # a list of _State objects
    
    def add(self, jig, noteIndex, octave, beat):
        self.currentJig = len(self.states)
        self.states.append(_State(jig, len(self.states), noteIndex))
        self.cost += self.globals.COSTS['ADD']
        self.beat = beat
        if jig.getNote(noteIndex)['octave'] != octave:
            self.cost += self.globals.COSTS['OCT']
    
    def advance(self, jigIndex, octave, beat):
        state = self.states[jigIndex]
        state.noteIndex = state.singamajig.getNextIndex(state.noteIndex)
        self.beat = beat
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
            return self.states[self.currentJig].toScoreState(self.beat)
        else:
            return None

def get_possibilities(prevPossibilities, midiNote, beat, isOn):
    globals = _Globals()
    possibilities = [] # possibilities for the current round
    maxCost = -1;
    costsThisRound = 0;
    (melody_pitch, melody_octave) = globals.midiToNote(midiNote)
    
    for prevPoss in prevPossibilities:
        nexts = prevPoss.getAdvanceableJigIndexes(melody_pitch)
        for nextJig in nexts:
            newPoss = prevPoss.copy()
            newPoss.advance(nextJig, melody_octave, beat)
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
            newPoss.add(jig, noteInstance.noteIndex, melody_octave, beat)
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

def download_all():
    globals = _Globals()
    if os.path.exists('./video'):
        print('Aborting video download, video directory already exists.')
        return
    os.makedirs('./video')
    for songNumber in range(0,len(globals.singamajig_data)):
        song = globals.singamajig_data[songNumber]
        print('Downloading "%s"...' % (song['title']))
        yt = pytube.YouTube(song['url'])
        yt.streams \
        .filter(progressive=True, file_extension='mp4') \
        .order_by('resolution') \
        .asc() \
        .first() \
        .download(output_path = './video', filename = str(songNumber))

def midi_to_sscore(filename, try_alt_keys = True):
    pattern = midi.read_midifile(filename)
    track = pattern[0] # @todo: support multiple tracks
    cheapestKeyPossibility = None
    # try 24 keys (well, every key in the surrounding 2 octaves)
    keyOffsets = range(-12, 12) if try_alt_keys else [0]
    for keyOffset in keyOffsets:
        tickTotal = 0;
        possibilities = [_Possibility()]
        for event in track:
            tickTotal += event.tick
            if isinstance(event, midi.NoteOnEvent):
                beat = tickTotal / pattern.resolution
                if event.get_velocity() > 0:
                    possibilities = get_possibilities(
                        possibilities,
                        event.get_pitch(),
                        beat,
                        True)
                else:
                    None
                    #possibilities = get_possibilities(
                    #    possibilities,
                    #    midiNote,
                    #    event.tick,
                    #    False)
            elif isinstance(event, midi.NoteOffEvent):
                None
                #possibilities = get_possibilities(
                #    possibilities,
                #    midiNote,
                #    event.tick,
                #    False)
    
        if len(possibilities) > 0 and (cheapestKeyPossibility == None or possibilities[0].cost < cheapestKeyPossibility.cost):
            cheapestKeyPossibility = possibilities[0]
    
    # reconstruct the possibility into a consumable format
    currentPossibility = cheapestKeyPossibility
    sscore = {
        'states': [],
        'jigs': len(cheapestKeyPossibility.states),
        'beats': int(math.ceil(cheapestKeyPossibility.beat))
    }
    while not currentPossibility == None:
        scoreState = currentPossibility.getScoreState()
        if not scoreState == None:
            sscore['states'].insert(0, scoreState)
        currentPossibility = currentPossibility.previousPoss
    return sscore

# Abjad can't handle lyrics so here's a hack in the interim
# https://github.com/Abjad/abjad/blob/5c7f5f7abd8013f99b60c9ceb3a91c771abbca7c/abjad/tools/scoretools/Note.py
class _Lyrics(abjad.Leaf):
    def __init__(self, ctx, lyrics = ''):
        self.written_duration = 1
        self.written_pitch = 'c'
        abjad.Leaf.__init__(self, self.written_duration)
        self.ctx = ctx
        self.lyrics = lyrics
    
    def add_lyric(self, lyric):
        self.lyrics += ' ' + lyric
    def _get_contents_summary(self):
        return '(contents summary)'
    def __format__(self, arg):
        return '\\new Lyrics \\lyricsto "%s" { %s }' % (self.ctx, self.lyrics)
    def _get_compact_representation(self):
        return '(compact representation)'
    def _get_compact_representation_with_tie(self):
        return '(compact representation with tie)'

def sscore_to_abjad_score(sscore):
    globals = _Globals()
    score = abjad.Score(context_name = 'Score')
    
    sig = abjad.TimeSignature((1, 4))
    
    # don't just use the score object since we're alternating lyrics blocks
    # ooh it can be tuples (Voice, _Lyrics)
    voices = []
    
    # create a staff of empty measures for each jig
    for i in range(0,sscore['jigs']):
        voice = abjad.Voice(name = globals.iToStaff(i))
        
        for beat in range(0,sscore['beats']):
            measure = abjad.Measure(sig, "r4")
            voice.extend(measure)
        
        # only now that the staves have content can we set their clef
        leaf = abjad.inspect(voice).get_leaf()
        abjad.attach(abjad.Clef('alto'), leaf)
        
        score.append(voice)
        
        lyrics = _Lyrics(globals.iToStaff(i))
        score.append(lyrics)
        voices.append((voice, lyrics))
    nextState = 0
    for beat in range(0,sscore['beats']):
        while sscore['states'][nextState].beat <= beat + 1:
            # thanks python for making me write this twice
            state = sscore['states'][nextState]
            snote = state.noteObj
            pitch = globals.lilypondPitch(snote)
            
            # generate correct amount of rest before the note begins
            # assume powers of 2 (no tuplets, sorry boiz)
            restBeats = state.beat % 1
            if restBeats != 0:
                rest16ths = int(restBeats / 0.25)
                rest = abjad.Rest(abjad.Duration(rest16ths, 16))
                
                noteBeats = 1 - restBeats
                note16ths = int(noteBeats / 0.25)
                anote = abjad.Note()
                anote.written_pitch = pitch
                anote.written_duration = abjad.Duration(note16ths, 16)
                measure = abjad.Measure(sig, [rest, anote])
            else:
                anote = abjad.Note()
                anote.written_pitch = pitch
                anote.written_duration = abjad.Duration(1, 4)
                measure = abjad.Measure(sig, [anote])
            # what if the measure already contained a note this beat?
            # eh that's a risk I'm willing to take
            
            voiceTuple = voices[state.singamajigIndex]
            voiceTuple[0][beat] = measure
            voiceTuple[1].add_lyric(snote['syllable'])
            
            nextState += 1
            if nextState >= len(sscore['states']):
                break
    
    return score

def render_score(score, beats, jigs):
    # adapted from https://github.com/Abjad/abjad/blob/5c7f5f7abd8013f99b60c9ceb3a91c771abbca7c/abjad/demos/ligeti/make_desordre_lilypond_file.py
    file = abjad.LilyPondFile.new(score, global_staff_size = 18)
    
    context_block = abjad.ContextBlock(source_context_name = 'Score')
    file.layout_block.items.append(context_block)
    # for future reference: http://lilypond.org/doc/v2.18/Documentation/learning/engravers-explained.en.html
    context_block.remove_commands.append('Bar_number_engraver')
    context_block.remove_commands.append('Default_bar_line_engraver')
    abjad.override(context_block).clef.transparent = True
    abjad.override(context_block).spacing_spanner.strict_grace_spacing = True
    abjad.override(context_block).spacing_spanner.strict_note_spacing = True
    abjad.override(context_block).spacing_spanner.uniform_stretching = True
    abjad.override(context_block).text_script.staff_padding = 0
    abjad.override(context_block).time_signature.transparent = True
    abjad.override(context_block).rest.transparent = True
    abjad.override(context_block).dots.transparent = True
    
    file.header_block.tagline = ' '
    
    file.paper_block.paper_width = beats * 15
    file.paper_block.paper_height = jigs * 20
    file.paper_block.bottom_margin = 0
    file.paper_block.left_margin = 0
    vector = abjad.SpacingVector(0, 0, 15, 0)
    #file.paper_block.system_system_spacing = vector
    abjad.show(file)
    #print(abjad.persist(staff).as_png('./renders/score.png', remove_ly=True))
