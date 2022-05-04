#!/bin/bash
FILE_FILTER=$1
TESTS_FILTER="$2"
UPDATE_REFS=${3:-No}

python3.9 ../jobs_launcher/executeTests.py --test_filter $TESTS_FILTER --file_filter $FILE_FILTER --tests_root ../jobs --work_root ../Work/Results --work_dir Anari --cmd_variables Tool "../Anari/anariRenderTests" ResPath "." UpdateRefs $UPDATE_REFS

