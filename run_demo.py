import subprocess
import sys
import os

# ------------------------
# Set paths
# ------------------------
BASE_DIR = r"C:\Users\Administrator\Documents\Grenada_Flood_AI_Demo"
SCRIPT_PATH = os.path.join(BASE_DIR, "flood_ai_local.py")

# ------------------------
# Activate virtual environment and run script
# ------------------------
# For Windows
VENV_PYTHON = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")

if not os.path.exists(VENV_PYTHON):
    raise FileNotFoundError(f"Python executable not found in venv: {VENV_PYTHON}")

print("Running the flood AI")

