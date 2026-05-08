# -*- coding: utf-8 -*-
import csv
import os
from pyrevit import revit, forms, DB

# This script exports Revit Text Notes to a CSV format compatible with the PDF extractor tool.

def run():
    doc = revit.doc
    active_view = doc.ActiveView

    # 1. Select Text Notes
    # We can either take all in view or ask the user to pick
    notes = DB.FilteredElementCollector(doc, active_view.Id)\
              .OfClass(DB.TextNote)\
              .ToElements()

    if not notes:
        forms.alert("No Text Notes found in the current view.", exitscript=True)

    # 2. UI: Pick reference point (Anchor A / Grid 1)
    try:
        origin_point = revit.pick_point("Select the reference point (e.g. Grid 1) for coordinate export")
    except Exception:
        forms.alert("Operation cancelled.", exitscript=True)

    # 3. UI: Select Save Location
    csv_path = forms.save_file(file_ext='csv', default_name="exported_labels.csv")
    if not csv_path:
        return

    # 4. Export Data
    data = []
    for note in notes:
        # Get coordinates (TextNote.Coord is the insertion point)
        pos = note.Coord
        
        # Calculate relative coordinates (in Feet)
        rel_x = pos.X - origin_point.X
        rel_y = pos.Y - origin_point.Y
        
        data.append({
            "Room_Name": note.Text,
            "X_Relative": rel_x,
            "Y_Relative": rel_y,
            "Scale_Factor": 1.0  # Already in Revit Feet
        })

    # 5. Write to CSV
    try:
        with open(csv_path, 'wb') as f:
            writer = csv.DictWriter(f, fieldnames=["Room_Name", "X_Relative", "Y_Relative", "Scale_Factor"])
            writer.writeheader()
            writer.writerows(data)
        
        forms.alert("Successfully exported {} labels to:\n{}".format(len(data), csv_path), title="Export Complete")
    except Exception as e:
        forms.alert("Failed to write CSV:\n" + str(e))

if __name__ == "__main__":
    run()
