set PATH=c:\python39\;c:\python39\scripts\;%PATH%
set TOOL=%1
set LIBRARY="%2"

python -m pip install -r ../jobs_launcher/install/requirements.txt

python build_cache.py --tool %TOOL% --library %LIBRARY%