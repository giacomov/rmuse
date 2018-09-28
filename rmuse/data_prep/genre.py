import re
import musicbrainzngs as mb
from rmuse.data_prep import name_regularizer
import time
from math import ceil
import yaml
import os


def _iter_over_dict(d):

    nodes = []

    assert isinstance(d, dict)

    assert len(d) == 1

    first_key = list(d.keys())[0]

    nodes.append(first_key)

    for dd in d[first_key]:

        if isinstance(dd, str):

            nodes.append(dd)

        else:

            nodes.extend(_iter_over_dict(dd))

    return nodes


def _flatten_tree(tree_list, parent=None):

    genres = {}

    for d in tree_list:

        assert isinstance(d, dict)

        assert len(d) == 1

        first_key = list(d.keys())[0]

        for node in _iter_over_dict(d):

            genres[node] = first_key

        genres[first_key] = first_key

    return genres


class GenreSolver(object):

    def __init__(self):

        # Read in yaml file
        path = os.path.join(os.path.dirname(__file__), 'genre-tree.yml')

        with open(path, "r") as genre_file:

            genres_tree = yaml.load(genre_file)

        # Now flatten the tree
        self._mapping = _flatten_tree(genres_tree)

    def __getitem__(self, item):

        return self._mapping[item]


class ThrottledQuery(object):

    def __init__(self, time_interval=1):

        self._last_query_time = None
        self._time_interval = time_interval

    def search_artists(self, *args, **kwargs):

        current_time = time.time()

        if self._last_query_time is None:

            # No need to wait, this is the first query
            pass

        else:

            # We need to wait to avoid hammering the server
            wait_time = ceil(current_time - self._last_query_time)

            time.sleep(wait_time)

        result = mb.search_artists(*args, **kwargs)

        self._last_query_time = time.time()

        return result


class MusicBrainz(object):

    def __init__(self, debug=False, timeout=1):
        """
        A class to interrogate MusicBrainz for the genre of artists.

        :param debug: print debug information (True or False)
        """

        # This is required by the API
        mb.set_useragent("RMUSE", "0.1", "https://github.com/giacomov")

        # This holds a class that throttle the requests to avoid spamming the server (and getting banned)
        self._throttled_query = ThrottledQuery(timeout)

        self._debug = debug

        self._genre_solver = GenreSolver()

    def find_genres(self, artists):
        """
        A generator to associate name of artists to their genre.

        :param artists: list of artist names
        :return: genres, one at the time. This allow to save progress.
        """

        for artist in artists:

            yield self._find_genre(artist)

    def _find_genre(self, artist):

        res = self._find_artist(artist)

        if 'tag-list' not in res:

            if self._debug:

                print("Could not find artist %s" % artist)

            return '', None

        else:

            if self._debug:

                print(res)

        # The tag tag-list contains the genres as given by users
        tag_list = res['tag-list']

        # Loop over all the genres and found the most important one (the one given by the majority of users)
        genre = None

        if len(tag_list) > 0:

            # Order by count
            count = -1

            # d is a dictionary with two keys: 'name' and 'count', representing respectively the name for the genre
            # and the number of times that name has been associated with the current artist
            for d in tag_list:

                # See if we can convert to genre
                try:

                    this_genre = self._genre_solver[d['name']]

                except:

                    # Try matching a simple regular expression
                    m = re.match(".*(rock|pop|jazz|blues|electronic|country|hip\s?hop).*", d['name'])

                    if m is not None:

                        this_genre = m.groups()[0]

                    else:

                        # Couldn't understand this genre, let's continue
                        continue

                # Count represents the number of times the current genre has been associated with this
                # artist
                this_count = int(d['count'])

                # If the current count is larger than the previous one, this genre has been associated
                # more times with this artist than previous ones
                if this_count > count:

                    genre = this_genre
                    count = this_count

            if genre is None:

                print("Couldn't make up genre from:")
                print(tag_list)

        return res['name'], genre

    def _find_artist(self, artist):
        """
        Interrogate the remote database and return the artist info

        :param artist: name of one artist
        :return: artist dictionary (or None if artist is not found)
        """

        try:

            result = self._throttled_query.search_artists(name_regularizer.regularize(artist))

        except mb.WebServiceError as exc:

            print("Something went wrong with the request: %s" % exc)

            return {}

        score = 0.0

        found = {}

        for artist in result['artist-list']:

            this_score = float(artist['ext:score'])

            if this_score > score and this_score > 85:

                found = artist

                score = float(artist['ext:score'])

        return found