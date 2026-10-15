# Query scaling benchmarks

The query and tree harnesses compare committed source snapshots using the
project's test settings, an in-memory SQLite database, a local-memory cache,
and synthetic base `File` records without storage or thumbnail I/O.

The latest matrix was measured on 2026-10-15 against baseline `a011dbd5` and
PR revision `4a2255f1`. Both harnesses use this same baseline. No earlier timings
are reused. Python 3.12 versus 3.14 is compared on Django 5.2; Django 5.2 versus
6.0 is compared on Python 3.14.

| Configuration | Python | Django | SQLite |
|---|---|---|---|
| py312-dj52 | 3.12.15 | 5.2.18 | 3.54.0 |
| py314-dj52 | 3.14.8 | 5.2.18 | 3.54.0 |
| py314-dj60 | 3.14.8 | 6.0.9 | 3.54.0 |

All environments use django-polymorphic 4.11.7 on macOS ARM64. Exact dependency
versions are recorded per environment in `results.json` and `tree_results.json`.
Compare before/after within each environment; cross-environment differences
include the interpreter and dependency/runtime effects recorded there.

## Reproduce

Create an environment for each row, install its Django requirements file and
this package, and use that environment's `python` in the recipe below. For exact
reproduction, pin dependencies to the corresponding `packages` mapping in the
raw results. Repeat for both `query_scaling.py` and `tree_scaling.py`.

```sh
bench_dir=$(mktemp -d)
before=$(git rev-parse a011dbd5)
after=$(git rev-parse 4a2255f1)
mkdir "$bench_dir/before" "$bench_dir/after"
git archive "$before" | tar -x -C "$bench_dir/before"
git archive "$after" | tar -x -C "$bench_dir/after"

for pair in 1 2 3; do
    set -- before after
    if [ "$pair" = 2 ]; then set -- after before; fi
    for side in "$@"; do
        revision="$before"
        if [ "$side" = after ]; then revision="$after"; fi
        PYTHONHASHSEED=0 python docs/benchmarks/query_scaling.py \
            --source "$bench_dir/$side" --revision "$revision" \
            --output "$bench_dir/$side-$pair.json"
    done
done
```

Each invocation is a fresh process with two warmups and five timed samples per
workload. Run processes sequentially, alternating revision order as above. The
recorded run also rotates the three environments between rounds. Table values
are medians of all 15 samples per revision/workload/environment.

The 36 processes cover two harnesses, two revisions, three environments, and
three repetitions. All 37 workload outputs match before/after across all six
processes in each environment: 111 validated workload/environment comparisons.
SQL counts and, for the query harness, model-instantiation counts are stable
across repetitions. Raw artifacts retain every timing sample and fingerprint.

The authenticated listing and search workloads render complete HTML through the
Django test client. Folder-count workloads include one child folder and one file
per displayed folder. Page size is 100. Session storage is cache-backed.

Permission workloads distinguish a grant at every level from one grant at the
root. Both start with a cold permission cache. Empty-result workloads prime an
empty cached result before measuring repeated checks. Fixture creation and cache
preparation are outside timings. Each case rolls back its database transaction.

Duplicate workloads consume every returned group. Mostly-unique cases contain
one two-file duplicate group and unique digests for all remaining files. The new
implementation returns concrete groups from one SQL query for base `File`
records; polymorphic subclasses can add subtype queries. Aggregation still
scans/groups database values, so this does not establish index performance.

SQL and model-instantiation counts are recorded in a separate untimed invocation.
Output fingerprints are also computed outside timings. HTML normalization replaces
only randomized CSRF tokens; listing fixture timestamps are fixed. Outputs must
match between revisions within each environment, not between Django versions.
Object counts are not peak memory.

These are local, single-process measurements. They exclude network, browser,
concurrency, production database latency, real image subclasses, and storage I/O.
Single-root traversal issues one query per level, including the leaf lookup, plus
the permission query; 100 folders require 101 queries. Overlapping grants can
finish in two queries when all folders are roots and fit in one batch. Repeated
empty permission results are recomputed to preserve compatibility. Timing ratios
below 1 represent slowdowns and are retained in the tables.

## Recorded query results

Each runtime cell is **before → after milliseconds (speedup)**. SQL counts are
identical across the three environments. See [results.json](results.json) for
all samples, model counts, environment versions, and output fingerprints.

