set PATH=c:\python39\;c:\python39\scripts\;%PATH%
set LIBRARY="%1"

python -m pip install -r ../jobs_launcher/install/requirements.txt

python build_cache.py --tool "..\Anari\anari_regression_tests.exe" --library %LIBRARY%