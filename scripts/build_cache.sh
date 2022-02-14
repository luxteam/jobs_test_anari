#!/bin/bash
LIBRARY="$2"

python3.9 build_cache.py --tool "../Anari/anari_regression_tests" --library $LIBRARY