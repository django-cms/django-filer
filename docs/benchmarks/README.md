# Query scaling benchmarks

The query and tree harnesses compare committed source snapshots using the
project's test settings, an in-memory SQLite database, a local-memory cache,
and synthetic base `File` records without storage or thumbnail I/O.

The latest matrix was measured on 2026-10-18 against baseline `a011dbd5` and
PR revision `16a0d96c`. Both harnesses use this same baseline. No earlier timings
are reused. Python 3.12 versus 3.14 is compared on Django 5.2; Django 5.2 versus
6.0 is compared on Python 3.14.

The later `5f3afb5f` commit only adds an explicit `return None` to a tree
helper. That helper compiles to identical instruction bytecode on Python 3.12
and 3.14 (source-location metadata differs). Timings remain attributed to
`16a0d96c`, the source snapshot actually measured.

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
after=$(git rev-parse 16a0d96c)
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
implementation returns evaluated querysets from one SQL query for base `File`
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
empty permission results are recomputed to preserve compatibility. Repeated empty-result checks are 16–22% slower in this rerun, with unchanged
SQL counts (0.82–0.86×). Timing ratios below 1 represent slowdowns and are
retained in the tables.

## Recorded query results

Each runtime cell is **before → after milliseconds (speedup)**. SQL counts are
identical across the three environments. See [results.json](results.json) for
all samples, model counts, environment versions, and output fingerprints.

