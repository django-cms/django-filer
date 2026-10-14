# Query scaling benchmarks

`query_scaling.py` runs the same workloads against an extracted source snapshot.
It uses the project's test settings, an in-memory SQLite database, a local-memory
cache, and synthetic base `File` records without storage or thumbnail I/O.

Install `tests/requirements/django-6.0.txt` and the package in a Python 3.13
environment. Run from the repository root, using that environment's `python`:

```sh
bench_dir=$(mktemp -d)
before=$(git rev-parse a011dbd5)
after=$(git rev-parse c7a0b2b2)
mkdir "$bench_dir/before" "$bench_dir/after"
git archive "$before" | tar -x -C "$bench_dir/before"
git archive "$after" | tar -x -C "$bench_dir/after"

for pair in 1 2 3; do
    set -- before after
    if [ "$pair" = 2 ]; then set -- after before; fi
    for side in "$@"; do
        revision="$before"
        if [ "$side" = after ]; then revision="$after"; fi
        python docs/benchmarks/query_scaling.py \
            --source "$bench_dir/$side" --revision "$revision" \
            --output "$bench_dir/$side-$pair.json"
    done
done
```

Each invocation is a fresh process with two warmups and five timed samples per
workload. Run processes sequentially, alternating revision order as above. Take
the median of all 15 samples for each revision/workload. Compare fingerprints,
query counts, and object counts across all three repetitions before reporting.
`results.json` retains the measured samples and those checks for the recorded run.

The authenticated listing and search workloads render complete HTML through the
Django test client. Folder-count workloads include one child folder and one file
per displayed folder. Page size is 100. Session storage is cache-backed.

Permission workloads distinguish a grant at every level from one grant at the
root. Both start with a cold permission cache. Empty-result workloads prime an
empty cached result before measuring repeated checks. Fixture creation and cache
preparation are outside timings. Each case rolls back its database transaction.

Duplicate workloads consume every returned queryset, so both eager and lazy
implementations perform the same requested work. Mostly-unique cases contain one
two-file duplicate group and unique digests for all remaining files. Aggregation
still scans/groups database values; this benchmark does not establish index or
production-database performance.

SQL and model-instantiation counts are recorded in a separate untimed invocation.
Output fingerprints are also computed outside timings. HTML normalization replaces
only randomized CSRF tokens; fixture timestamps are fixed. All other HTML and all
returned IDs must match across revisions. Object counts are not peak memory.

These are local, single-process measurements. They exclude network, browser,
concurrency, production database latency, real image subclasses, and storage I/O.
Single-root traversal issues one query per level, including the leaf lookup, plus
the permission query; 100 folders require 101 queries. Overlapping grants can
still finish in two queries when all folders are roots and fit in one batch.

## Recorded results

Baseline `a011dbd5` versus `c7a0b2b2`, Python 3.13.16 / Django 6.0.9.
All 21 output fingerprints match across the six processes. See `results.json`
for raw samples, environment versions, and object counts.

