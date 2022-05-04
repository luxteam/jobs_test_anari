#!/bin/bash
LIBRARY="$1"

python3.9 build_cache.py --tool "../Anari/anariRenderTests" --library $LIBRARY