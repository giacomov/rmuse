import pandas as pd
import numpy as np


# This is necessary otherwise flask will fail importing submodules
import rmuse

from rmuse.originality.originality import OriginalityScore
from rmuse.chords_ai import ChordsAI
from rmuse.chords_ai.player import ChordSequencePlayer

np.random.seed(10)

from flask import Flask
from flask import render_template
from flask import url_for

import tensorflow as tf
import json

# Read configuration
with open("configuration.json") as f:

    configuration = json.load(f)

app = Flask(__name__)

seed_sequences = {'Em': "Em Am D7 G Em C Am Em",
                  'C': "C G Am F C Dm G C",
                  "Am": "Am Dm E Am C G Em Am",
                  "A": "A Bm E A F#m Bm E A",
                  "D": "D Bm E A D7 G A D"}

seed_sequences_rock = {'C': "C Em Am F A# C G C"}

ai = ChordsAI(configuration['hit_maker_model'],
              configuration['hit_maker_vocabulary'])

ai.model_summary()

ai_rock = ChordsAI(configuration['connoisseur_model'], configuration['connoisseur_vocabulary'],
                   sort_vocabulary=False)

ai_rock.model_summary()

graph = tf.get_default_graph()


def _get_prediction(input_sequence, ai_, seed_):

    if input_sequence is None:

        # First run

        input_sequence = ''
        choices = 'X X X X X C Am X X X X'
        probabilities = " ".join(["0"] * 11)

    else:

        # Any other run
        input_sequence = input_sequence.strip()
        s = input_sequence.split()

        # If we only have one chord, init with a seed
        if len(s) == 1:

            # First run
            gen_seq = seed_[s[0]]

        else:

            # Pad
            # NOTE: this will be empty if len(s) > of the length of the list
            gen_seq = seed_[s[0]].split()[len(s):]
            gen_seq.extend(s)
            gen_seq = " ".join(gen_seq)

        # Generate audio for this sequence
        try:

            pl = ChordSequencePlayer()
            pl.to_wav(input_sequence, 'static/test.wav')

        except:

            pass

        with graph.as_default():

            r = ai_.get_next_possibilities(gen_seq.split())

        # Redorder them with the most probable value in the middle,
        # and the others up and down. So if the chords and their probabilities are
        # (G, 0.5), (F, 0.4), (Am, 0.3), (D, 0.1), (E, 0.05), the output order will be
        # D F G Am E

        probs = pd.Series({k: v for k, v in zip(*r)})

        first_ten = probs.sort_values(ascending=False)[:11]

        first_half = pd.Series()
        second_half = pd.Series()

        for v in first_ten.iloc[::2].iteritems():
            first_half[v[0]] = v[1]

        for v in first_ten.iloc[1::2].iteritems():
            second_half[v[0]] = v[1]

        ss = pd.concat([pd.Series(first_half).iloc[::-1], pd.Series(second_half)])

        print("=================================")
        print(input_sequence)
        print(gen_seq)
        print(ss)
        print("=================================")

        # Re add the empty space at the beginning, which is where the play button will go
        input_sequence = " " + input_sequence

        choices = " ".join(ss.index.values)
        probabilities = " ".join(list(map(lambda x:"%.3f" % x, ss.values)))

    return input_sequence, choices, probabilities


@app.route('/webgl/')
@app.route('/webgl/<input_sequence>')
def webgl(input_sequence=None):

    import tensorflow as tf

    global graph

    input_sequence, choices, probabilities = _get_prediction(input_sequence, ai, seed_sequences)

    return render_template("view.html", input_sequence=input_sequence,
                           choices=choices,
                           probabilities=probabilities,
                           score="10")


@app.route('/rock/')
@app.route('/rock/<input_sequence>')
def rock(input_sequence=None):

    import tensorflow as tf

    global graph

    input_sequence, choices, probabilities = _get_prediction(input_sequence, ai_rock, seed_sequences_rock)

    if len(input_sequence.split(" ")) <= 3:

        # Not enough chords for score
        score = '(need at least 3 chords)'

    else:

        os = OriginalityScore(configuration['connoisseur_binomials'])
        score = os.originality_ranking(input_sequence.strip())

    return render_template("view.html", input_sequence=input_sequence,
                           choices=choices,
                           probabilities=probabilities,
                           score=score)

@app.route('/')
def main():

    return render_template("initial_selection.html")