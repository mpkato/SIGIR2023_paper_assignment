import pandas as pd
import os
from collections import defaultdict
from settings import ASSIGNMENT_SCORES

def parse_topics(df):
    topics = defaultdict(set)
    for idx, (identifier, topic) in df.iterrows():
        topics[identifier].add(topic)
    return topics

def add_topic_score(input_dirpath):
    rev_topic_filepath = os.path.join(args.input_dirpath, "reviewer_topic.csv")
    rev_topic_df = pd.read_csv(rev_topic_filepath, header=None)
    rev_topics = parse_topics(rev_topic_df)

    paper_topic_filepath = os.path.join(args.input_dirpath, "submission_topic.csv")
    paper_topic_df = pd.read_csv(paper_topic_filepath, header=None)
    paper_topics = parse_topics(paper_topic_df)

    topic_scores = []
    for rid in rev_topics:
        for pid in paper_topics:
            fit = len(rev_topics[rid] & paper_topics[pid])
            if fit > 0:
                score = fit * ASSIGNMENT_SCORES["topic"]
                topic_scores.append([rid, pid, score])
    topic_score_df = pd.DataFrame(topic_scores, columns=["rid", "pid", "score"])
    return topic_score_df


def merge_score_dfs(dfs):
    scores = defaultdict(int)
    for df in dfs:
        for idx, (rid, pid, score) in df.iterrows():
            scores[(rid, pid)] += score
    scores = [(rid, pid, score) for (rid, pid), score in scores.items()]
    score_df = pd.DataFrame(scores, columns=["rid", "pid", "score"])
    return score_df

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser(description="This script computes the score of each assignment. "
                            "The scores are output in [input_dirpath]/score.xlsx")
    parser.add_argument("input_dirpath",
                        help="The directory where files from EasyChair are located.")
    args = parser.parse_args()

    # topical fit
    topic_score_df = add_topic_score(args.input_dirpath)

    # bid
    bid_filepath = os.path.join(args.input_dirpath, "bid.csv")
    bid_df = pd.read_csv(bid_filepath, header=None)
    bid_df.columns = ["rid", "pid", "pref"]
    bid_df["score"] = bid_df.pref.apply(lambda x: ASSIGNMENT_SCORES[x])
    bid_df = bid_df[["rid", "pid", "score"]]

    # declared COI
    coi_filepath = os.path.join(args.input_dirpath, "conflict.csv")
    coi_df = pd.read_csv(coi_filepath, header=None)
    coi_df.columns = ["rid", "pid"]
    coi_df["score"] = ASSIGNMENT_SCORES["conflict"]

    score_df = merge_score_dfs([topic_score_df, bid_df, coi_df])
    score_filepath = os.path.join(args.input_dirpath, "score.xlsx")
    score_df.to_excel(score_filepath, index=None)
