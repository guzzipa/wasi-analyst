# src/wasi_analyst/ui/launch.py
from pathlib import Path
import os

def main():
    # app.py vive junto a este archivo
    script = Path(__file__).with_name("app.py")
    # reemplaza el proceso actual por `streamlit run app.py`
    os.execvp("streamlit", ["streamlit", "run", str(script)])

