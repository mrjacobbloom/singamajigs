# singamajigs
This algorithm produces a score to perform a given melody on a number of
Sing-a-ma-jigs. It optimizes for most notes in a row, then smallest set of dolls
needed. It doesn't necessarily find the best possible solution because the
number of possibilities increases exponentially with every note. Instead, I used
a [beam search](https://en.wikipedia.org/wiki/Beam_search) which saves some
fixed number of the most promising solutions, which makes it partially resilient
to local maxima but won't take up a ludicrous amount of memory either.

```shell
python3 driver.py
```

## What does this all even mean?
The Sing-a-ma-jigs were a line of singing toys. Each model had one public-domain
song that it sang one note of each time it was squeezed. A person could
theoretically use many Sing-a-ma-jigs to play a different melody of their
choosing. Imagine a handbell choir where every time you play a note that bell
will play a predictable but different note the next time. This algorithm
(assuming I can get it to work) outputs a score to play a song under those
constraints, while optimizing to maximize the number of consecutive notes played
by one Sing-a-ma-jig (bell) and then minimize the number of Sing-a-ma-jigs
needed.

It also tries transposing the song up and down 12 keys to see if it can find a
better match. It uses a little randomization to spice things up, so I make no
promise of determinism.

## Why?
Because they're obnoxious. Also because I saw videos like
[this one](https://www.youtube.com/watch?v=P1a554_J9VU) and thought to myself
"this person had to do so much planning, and keeping track of the notes each
doll makes, and I should make it easy for future generations to do this." And
because it's an interesting coding exercise and I need to get more comfortable
in Python.

## Installation
Pardon me while I figure out how dependency management works in the Python
universe. Here are the things you need to figure out how to install:

- [python3-midi](https://github.com/louisabraham/python3-midi)
  - the setup file for this required a package called "six" that I had to install
    separately 🤷‍
- [pytube](https://github.com/nficano/pytube)
- [abjad](http://projectabjad.org/)
- [Imagemajick](http://www.imagemagick.org/script/index.php)

## Usage
```python
import singamajigs

# download all the videos (if you want them in the visualization)
# you only need to run this once!
singamajigs.download_all()

# generate a score object from a MIDI file
score = singamajigs.midi_to_score("path/to/file/myIncredibleSong.mid")
```

## Credits
A big thanks to the YouTube channel
[SuperSingamajigs](https://www.youtube.com/user/SuperSingamajigs) for posting
clear videos of each Sing-a-ma-jig's song. This project downloads their videos
for the visualizer, but the video files themselves are not distributed with this
repo.

The Sing-a-ma-jigs&trade; are the property of Fisher-Price and I've done my best
not to infringe on their rights in this project. I believe all of the songs
they perform are in the Public Domain (I skipped the ones that aren't) but if I've
posted something I shouldn't have, please let me know so I can remove it.
