# SIGIR 2023 Paper Assignment Scripts

These scripts were used to assign papers to reviewers in SIGIR 2023.

## Installation

Python 3.7 was used to run the scripts.

Please install necessary packages by `pip install -r requirements.txt`

## How to use

### 1. Download EasyChair files and put them into a directory.

Please download the following files from EasyChair:

Assignment -> Download in CSV
- reviewer.csv
- conflict.csv
- bid.csv   
- reviewer_topic.csv
- submission_topic.csv

Go to Premium -> Conference data download -> Excel,
check "Program committee", "Submissions", and "Authors", and download the Excel file.
The file should be renamed "easychair.xlsx".

All the files above should be in the same directory.

Samples files are in the `sample_data` directory.

### 2. Prepare a list of PC members.

Please create an Excel file that contains a single sheet listing all the PC members to be assigned.
You can copy the "Program committee" sheet of easychair.xlsx
and append "max" column that indicates the individual upper bound of the number of assigned papers.

If you want to assign papers to PCs and SPCs separately,
you can create an PC list Excel file for each.

An example can be found at `sample_data/pc.xlsx`.


### 3. Run `compute_score.py` to compute the score of assignment.

```
usage: compute_score.py [-h] input_dirpath

This script computes the score of each assignment.

positional arguments:
  input_dirpath  The directory where files from EasyChair are located.
```

By running this script, you can obtain `[input_dirpath]/score.xlsx`,
which contains the score of each assignment.
This file is necessary for the next step.

You can try this program with the same data as follows:

```$ python compute_score.py sample_data```


### 4. Run `assign.py` to assign papers to each reviewer.


```
usage: assign.py [-h] --assign_num ASSIGN_NUM --default_min DEFAULT_MIN
                 --default_max DEFAULT_MAX --country_coi_max COUNTRY_COI_MAX
                 [--max_no_bid MAX_NO_BID]
                 pc_filepath input_dirpath output_filepath

This script outputs the optimal assignment under given constraints.

positional arguments:
  pc_filepath           Excel file containing PC or SPC members.
  input_dirpath         Directory where files from EasyChair are located.
  output_filepath       CSV file including the output assignments.

optional arguments:
  -h, --help            show this help message and exit
  --assign_num ASSIGN_NUM
                        Number of reviewers per paper.
  --default_min DEFAULT_MIN
                        Default value of the minimum number of papers per
                        reviewer.
  --default_max DEFAULT_MAX
                        Default value of the maximum number of papers per
                        reviewer.
  --country_coi_max COUNTRY_COI_MAX
                        Maximum number of reviewers per paper who belong to
                        the same country/region as the authors of the paper.
  --max_no_bid MAX_NO_BID
                        Format: [min_bid_num1]:[max_no_bid1],[min_bid_num2]:[m
                        ax_no_bid2],... A special constraint that only
                        [max_no_bid] or fewer papers are assigned to reviewers
                        who bid [min_bid_num] or more papers.
```


After running the `compute_score.py`, you can try this script as follows:

```$ python assign.py sample_data/pc.xlsx sample_data/ assignment.csv --assign_num 1 --default_min 0 --default_max 1 --country_coi_max 1```


Each line of the output file follows the format below:
```
[reviewer ID],[paper ID]
``` 


### 5. Run `test_assignment.py` to ensure that the assignment was successfully conducted.

```
usage: test_assignment.py [-h] --assign_num ASSIGN_NUM --default_max
                          DEFAULT_MAX --country_coi_max COUNTRY_COI_MAX
                          input_dirpath pc_filepath input_filepath
                          output_filepath

This script outputs the assignment statistics.

positional arguments:
  input_dirpath         Directory where files from EasyChair are located.
  pc_filepath           Excel file containing PC or SPC members.
  input_filepath        CSV file output by assing.py
  output_filepath       Excel file including the assignment statistics.

optional arguments:
  -h, --help            show this help message and exit
  --assign_num ASSIGN_NUM
                        Number of reviewers per paper.
  --default_max DEFAULT_MAX
                        Default value of the maximum number of papers per
                        reviewer.
  --country_coi_max COUNTRY_COI_MAX
                        Maximum number of reviewers per paper who belong to
                        the same country/region as the authors of the paper.
```

While running this script is optional, you can see some statistics of the assignment to ensure whether the assignment is successful.

For example, you can produce the statistics of `assignment.csv` as follows:
```
python test_assignment.py sample_data/ sample_data/pc.xlsx assignment.csv assignment_stat.xlsx --assign_num 1 --default_max 1 --country_coi_max 1
```
where optional arguments should be the same as those given to `assign.py`.


### 6. Upload the assignment CSV file to EasyChair.

Finally, you can upload the assignment CSV file at "Assignment -> Upload in CSV" in EasyChair.