| Workload | Size | Python 3.12.15 / Django 5.2.18 | Python 3.14.8 / Django 5.2.18 | Python 3.14.8 / Django 6.0.9 | SQL queries |
|---|---:|---:|---:|---:|---:|
| Rendered file listing, page 1 | 100 | 34.18 → 35.71 (0.96×) | 37.07 → 37.01 (1.00×) | 35.51 → 39.39 (0.90×) | 4 → 5 |
| Rendered file listing, page 1 | 1,000 | 62.49 → 36.44 (1.71×) | 71.84 → 36.72 (1.96×) | 71.54 → 37.11 (1.93×) | 4 → 5 |
| Rendered file listing, page 1 | 10,000 | 370.57 → 38.37 (9.66×) | 416.36 → 38.45 (10.83×) | 428.20 → 38.05 (11.25×) | 4 → 5 |
| Rendered file search, page 1 | 100 | 34.18 → 36.02 (0.95×) | 37.85 → 36.89 (1.03×) | 36.26 → 36.56 (0.99×) | 4 → 5 |
| Rendered file search, page 1 | 1,000 | 61.97 → 37.12 (1.67×) | 71.29 → 37.23 (1.91×) | 67.83 → 37.09 (1.83×) | 4 → 5 |
| Rendered file search, page 1 | 10,000 | 364.42 → 37.84 (9.63×) | 425.17 → 39.43 (10.78×) | 411.99 → 39.28 (10.49×) | 4 → 5 |
| Rendered folder counts | 25 | 21.04 → 15.01 (1.40×) | 23.19 → 15.04 (1.54×) | 23.00 → 15.13 (1.52×) | 54 → 5 |
| Rendered folder counts | 100 | 53.76 → 30.59 (1.76×) | 57.72 → 29.85 (1.93×) | 57.51 → 30.71 (1.87×) | 204 → 5 |
| Overlapping grants at every level, cold | 25 | 45.78 → 0.50 (91.02×) | 52.15 → 0.54 (97.33×) | 52.39 → 0.54 (97.53×) | 351 → 2 |
| Overlapping grants at every level, cold | 50 | 173.71 → 0.54 (323.36×) | 198.57 → 0.59 (337.65×) | 196.95 → 0.59 (334.15×) | 1,326 → 2 |
| Overlapping grants at every level, cold | 100 | 693.28 → 0.65 (1072.84×) | 773.37 → 0.71 (1086.00×) | 763.77 → 0.71 (1077.57×) | 5,151 → 2 |
| Single root grant, cold | 25 | 3.70 → 2.68 (1.38×) | 4.21 → 2.96 (1.42×) | 4.18 → 2.95 (1.42×) | 27 → 26 |
| Single root grant, cold | 50 | 6.91 → 4.97 (1.39×) | 7.93 → 5.53 (1.43×) | 7.85 → 5.51 (1.43×) | 52 → 51 |
| Single root grant, cold | 100 | 14.34 → 9.68 (1.48×) | 15.53 → 10.66 (1.46×) | 15.62 → 10.66 (1.46×) | 102 → 101 |
| Repeated empty permission checks | 100 | 24.68 → 30.10 (0.82×) | 27.97 → 32.78 (0.85×) | 28.16 → 33.14 (0.85×) | 100 → 100 |
| Repeated empty permission checks | 1,000 | 249.40 → 300.14 (0.83×) | 279.75 → 327.03 (0.86×) | 284.05 → 328.76 (0.86×) | 1,000 → 1,000 |
| Duplicate group, consumed | 100 | 69.86 → 1.05 (66.50×) | 82.78 → 1.21 (68.37×) | 84.10 → 1.21 (69.77×) | 101 → 1 |
| Duplicate group, consumed | 200 | 270.03 → 1.70 (158.91×) | 302.05 → 1.94 (155.94×) | 304.74 → 1.94 (157.06×) | 201 → 1 |
| Duplicate group, consumed | 400 | 1073.19 → 3.04 (353.00×) | 1155.19 → 3.44 (336.09×) | 1155.20 → 3.55 (325.55×) | 401 → 1 |
| Mostly unique SHA1s, one two-file group | 100 | 12.52 → 0.46 (27.01×) | 14.38 → 0.48 (30.14×) | 14.26 → 0.48 (29.95×) | 101 → 1 |
| Mostly unique SHA1s, one two-file group | 400 | 53.10 → 0.56 (94.12×) | 60.21 → 0.56 (107.16×) | 59.92 → 0.57 (105.20×) | 401 → 1 |

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
| Descendant IDs of root | 50 | 13.22 → 0.52 (25.20×) | 14.89 → 0.57 (26.19×) | 14.70 → 0.57 (25.67×) | 101 → 3 |
| Descendant IDs of root | 200 | 52.28 → 1.08 (48.26×) | 59.16 → 1.15 (51.31×) | 58.58 → 1.16 (50.60×) | 401 → 3 |
| Search limited to root folder | 50 | 48.89 → 33.67 (1.45×) | 51.99 → 35.72 (1.46×) | 51.90 → 34.92 (1.49×) | 107 → 9 |
| Search limited to root folder | 200 | 99.35 → 31.64 (3.14×) | 112.62 → 32.50 (3.47×) | 110.51 → 33.77 (3.27×) | 407 → 8 |
| Folder edit permission check | 50 | 44.49 → 5.35 (8.31×) | 50.19 → 6.28 (7.99×) | 49.63 → 5.84 (8.50×) | 308 → 13 |
| Folder edit permission check | 200 | 177.37 → 16.22 (10.93×) | 198.14 → 18.12 (10.94×) | 196.75 → 18.27 (10.77×) | 1,208 → 13 |
| Copy/move destination choices | 50 | 44.40 → 5.61 (7.92×) | 50.23 → 6.13 (8.19×) | 49.66 → 6.13 (8.10×) | 311 → 15 |
| Copy/move destination choices | 200 | 175.79 → 18.94 (9.28×) | 198.26 → 20.59 (9.63×) | 198.25 → 20.65 (9.60×) | 1,211 → 15 |
| Rendered delete confirmation | 50 | 59.48 → 24.73 (2.41×) | 62.36 → 26.55 (2.35×) | 62.89 → 27.09 (2.32×) | 273 → 27 |
| Rendered delete confirmation | 200 | 191.28 → 63.05 (3.03×) | 215.20 → 70.23 (3.06×) | 215.85 → 70.22 (3.07×) | 1,023 → 27 |
| Copy/move confirmation listing | 50 | 34.22 → 6.90 (4.96×) | 38.48 → 7.60 (5.06×) | 38.29 → 7.38 (5.19×) | 204 → 8 |
| Copy/move confirmation listing | 200 | 135.88 → 23.67 (5.74×) | 150.49 → 25.57 (5.88×) | 151.48 → 26.32 (5.75×) | 804 → 8 |
| Rendered search as staff user | 25 | 23.19 → 19.14 (1.21×) | 22.12 → 19.48 (1.14×) | 22.25 → 19.43 (1.15×) | 36 → 10 |
| Rendered search as staff user | 100 | 50.69 → 38.22 (1.33×) | 53.69 → 40.16 (1.34×) | 52.39 → 39.78 (1.32×) | 111 → 10 |
| Pick-folder popup search | 25 | 22.78 → 14.74 (1.55×) | 23.78 → 14.05 (1.69×) | 23.77 → 14.05 (1.69×) | 83 → 10 |
| Pick-folder popup search | 100 | 68.80 → 32.81 (2.10×) | 71.27 → 30.18 (2.36×) | 71.23 → 30.09 (2.37×) | 308 → 10 |