| Workload | Size | Before (ms) | After (ms) | Speedup | SQL queries |
|---|---:|---:|---:|---:|---:|
| Rendered file listing, page 1 | 100 | 38.24 | 36.58 | 1.05× | 4 → 5 |
| Rendered file listing, page 1 | 1,000 | 73.10 | 36.57 | 2.00× | 4 → 5 |
| Rendered file listing, page 1 | 10,000 | 402.70 | 38.66 | 10.4× | 4 → 5 |
| Rendered file search, page 1 | 100 | 35.33 | 37.11 | 0.95× | 4 → 5 |
| Rendered file search, page 1 | 1,000 | 67.95 | 36.77 | 1.85× | 4 → 5 |
| Rendered file search, page 1 | 10,000 | 379.72 | 38.14 | 10.0× | 4 → 5 |
| Rendered folder counts | 25 | 21.18 | 14.85 | 1.43× | 54 → 5 |
| Rendered folder counts | 100 | 54.22 | 28.76 | 1.88× | 204 → 5 |
| Overlapping grants at every level, cold | 25 | 49.47 | 0.47 | 106.3× | 351 → 2 |
| Overlapping grants at every level, cold | 50 | 188.14 | 0.51 | 369.1× | 1,326 → 2 |
| Overlapping grants at every level, cold | 100 | 737.20 | 0.63 | 1169.3× | 5,151 → 2 |
| Single root grant, cold | 25 | 4.04 | 2.58 | 1.56× | 27 → 26 |
| Single root grant, cold | 50 | 7.57 | 4.91 | 1.54× | 52 → 51 |
| Single root grant, cold | 100 | 14.80 | 9.13 | 1.62× | 102 → 101 |
| Repeated empty permission checks | 100 | 27.06 | 28.29 | 0.96× | 100 → 100 |
| Repeated empty permission checks | 1,000 | 271.72 | 283.27 | 0.96× | 1,000 → 1,000 |
| Duplicate group, one shared SHA1, consumed | 100 | 82.41 | 1.07 | 76.8× | 101 → 2 |
| Duplicate group, one shared SHA1, consumed | 200 | 298.94 | 1.73 | 172.5× | 201 → 2 |
| Duplicate group, one shared SHA1, consumed | 400 | 1177.28 | 3.34 | 352.7× | 401 → 2 |
| Mostly unique SHA1s, one two-file group, consumed | 100 | 14.70 | 0.34 | 43.6× | 101 → 2 |
| Mostly unique SHA1s, one two-file group, consumed | 400 | 63.19 | 0.45 | 139.9× | 401 → 2 |

## Tree and search workloads

`tree_scaling.py` measures folder-tree and search paths with the same method:
three fresh processes per revision, alternating order, two warmups and five
timed samples each, medians of all 15 samples. Run it like `query_scaling.py`,
with `--source`, `--revision`, and `--output`.

Trees have one root, `size` children, and one grandchild per child. Where noted,
each grandchild holds one file. Permission workloads run as a staff user with a
subtree grant and a cold permission cache. Search workloads use page size 100.

| Workload | What runs |
|---|---|
| descendant ids | `Folder.get_descendants_ids()` on the root |
| limited search | Rendered search limited to the root, with files |
| edit check | `check_folder_edit_permissions` on the root, with files |
| destinations | Copy/move destination choices for the staff user |
| delete confirmation | Rendered delete confirmation for the root, with files |
| move listing | Copy/move confirmation list for the root, with files |
| search files | Rendered search over `size` files as the staff user |
| pick search folders | Rendered pick-folder popup search over `size` folders |

## Recorded tree results

Baseline `b53e7c03` versus `6bbfdb04`, Python 3.12.0 / Django 5.2.18.
All 16 output fingerprints match across the six processes. See
`tree_results.json` for raw samples and environment versions.

| Workload | Size | Before (ms) | After (ms) | Speedup | SQL queries |
|---|---:|---:|---:|---:|---:|
| descendant ids | 50 | 12.74 | 0.42 | 30.3× | 101 → 3 |
| descendant ids | 200 | 50.37 | 0.88 | 57.5× | 401 → 3 |
| limited search | 50 | 46.57 | 34.00 | 1.4× | 107 → 9 |
| limited search | 200 | 82.52 | 31.56 | 2.6× | 406 → 8 |
| edit check | 50 | 30.60 | 4.84 | 6.3× | 209 → 13 |
| edit check | 200 | 119.32 | 15.36 | 7.8× | 809 → 13 |
| destinations | 50 | 18.33 | 5.35 | 3.4× | 113 → 15 |
| destinations | 200 | 70.74 | 17.76 | 4.0× | 413 → 15 |
| delete confirmation | 50 | 55.59 | 24.56 | 2.3× | 273 → 27 |
| delete confirmation | 200 | 187.16 | 61.63 | 3.0× | 1,023 → 27 |
| move listing | 50 | 33.20 | 6.77 | 4.9× | 204 → 8 |
| move listing | 200 | 130.39 | 23.27 | 5.6× | 804 → 8 |
| search files | 25 | 22.03 | 19.47 | 1.1× | 35 → 10 |
| search files | 100 | 49.98 | 38.32 | 1.3× | 110 → 10 |
| pick search folders | 25 | 21.46 | 14.12 | 1.5× | 82 → 10 |
| pick search folders | 100 | 60.43 | 29.34 | 2.1× | 307 → 10 |
