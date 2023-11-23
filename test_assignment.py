import os
import pandas as pd
import numpy as np
from pprint import pprint
from collections import defaultdict

PREFS = ["yes", "maybe", "no"]

def main():
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("input_dirpath")
    parser.add_argument("pc_filepath")
    parser.add_argument("input_filepath")
    parser.add_argument("output_filepath")
    parser.add_argument("--assign_num", type=int, required=True)
    parser.add_argument("--default_max", type=int, required=True)
    parser.add_argument("--country_coi_max", type=int, required=True)
    parser.add_argument("--no_strict", action="store_true")
    args = parser.parse_args()

    result_stat = []

    paper_filepath = os.path.join(args.input_dirpath, "easychair.xlsx")
    paper_df = pd.read_excel(paper_filepath, "Submissions")
    author_df = pd.read_excel(paper_filepath, "Authors")
    paper_ids = paper_df["#"].astype(int).tolist()
    paper_df.set_index("#", inplace=True)

    pc_df = pd.read_excel(args.pc_filepath)
    pc_num = len(pc_df)
    reviewer_filepath = os.path.join(args.input_dirpath, "reviewer.csv")
    rev_df = pd.read_csv(reviewer_filepath, header=None)
    rev_df.columns = ["id", "name", "email", "role"]
    pc_df = pc_df.merge(rev_df, on="email")
    assert pc_num == len(pc_df)
    reviewer_ids = pc_df["id"].astype(int).tolist()
    reviewer_ids_set = set(reviewer_ids)
    pc_df.set_index("id", inplace=True)

    assign_df = pd.read_csv(args.input_filepath, header=None)
    assign_df.columns = ["rid", "pid"]
    rev_papers = defaultdict(set)
    paper_revs = defaultdict(set)
    for idx, (rid, pid) in assign_df.iterrows():
        if not args.no_strict or rid in reviewer_ids_set:
            rev_papers[rid].add(pid)
            paper_revs[pid].add(rid)
    
    assert set(rev_papers).issubset(set(reviewer_ids))
    result_stat.append(["# of reviewers", len(set(reviewer_ids))])
    assert set(paper_revs) == set(paper_ids)
    result_stat.append(["# of papers", len(set(paper_ids))])

    violation = 0
    for r, papers in rev_papers.items():
        max_num = pc_df.at[r, "max"]
        max_num = max_num if not np.isnan(max_num) else args.default_max
        if not (len(papers) <= max_num):
            violation += 1
            print("Upper bound violation:", r)
    result_stat.append(["# of upper bound violation", violation])

    coi_filepath = os.path.join(args.input_dirpath, "conflict.csv")
    coi_df = pd.read_csv(coi_filepath, header=None)
    coi_df.columns = ["rid", "pid"]
    violation = 0
    for idx, (rid, pid) in coi_df.iterrows():
        assert pid in paper_revs
        if rid in rev_papers and pid in rev_papers[rid]:
            violation += 1
            print("COI violation: ", rid, pid)
    result_stat.append(["# of COI violation", violation])

    paper_countries = defaultdict(set)
    for idx, (pid, country) in author_df[["submission #", "country"]].iterrows():
        paper_countries[pid].add(country)

    country_samples = set(pc_df["country"].tolist())
    violation = 0
    for p, reviewers in paper_revs.items():
        countries = paper_countries[p]
        country_coi_num = 0
        for r in reviewers:
            if pc_df.at[r, "country"] in countries:
                country_coi_num += 1
        if country_coi_num > args.country_coi_max:
            violation += 1
            print("Country COI violation:", rid, pid)
    result_stat.append(["# of country COI violation", violation])

    # statistics
    bid_filepath = os.path.join(args.input_dirpath, "bid.csv")
    bid_df = pd.read_csv(bid_filepath, header=None)
    bid_df.columns = ["rid", "pid", "pref"]
    bidding_rev = defaultdict(lambda: dict())
    bidding_paper = defaultdict(lambda: dict())
    for idx, (rid, pid, pref) in bid_df.iterrows():
        if rid in reviewer_ids_set:
            bidding_rev[rid][pid] = pref
            bidding_paper[pid][rid] = pref

    rev_num_sat = defaultdict(int)
    for r, papers in rev_papers.items():
        num = len(papers)
        rev_num_sat[num] += 1
    for num in sorted(rev_num_sat):
        result_stat.append([f"# of reviewers with {num} papers", rev_num_sat[num]])
    paper_sat = defaultdict(int)
    for p, reviewers in paper_revs.items():
        num = len(set(reviewers) & set(bidding_paper[p]))
        paper_sat[num] += 1
    for num in sorted(paper_sat):
        result_stat.append([f"# of papers with {num} willing reviewers", paper_sat[num]])
    rev_sat = defaultdict(int)
    for r, papers in rev_papers.items():
        num = len(set(papers) & set(bidding_rev[r]))
        rev_sat[num] += 1
    for num in sorted(rev_sat):
        result_stat.append([f"# of reviewers with {num} bidded paper", rev_sat[num]])

    pprint(result_stat)
    result_stat_df = pd.DataFrame(result_stat, columns=["Name", "Value"])

    last_minutes = set()
    if "last" in pc_df.columns:
        for rid in reviewer_ids:
            if pc_df.at[rid, "last"] == 1:
                last_minutes.add(rid)

    def read_topics(df):
        topics = defaultdict(set)
        for idx, (identifier, topic) in df.iterrows():
            topics[identifier].add(topic)
        return topics
    def range_str(string, num):
        return [string.format(n) for n in range(num)]
    paper_topic_filepath = os.path.join(args.input_dirpath, "submission_topic.csv")
    paper_topic_df = pd.read_csv(paper_topic_filepath, header=None)
    paper_topics = read_topics(paper_topic_df)
    rev_topic_filepath = os.path.join(args.input_dirpath, "reviewer_topic.csv")
    rev_topic_df = pd.read_csv(rev_topic_filepath, header=None)
    rev_topics = read_topics(rev_topic_df)
    result_papers = []
    for p, reviewers in paper_revs.items():
        reviewers = list(reviewers)
        countries = "/".join(list(paper_countries[p]))
        ts = "/".join(list(paper_topics[p]))
        rev_pref = [bidding_rev[r][p] if p in bidding_rev[r] else "no"
                    for r in reviewers]
        pref_dist = [rev_pref.count(pref) for pref in PREFS]
        num_bids = len(bidding_paper[p])
        num_valid_bids = len([r for r in bidding_paper[p]
                              if pc_df.at[r, "country"] not in paper_countries[p]])
        num_last_minutes = len([r for r in reviewers if r in last_minutes])
        rev_countries = [pc_df.at[r, "country"] for r in reviewers]
        rev_country_count = max([rev_countries.count(c) for c in rev_countries])
        rev_ts = ["/".join(list(rev_topics[r])) for r in reviewers]
        result_papers.append([p, paper_df.at[p, "title"], paper_df.at[p, "authors"],
                              countries, ts, num_bids, num_valid_bids, num_last_minutes,
                              rev_country_count] 
                             + pref_dist + reviewers
                             + rev_pref + rev_countries + rev_ts)
    result_paper_df = pd.DataFrame(result_papers, 
                                   columns=["Paper ID", "Title", "Authors",
                                            "Countries", "Topics", "# of bids",
                                            "# of valid bids", "# of last minute reviewers",
                                            "Most freq. countries"]
                                   + PREFS
                                   + range_str("Reviewer_{}", args.assign_num)
                                   + range_str("Bid_{}", args.assign_num)
                                   + range_str("Country_{}", args.assign_num)
                                   + range_str("Topics_{}", args.assign_num))

    def fill_list(l):
        if len(l) >= args.default_max:
            return l
        return l + [""] * (args.default_max - len(l))
    result_rev = []
    for r, papers in rev_papers.items():
        papers = list(papers)
        ts = "/".join(list(rev_topics[r]))
        country = pc_df.at[r, "country"]
        num_bids = len(bidding_rev[r])
        num_valid_bids = len([p for p in bidding_rev[r] 
                              if country not in paper_countries[p]])
        paper_prefs = fill_list([bidding_paper[p][r] if r in bidding_paper[p] else "no"
                                for p in papers])
        pref_dist = [paper_prefs.count(pref) for pref in PREFS]
        paper_cs = fill_list(["/".join(list(paper_countries[p]))
                                     for p in papers])
        paper_ts = fill_list(["/".join(list(paper_topics[p]))
                                  for p in papers])
        result_rev.append([r, pc_df.at[r, "name"], pc_df.at[r, "email"],
                           country, ts, num_bids, num_valid_bids]
                          + pref_dist + fill_list(papers)
                          + paper_prefs + paper_cs + paper_ts)
    result_rev_df = pd.DataFrame(result_rev,
                                 columns=["Reviewer ID", "Name", "Email",
                                          "Country", "Topics", "# of bids",
                                          "# of valid bids"]
                                   + PREFS
                                   + range_str("Paper_{}", args.default_max)
                                   + range_str("Bid_{}", args.default_max)
                                   + range_str("Countries_{}", args.default_max)
                                   + range_str("Topics_{}", args.default_max))

    with pd.ExcelWriter(args.output_filepath) as writer:
        result_stat_df.to_excel(writer, index=None, sheet_name='Stats')
        result_paper_df.to_excel(writer, index=None, sheet_name='Papers')
        result_rev_df.to_excel(writer, index=None, sheet_name='Reviewers')


if __name__ == '__main__':
    main()
