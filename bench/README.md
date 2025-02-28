# Wn Benchmarking

This directory contains code and data for running benchmarks for
Wn. The benchmarks are implemented using
[pytest-benchmarks](https://github.com/ionelmc/pytest-benchmark/), so
they are run using pytest as follows (from the top-level project
directory):

```console
$ hatch test bench/  # run the benchmarks
$ hatch test bench/ --benchmark-autosave  # run benchmarks and store results
$ hatch test bench/ --benchmark-compare  # run benchmarks and compare to stored result
$ hatch test -- --help  # get help on options (look for those prefixed `--benchmark-`)
```

Notes:

* The tests are not exhaustive; when making a change that may affect
  performance, consider making a new test if one doesn't exist
  already. It would be helpful to check in the test to Git, but not
  the benchmark results since those are dependent on the machine.
* Benchmark the code before and after the changes. Store the results
  locally for comparison.
* Ensure the testing environment has a steady load (wait for
  long-running processes to finish, close any active web browser tabs,
  etc.) prior to and while running the test.
* Expect high variance for IO-bound tasks.

