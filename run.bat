@echo off
REM Change to the script directory
cd /d "C:\Python\Hubspot-DSV-List"

REM Activate the virtual environment
call "C:\Python\Hubspot-DSV-List\.venv\Scripts\activate.bat"

REM Run the Python script
python "C:\Python\Hubspot-DSV-List\main.py"

REM Pause to see the output
REM pause