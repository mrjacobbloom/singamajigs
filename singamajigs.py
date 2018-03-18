import json

singamajig_data = json.load(open('singamajig_data.json'))

def singamajigs(melody):
    possibilities = []
    for melody_note in melody:
        if "#" in melody_note:
            "bleb"
            # @TODO figure out how to flat the sharp things
        # @TODO ok so how the heck is this actually gonna work
        possibilities.append(melody_note + " is a bad note")
    return possibilities;
