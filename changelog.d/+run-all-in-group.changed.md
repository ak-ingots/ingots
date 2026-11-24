`run_group()` of the operations and their runner is `run_all_in_group()`
now, beside `run_each_in_group()`: it runs a group as a whole, the caller
checked for every operation before any runs, the failures raised
together. Breaking: a call of `run_group()` moves to `run_all_in_group()`.