| Workload | Size | Python 3.12.15 / Django 5.2.18 | Python 3.14.8 / Django 5.2.18 | Python 3.14.8 / Django 6.0.9 | SQL queries |
|---|---:|---:|---:|---:|---:|
| Rendered file listing, page 1 | 100 | 34.27 → 34.70 (0.99×) | 35.53 → 36.80 (0.97×) | 35.86 → 36.54 (0.98×) | 4 → 5 |
| Rendered file listing, page 1 | 1,000 | 62.18 → 35.17 (1.77×) | 71.41 → 36.66 (1.95×) | 69.84 → 36.93 (1.89×) | 4 → 5 |
| Rendered file listing, page 1 | 10,000 | 367.02 → 36.98 (9.93×) | 414.24 → 38.19 (10.85×) | 412.66 → 38.61 (10.69×) | 4 → 5 |
| Rendered file search, page 1 | 100 | 34.22 → 34.97 (0.98×) | 35.93 → 36.54 (0.98×) | 35.83 → 36.83 (0.97×) | 4 → 5 |
| Rendered file search, page 1 | 1,000 | 61.65 → 35.20 (1.75×) | 70.13 → 36.96 (1.90×) | 68.41 → 37.95 (1.80×) | 4 → 5 |
| Rendered file search, page 1 | 10,000 | 351.26 → 37.61 (9.34×) | 416.97 → 40.13 (10.39×) | 393.28 → 39.69 (9.91×) | 4 → 5 |
| Rendered folder counts | 25 | 21.06 → 14.78 (1.42×) | 21.49 → 14.99 (1.43×) | 21.53 → 15.05 (1.43×) | 54 → 5 |
| Rendered folder counts | 100 | 52.82 → 29.15 (1.81×) | 55.76 → 29.70 (1.88×) | 56.08 → 29.98 (1.87×) | 204 → 5 |
| Overlapping grants at every level, cold | 25 | 46.03 → 0.46 (100.50×) | 52.14 → 0.51 (103.24×) | 51.43 → 0.51 (99.89×) | 351 → 2 |
| Overlapping grants at every level, cold | 50 | 174.72 → 0.51 (339.81×) | 197.93 → 0.56 (356.39×) | 195.35 → 0.56 (346.75×) | 1,326 → 2 |
| Overlapping grants at every level, cold | 100 | 680.66 → 0.62 (1100.65×) | 766.20 → 0.68 (1126.77×) | 761.74 → 0.68 (1114.61×) | 5,151 → 2 |
| Single root grant, cold | 25 | 3.73 → 3.34 (1.12×) | 4.20 → 3.68 (1.14×) | 4.17 → 3.71 (1.12×) | 27 → 26 |
| Single root grant, cold | 50 | 6.95 → 6.37 (1.09×) | 7.90 → 7.04 (1.12×) | 7.83 → 7.15 (1.10×) | 52 → 51 |
| Single root grant, cold | 100 | 14.38 → 12.46 (1.15×) | 15.46 → 13.75 (1.12×) | 15.29 → 13.88 (1.10×) | 102 → 101 |
| Repeated empty permission checks | 100 | 24.75 → 25.80 (0.96×) | 27.85 → 28.25 (0.99×) | 27.75 → 28.24 (0.98×) | 100 → 100 |
| Repeated empty permission checks | 1,000 | 247.65 → 257.22 (0.96×) | 279.12 → 280.84 (0.99×) | 278.28 → 281.56 (0.99×) | 1,000 → 1,000 |
| Duplicate group, consumed | 100 | 68.86 → 1.02 (67.69×) | 83.23 → 1.17 (70.87×) | 82.46 → 1.19 (69.49×) | 101 → 1 |
| Duplicate group, consumed | 200 | 266.13 → 1.67 (159.67×) | 303.87 → 1.91 (158.87×) | 299.78 → 1.92 (156.42×) | 201 → 1 |
| Duplicate group, consumed | 400 | 1031.48 → 2.92 (352.89×) | 1142.77 → 3.43 (333.32×) | 1146.00 → 3.41 (336.38×) | 401 → 1 |
| Mostly unique SHA1s, one two-file group | 100 | 12.48 → 0.41 (30.65×) | 14.30 → 0.44 (32.25×) | 14.41 → 0.45 (32.18×) | 101 → 1 |
| Mostly unique SHA1s, one two-file group | 400 | 52.80 → 0.49 (108.30×) | 60.11 → 0.53 (113.84×) | 60.34 → 0.54 (112.31×) | 401 → 1 |

