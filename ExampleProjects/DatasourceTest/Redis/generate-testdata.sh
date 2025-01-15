#! /bin/bash

slowdash_dir="$(dirname $(dirname $(command -v slowdash)))"
python3 $slowdash_dir/utils/generate-testdata.py --db-url=redis://localhost:6379/12
