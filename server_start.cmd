if "%HOST%"=="" set HOST=0.0.0.0
if "%PORT%"=="" set PORT=8000
uvicorn src.api:app --host %HOST% --port %PORT% --reload --reload-dir src