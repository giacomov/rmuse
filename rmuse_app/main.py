import os

import pandas as pd
import numpy as np


# This is necessary otherwise flask will fail importing submodules
import rmuse

from rmuse.originality.originality import OriginalityScore
from rmuse.chords_ai import ChordsAI
from rmuse.chords_ai.custom_metric import sparse_top_k_categorical_accuracy_3
from rmuse.chords_ai.player import ChordSequencePlayer

np.random.seed(10)

from flask import Flask, request, jsonify
from flask import render_template
from flask import url_for
import hashlib

import tensorflow as tf
import json
import requests


# Read configuration
with open("configuration.json") as f:

    configuration = json.load(f)

# Google analytics set up
# Environment variables are defined in app.yaml.
GA_TRACKING_ID = configuration['GA_TRACKING_ID']


# https://developers.google.com/analytics/devguides/collection/protocol/v1/reference
def track_event(page):
    data = {
        'v': '1',  # API Version.
        'tid': GA_TRACKING_ID,  # Tracking ID / Property ID.
        # Anonymous Client Identifier. Ideally, this should be a UUID that
        # is associated with particular user, device, or browser instance.
        'cid': _get_unique_id(),
        't': 'pageview',  # Event hit type.
        'dp': page,  # Page visited
    }

    print("Sending to GOOGLE:")
    print(data)

    try:

        response = requests.post(
            'http://www.google-analytics.com/collect', data=data)

        # If the request fails, this will raise a RequestException. Depending
        # on your application's needs, this may be a non-error and can be caught
        # by the caller.
        # response.raise_for_status()

    except:

        pass


# Set up Flask app
app = Flask(__name__)


# Init Tensorflow stuff (we avoid reloading every time, because
# we need real-time performance)

seed_sequences = {'Em': "Em Am D7 G Em C Am Em",
                  'C': "C G Am F C Dm G C",
                  "Am": "Am Dm E Am C G Em Am",
                  "A": "A Bm E A F#m Bm E A",
                  "D": "D Bm E A D7 G A D"}

seed_sequences_rock = {'C': "C Em Am F A# C G C",
                       'Am': "Am Dm Am Dm Am E Am"}

hit_maker = ChordsAI(configuration['hit_maker_model'],
                     configuration['hit_maker_vocabulary'])

hit_maker.model_summary()

connoisseur = ChordsAI(configuration['connoisseur_model'], configuration['connoisseur_vocabulary'],
                       sort_vocabulary=False)

connoisseur.model_summary()

# We need this to get around the multitask nature of flask
graph = tf.get_default_graph()


# This function returns a (more or less) unique id to identify a user
# We need this so multiple users can use the rmuse at the same time
def _get_unique_id():

    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:

        # Not in nginx

        ip_address = request.environ['REMOTE_ADDR']

    else:

        # In nginx

        ip_address = request.environ['HTTP_X_FORWARDED_FOR']

    print(ip_address)

    # This is something like '
    # Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36'
    user_agent = request.headers.get('User-Agent')

    hash_material = "%s%s" % (user_agent, ip_address)

    print("Got a visit from: %s" % ip_address)
    print("User agent: %s" % user_agent)

    return hashlib.md5(hash_material.encode('utf-8')).hexdigest()


def _get_prediction(input_sequence, ai_, seed_):

    if input_sequence is None:

        # First run

        input_sequence = ''
        choices = 'X X X X X C Am X X X X'
        probabilities = " ".join(["0"] * 11)

        audio_filename = None

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
        audio_filename = 'wave/%s.wav' % _get_unique_id()
        pl = ChordSequencePlayer()
        pl.to_wav(input_sequence, os.path.join("static", audio_filename))

        with graph.as_default():

            r = ai_.get_next_possibilities(gen_seq.split())

        # Redorder them with the most probable value in the middle,
        # and the others up and down. So if the chords and their probabilities are
        # (G, 0.5), (F, 0.4), (Am, 0.3), (D, 0.1), (E, 0.05), the output order will be
        # D F G Am E

        probs = pd.Series({k: v for k, v in zip(*r)})

        first_ten = probs.sort_values(ascending=False)[:7]

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

    return input_sequence, choices, probabilities, audio_filename


@app.route('/hitmaker/')
@app.route('/hitmaker/<input_sequence>')
def hitmaker(input_sequence=None):

    track_event('/hitmaker')

    import tensorflow as tf

    global graph

    input_sequence, choices, probabilities, audio_file = _get_prediction(input_sequence, hit_maker, seed_sequences)

    if len(input_sequence.split(" ")) <= 3:

        # Not enough chords for score
        score = '(need at least 3 chords)'

    else:

        os = OriginalityScore(configuration['connoisseur_binomials'])
        score = os.originality_ranking(input_sequence.strip())

    if audio_file is not None:

        audio = url_for('static', filename=audio_file)

    else:

        audio = ""

    return render_template("view.html", input_sequence=input_sequence,
                           choices=choices,
                           probabilities=probabilities,
                           score=score,
                           icon_file=url_for('static', filename='hit_maker.png'),
                           robot_name="The Hit Maker",
                           audio_file=audio)


@app.route('/connoisseur/')
@app.route('/connoisseur/<input_sequence>')
def theconnoisseur(input_sequence=None):

    track_event('/connoisseur')

    import tensorflow as tf

    global graph

    input_sequence, choices, probabilities, audio_file = _get_prediction(input_sequence, connoisseur, seed_sequences_rock)

    if len(input_sequence.split(" ")) <= 3:

        # Not enough chords for score
        score = '(need at least 3 chords)'

    else:

        os = OriginalityScore(configuration['connoisseur_binomials'])
        score = os.originality_ranking(input_sequence.strip())

    if audio_file is not None:

        audio = url_for('static', filename=audio_file)

    else:

        audio = ""

    return render_template("view.html", input_sequence=input_sequence,
                           choices=choices,
                           probabilities=probabilities,
                           score=score,
                           icon_file=url_for('static', filename='connoisseur.png'),
                           robot_name="The Connoisseur",
                           audio_file=audio)

@app.route('/')
def main():

    track_event('/')

    return render_template("initial_selection.html")