## Tree and search workloads

Trees have one root, `size` children, and one grandchild per child. Each grandchild
has one file for limited search, permission checks, destinations, delete
confirmation, and copy/move listing. Permission workloads use a staff user with
a subtree grant and a cold permission cache. Search page size is 100.

The copy/move listing workload measures confirmation-list construction, not file
copying or moving. The edit-check workload measures a separate permission walk.

## Recorded tree results

Each runtime cell is **before → after milliseconds (speedup)**. SQL counts are
identical across the three environments. See [tree_results.json](tree_results.json)
for all samples, environment versions, and output fingerprints.

| Workload | Size | Python 3.12.15 / Django 5.2.18 | Python 3.14.8 / Django 5.2.18 | Python 3.14.8 / Django 6.0.9 | SQL queries |
|---|---:|---:|---:|---:|---:|
| Descendant IDs of root | 50 | 13.27 → 0.58 (22.88×) | 14.89 → 0.63 (23.70×) | 14.68 → 0.62 (23.64×) | 101 → 3 |
| Descendant IDs of root | 200 | 52.14 → 1.12 (46.68×) | 59.05 → 1.21 (48.96×) | 58.60 → 1.20 (48.99×) | 401 → 3 |
| Search limited to root folder | 50 | 48.17 → 33.68 (1.43×) | 51.74 → 35.01 (1.48×) | 53.35 → 34.60 (1.54×) | 107 → 9 |
| Search limited to root folder | 200 | 99.36 → 31.59 (3.15×) | 112.20 → 32.33 (3.47×) | 110.94 → 33.88 (3.27×) | 407 → 8 |
| Folder edit permission check | 50 | 44.32 → 5.08 (8.73×) | 49.87 → 5.71 (8.73×) | 49.92 → 5.64 (8.85×) | 308 → 13 |
| Folder edit permission check | 200 | 173.47 → 15.76 (11.01×) | 197.92 → 18.13 (10.91×) | 196.84 → 17.96 (10.96×) | 1,208 → 13 |
| Copy/move destination choices | 50 | 44.34 → 5.63 (7.88×) | 49.92 → 6.24 (8.00×) | 49.87 → 6.17 (8.08×) | 311 → 15 |
| Copy/move destination choices | 200 | 175.33 → 18.90 (9.28×) | 197.60 → 20.83 (9.49×) | 195.89 → 20.64 (9.49×) | 1,211 → 15 |
| Rendered delete confirmation | 50 | 56.37 → 24.52 (2.30×) | 62.13 → 26.57 (2.34×) | 62.24 → 26.43 (2.35×) | 273 → 27 |
| Rendered delete confirmation | 200 | 191.66 → 62.32 (3.08×) | 215.13 → 68.97 (3.12×) | 214.37 → 70.79 (3.03×) | 1,023 → 27 |
| Copy/move confirmation listing | 50 | 34.24 → 6.81 (5.03×) | 38.19 → 7.51 (5.09×) | 38.09 → 7.50 (5.08×) | 204 → 8 |
| Copy/move confirmation listing | 200 | 134.52 → 23.41 (5.75×) | 150.14 → 25.78 (5.82×) | 150.47 → 25.42 (5.92×) | 804 → 8 |
| Rendered search as staff user | 25 | 21.50 → 18.77 (1.15×) | 21.87 → 19.13 (1.14×) | 22.08 → 19.20 (1.15×) | 36 → 10 |
| Rendered search as staff user | 100 | 49.02 → 37.68 (1.30×) | 51.87 → 41.05 (1.26×) | 51.61 → 39.17 (1.32×) | 111 → 10 |
| Pick-folder popup search | 25 | 22.65 → 13.96 (1.62×) | 23.62 → 13.91 (1.70×) | 23.52 → 13.79 (1.71×) | 83 → 10 |
| Pick-folder popup search | 100 | 65.45 → 29.73 (2.20×) | 70.79 → 30.27 (2.34×) | 69.04 → 29.84 (2.31×) | 308 → 10 |
