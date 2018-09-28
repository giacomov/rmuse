import pandas as pd
import numpy as np


class OriginalityScore(object):

    def __init__(self, binomials_file):

        df1 = pd.read_hdf(binomials_file)  # type: pd.DataFrame

        df2 = df1.copy()  # type: pd.DataFrame
        new_index = df2.index.str.replace("|", "")
        df2.set_index(new_index, inplace=True)

        self._df = pd.concat([df1, df2])

    def _compute_scores(self, seq):

        # Divide sequences in binomials
        seq_list = seq.split(" ")

        n = len(seq_list)

        binomials = [seq_list[i:i + 2] for i in range(n - 1)]

        # Accumulate the score for each binomial
        scores = []

        for binomial in binomials:

            try:

                scores.append(self._df.loc[" ".join(binomial)]['freq'])

            except KeyError:

                scores.append(0)

        return np.array(scores)

    def originality_ranking(self, seq):

        score = self.get(seq)

        bins = [0.93213195, 0.98748184, 0.99929992, 1.02716672, 1.04493579,
                1.11215457, 1.1422417, 1.1567116, 1.18432453, 1.199464,
                1.21132991, 1.2259034, 1.23468122, 1.24551665, 1.2563542,
                1.26145325, 1.26533113, 1.26868, 1.27149013, 1.27388701,
                1.2776633, 1.28731899, 1.3103007, 1.32013475, 1.33125573,
                1.33424145, 1.3543653, 1.36695061, 1.37436511, 1.38655104,
                1.39388425, 1.39686085, 1.41735579, 1.43035331, 1.4429093,
                1.44944341, 1.45704017, 1.46463391, 1.49366259, 1.52715705,
                1.55726702, 1.56887525, 1.57908562, 1.6216297, 1.63301693,
                1.68213129, 1.70157119, 1.71125834, 1.73588593, 1.77805626,
                1.82844388, 1.86247488, 1.89750024, 1.91923205, 1.93583459,
                1.94815058, 1.95943441, 1.97492207, 1.98796137, 2.00715281,
                2.01826435, 2.02609241, 2.03620156, 2.04622862, 2.0540805,
                2.06432736, 2.07953478, 2.10402444, 2.13672058, 2.15131994,
                2.17020714, 2.20266509, 2.25826892, 2.28926969, 2.32009056,
                2.35539285, 2.37615052, 2.40906038, 2.44552785, 2.4786656,
                2.52073999, 2.56117427, 2.59336809, 2.63969179, 2.68924895,
                2.73279736, 2.79718025, 2.85575907, 2.91732697, 2.98420135,
                3.0444043, 3.09982279, 3.15540491, 3.21319879, 3.27989892,
                3.36429029, 3.4750827, 3.60017179, 3.74521845, 4.00912328,
                5.25458901]

        rank = np.digitize(score, bins)

        return rank / float(10)

    def get(self, seq):

        return np.log10(self._originality_two(seq))

    def _originality_one(self, seq):

        scores = self._compute_scores(seq)

        # Get the average of all but the most original
        n = len(scores)

        if n < 1:

            return 0

        elif n == 1:

            return scores[0]

        else:

            idx = np.argmin(scores)

            min_ = scores[idx]

            avg = np.average(np.delete(scores, [idx]))

            return 1.0 / np.average([min_, avg])

    def _originality_two(self, seq):

        scores = self._compute_scores(seq)

        # Get the average of all but the most original
        n = len(scores)

        if n < 1:

            return 0

        elif n == 1:

            return scores[0]

        else:

            min_ = scores.min()

            vv = min_ + np.median(scores)

            return 1.0 / vv
