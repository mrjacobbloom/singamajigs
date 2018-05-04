#!/usr/bin/env python3
import singamajigs
from pprint import pprint

score = singamajigs.midi_to_score("wnw.mid")
pprint(score)
