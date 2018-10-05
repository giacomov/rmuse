// Takes all chords and generate the list of notes they are composed of
// Usage: nodejs generate_chords_components.js

var s11 = require('sharp11');

var notes = {};

var fs = require('fs');
var vocabulary = JSON.parse(fs.readFileSync('data/all_fundamentals.json', 'utf8'));

for (let ch of vocabulary) {

	var these_notes = s11.chord.create(ch).chord;

	var this_arr = [];

	for (let note of these_notes) {

		this_arr.push(note.name);

	}

	notes[ch] = this_arr;

}

fs.writeFile ("data/chords_components.json", JSON.stringify(notes), function(err) {
    if (err) throw err;
    console.log('complete');
    }
);
