import random
import time
import mip
import pandas as pd
import numpy as np
import os
import re
from collections import defaultdict

TIME_LIMIT = 60 * 60
BID_SCORE = 1000

def model(paper_ids, reviewer_ids, assignments, scores, min_max,
          country_coi, country_pcs,
          assign_num, country_coi_max, max_no_bid_str):
    m = mip.Model(name='paper_assignment')

    # vars
    assignment_vars = {}
    for a in assignments:
        assignment_vars[a] = m.add_var(name=f"Var_a({a})", var_type=mip.BINARY)

    # objective
    m.objective = mip.maximize(mip.xsum((scores[r][p]) * assignment_vars[(r, p)]
                                        for r, p in assignment_vars))

    # consts
    for p in paper_ids:
        m.add_constr(
                mip.xsum(assignment_vars[(r, p)] for r in reviewer_ids) == assign_num,
                name=f"Con_Paper({p})")
        m.add_constr(
                mip.xsum(assignment_vars[(r, p)] for r in reviewer_ids 
                         if r in country_coi[p]) <= country_coi_max,
                name=f"Con_Country({p})")

    for r in reviewer_ids:
        min_num, max_num = min_max[r]
        m.add_constr(
                mip.xsum(assignment_vars[(r, p)] for p in paper_ids) <= max_num,
                name=f"Con_Max({r})")
        m.add_constr(
                mip.xsum(assignment_vars[(r, p)] for p in paper_ids) >= min_num,
                name=f"Con_MIN({r})")

    if max_no_bid_str:
        max_no_bid_settings = read_max_no_bid_str(max_no_bid_str)
        for r in reviewer_ids:
            bid_num = len([scores[r][p] for p in scores[r] if scores[r][p] >= BID_SCORE])
            for setting in max_no_bid_settings:
                min_bid, max_no_bid = setting["min_bid"], setting["max_no_bid"]
                if bid_num >= min_bid:
                    m.add_constr(
                            mip.xsum(assignment_vars[(r, p)] for p in paper_ids
                                    if scores[r][p] < BID_SCORE) <= max_no_bid,
                            name=f"Con_Max_No_Bid({r})")
                    break
    
    return m


def read_max_no_bid_str(s):
    settings = []
    for setting in s.strip().split(","):
        min_bid, max_no_bid = map(int, setting.split(":"))
        settings.append({"min_bid": min_bid, "max_no_bid": max_no_bid})
    settings = sorted(settings, key=lambda x: x["min_bid"], reverse=True)
    print(settings)
    return settings


def read_reviewers(pc_filepath, reviewer_filepath):
    pc_df = pd.read_excel(pc_filepath, engine='openpyxl')
    rev_df = pd.read_csv(reviewer_filepath, header=None)
    rev_df.columns = ["id", "name", "email", "role"]

    pc_df = pd.merge(pc_df, rev_df, on="email")
    return pc_df

def get_max_num(pc_df, default_max):
    max_nums = {}
    for idx, (rid, max_num) in pc_df[["id", "max"]].iterrows():
        rid = int(rid)
        max_nums[rid] = default_max if np.isnan(max_num) else max_num
    return max_nums

def read_scores(score_filepath):
    scores = defaultdict(lambda: defaultdict(int))
    score_df = pd.read_excel(score_filepath, engine='openpyxl')
    for idx, (rid, pid, score) in score_df.iterrows():
        rid, pid, score = int(rid), int(pid), int(score)
        scores[rid][pid] = score
    return scores

def find_country_coi(input_dirpath):
    easychair_filepath = os.path.join(input_dirpath, "easychair.xlsx")
    pc_df = pd.read_excel(easychair_filepath, "Program committee", engine='openpyxl')
    author_df = pd.read_excel(easychair_filepath, "Authors", engine='openpyxl')

    paper_countries = defaultdict(set)
    for idx, (pid, country) in author_df[["submission #", "country"]].iterrows():
        paper_countries[pid].add(country)

    rev_filepath = os.path.join(input_dirpath, "reviewer.csv")
    rev_df = pd.read_csv(rev_filepath, header=None)
    rev_df.columns = ["id", "name", "email", "role"]
    pc_df = pd.merge(pc_df, rev_df, on="email")

    country_coi = defaultdict(set)
    for idx, (rid, country) in pc_df[["id", "country"]].iterrows():
        for pid, country_set in paper_countries.items():
            if country in country_set:
                country_coi[pid].add(rid)
    return country_coi


