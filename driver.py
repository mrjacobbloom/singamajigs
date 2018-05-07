#!/usr/bin/env python3
import singamajigs
#from pprint import pprint

sscore = singamajigs.midi_to_sscore("wnw.mid", try_alt_keys = False)
for state in sscore['states']:
    print(str(state))
ascore = singamajigs.sscore_to_abjad_score(sscore)
print(format(ascore))
singamajigs.render_score(ascore, sscore['beats'], sscore['jigs'])
