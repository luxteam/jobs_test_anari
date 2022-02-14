#!/bin/bash
LIBRARY="$1"

python3.9 build_cache.py --tool "../Anari/anari_regression_tests" --library $LIBRARY