def find_country_pcs(input_dirpath):
    easychair_filepath = os.path.join(input_dirpath, "easychair.xlsx")
    pc_df = pd.read_excel(easychair_filepath, "Program committee", engine='openpyxl')

    rev_filepath = os.path.join(input_dirpath, "reviewer.csv")
    rev_df = pd.read_csv(rev_filepath, header=None)
    rev_df.columns = ["id", "name", "email", "role"]
    pc_df = pd.merge(pc_df, rev_df, on="email")

    country_pcs = defaultdict(set)
    for idx, (rid, country) in pc_df[["id", "country"]].iterrows():
        country_pcs[country].add(rid)
    return country_pcs


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser(description="This script outputs the optimal assignment under given constraints.")
    parser.add_argument("pc_filepath", help="Excel file containing PC or SPC members.")
    parser.add_argument("input_dirpath", help="Directory where files from EasyChair are located.")
    parser.add_argument("output_filepath", help="CSV file including the output assignments.")
    parser.add_argument("--assign_num", type=int, required=True,
                        help="Number of reviewers per paper.")
    parser.add_argument("--default_min", type=int, required=True,
                        help="Default value of the minimum number of papers per reviewer.")
    parser.add_argument("--default_max", type=int, required=True,
                        help="Default value of the maximum number of papers per reviewer.")
    parser.add_argument("--country_coi_max", type=int, required=True,
                        help="Maximum number of reviewers per paper who "
                        "belong to the same country/region as the authors "
                        "of the paper.")
    parser.add_argument("--max_no_bid", type=str, default=None,
                        help="Format: [min_bid_num1]:[max_no_bid1],[min_bid_num2]:[max_no_bid2],... "
                        "A special constraint that only [max_no_bid] or fewer papers are assigned to "
                        "reviewers who bid [min_bid_num] or more papers.")
    args = parser.parse_args()

    paper_filepath = os.path.join(args.input_dirpath, "easychair.xlsx")
    paper_df = pd.read_excel(paper_filepath, "Submissions", engine='openpyxl')
    paper_ids = paper_df["#"].astype(int).tolist()
    reviewer_filepath = os.path.join(args.input_dirpath, "reviewer.csv")
    pc_df = read_reviewers(args.pc_filepath, reviewer_filepath)
    reviewer_ids = pc_df["id"].astype(int).tolist()
    max_nums = get_max_num(pc_df, args.default_max)
    score_filepath = os.path.join(args.input_dirpath, "score.xlsx")
    scores = read_scores(score_filepath)

    assignments = [(j, i) for i in paper_ids for j in reviewer_ids]
    min_max = {}
    for r in reviewer_ids:
        max_num = max_nums[r]
        min_num = min([args.default_min, max_num])
        min_max[r] = (min_num, max_num)

    country_coi = find_country_coi(args.input_dirpath)
    country_pcs = find_country_pcs(args.input_dirpath)

    m = model(paper_ids, reviewer_ids, assignments, scores,
              min_max, country_coi, country_pcs, 
              args.assign_num, args.country_coi_max, args.max_no_bid)

    m.threads = -1
    status = m.optimize(max_seconds=TIME_LIMIT)
    obj_val = m.objective_value
    is_optimal = (status == mip.OptimizationStatus.OPTIMAL)

    print("Is optimal?", is_optimal)

    output_reviewer_df = []
    for r in reviewer_ids:
        assigned_papers = [p for p in paper_ids
                if m.var_by_name(f"Var_a({(r, p)})").x == 1]
        for p in assigned_papers:
            output_reviewer_df.append([r, p])
    output_reviewer_df = pd.DataFrame(output_reviewer_df, columns=["rid", "pid"])
    output_reviewer_df.to_csv(args.output_filepath, index=None, header=None)


if __name__ == '__main__':
    main()
