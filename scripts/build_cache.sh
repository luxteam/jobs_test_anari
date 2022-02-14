#!/bin/bash
TOOL=$1
LIBRARY="$2"

python3.9 build_cache.py --tool $TOOL --library $LIBRARY