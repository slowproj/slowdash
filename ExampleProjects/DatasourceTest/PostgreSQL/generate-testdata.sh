#! /bin/bash

slowdash_dir="$(dirname $(dirname $(command -v slowdash)))"
python3 $slowdash_dir/utils/generate-testdata.py --db-url=postgresql://slowdash:slowdash@localhost:5432/SlowTestData
