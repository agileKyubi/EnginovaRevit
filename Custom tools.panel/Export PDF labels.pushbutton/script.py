# -*- coding: utf-8 -*-
import os
import subprocess
import json
import csv
import sys
from pyrevit import forms, script

reload(sys)
sys.setdefaultencoding('utf-8')

# --- CONFIGURATION ---
# Path to your Python 3 executable (must have 'pymupdf' installed)
PYTHON_EXE = r"C:\Users\n4107\AppData\Local\Microsoft\WindowsApps\python.exe"

# Use shell=True if paths have spaces, and set the environment to use UTF-8
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

LABEL_SETS = {
    "APARTMENT": ["BED", "LIVING", "KITCHEN", "ENS", "BATH", "STUDY", "ENTRY", "DINING", "WIR", "MPR", "SCULLERY", "PTY", "PDR", "BT", "GARAGE", "ELEC", "STAIRS", "LIFT", "PRIMARY", "CARPARK", "LDY"],
    "SCHOOL": ["GYM", "ADMIN", "OFFICE"]
}



def run():
    # 1. UI: Pick PDF File
    pdf_path = forms.pick_file(file_ext='pdf', title="Select PDF for Label Extraction")
    if not pdf_path:
        return

    # 2. UI: Ask for Grid Distance
    grid_dist_str = forms.ask_for_string(default="3600", prompt="Enter Grid A to B distance (mm):")
    if not grid_dist_str:
        return

    # 3. UI: Select Label Set
    selected_set_name = forms.ask_for_one_item(sorted(LABEL_SETS.keys()), default="APARTMENT")
    if not selected_set_name:
        return

    # 4. UI: Anchor Labels
    grid_a = forms.ask_for_string(default="1", prompt="Anchor A Label:")
    grid_b = forms.ask_for_string(default="2", prompt="Anchor B Label:")
    if not grid_a or not grid_b:
        return

    # 5. Execute logic.py via Subprocess
    # We pass arguments: pdf_path, dist, labels_json, gridA, gridB
    logic_script = os.path.join(os.path.dirname(__file__), "logic.py")
    labels_json = json.dumps(LABEL_SETS[selected_set_name])
    
    process = subprocess.Popen(
        [PYTHON_EXE, logic_script, pdf_path, grid_dist_str, labels_json, grid_a, grid_b],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=env
    )
    stdout, stderr = process.communicate()
    # 6. Process Result
    try:
        output = json.loads(stdout)
        if "success" in output:
            rooms = output["rooms"]
            # Save to CSV (placed next to PDF)
            csv_path = pdf_path.replace(".pdf", "_extracted.csv")
            
            # IronPython csv write
            with open(csv_path, 'wb') as f:
                writer = csv.DictWriter(f, fieldnames=["Room_Name", "X_Relative", "Y_Relative", "Scale_Factor"])
                writer.writeheader()
                writer.writerows(rooms)
            
            forms.alert("Successfully extracted {} rooms!\n\nSaved to: {}".format(len(rooms), csv_path), title="Success")
        else:
            forms.alert("Logic Error: " + output.get("error", "Unknown error"))
    except Exception as e:
        forms.alert("Subprocess Failed:\n" + stderr + "\n\nSystem Error: " + str(e))

if __name__ == "__main__":
    run()
