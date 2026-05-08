# -*- coding: utf-8 -*-
# Extract hidden elements from IFC

from pyrevit import revit, forms
from pyrevit import script
import json
import os
from Autodesk.Revit.DB import *

doc = revit.doc
active_view = doc.ActiveView

def get_centroid(bbox):
    if not bbox:
        return None
    return XYZ((bbox.Min.X + bbox.Max.X)/2, 
               (bbox.Min.Y + bbox.Max.Y)/2, 
               (bbox.Min.Z + bbox.Max.Z)/2)

# 1. Find the linked IFC document
link_instances = FilteredElementCollector(doc).OfClass(RevitLinkInstance).ToElements()
if not link_instances:
    forms.alert("No linked models found in this project.")
    script.exit()

# Assuming the first link is the target, or prompt user if multiple
if len(link_instances) > 1:
    target_link = forms.select_revit_links(title="Select the linked IFC")
else:
    target_link = link_instances[0]

if not target_link:
    script.exit()

link_doc = target_link.GetLinkDocument()
if not link_doc:
    forms.alert("The selected link is not loaded.")
    script.exit()

transform = target_link.GetTotalTransform()

# 2. Get the Visibility Overrides for this link in the active view
# This is the correct way to find elements hidden individually in a link
hidden_centroids = []

try:
    overrides = active_view.GetLinkOverrides(target_link.Id)
    if not overrides:
        forms.alert("No overrides found for this link in the current view.")
        script.exit()
    
    hidden_ids = overrides.GetHiddenElementIds()
    
    if not hidden_ids:
        forms.alert("No individually hidden elements found in the selected link.")
        script.exit()

    # 3. Process hidden elements
    for eid in hidden_ids:
        el = link_doc.GetElement(eid)
        if not el:
            continue
            
        # Optional: Filter by category if needed (e.g. only Generic Models)
        # if el.Category.Id.IntegerValue != int(BuiltInCategory.OST_GenericModel):
        #     continue

        bbox = el.get_BoundingBox(None)
        centroid = get_centroid(bbox)
        if centroid:
            # Transform to host coordinates
            host_centroid = transform.OfPoint(centroid)
            hidden_centroids.append({
                "id": el.Id.IntegerValue,
                "category": el.Category.Name if el.Category else "Unknown",
                "x": host_centroid.X,
                "y": host_centroid.Y,
                "z": host_centroid.Z
            })

except Exception as e:
    forms.alert("Failed to extract hidden elements. Your Revit version may not support this method, or the link is not overridden.\n\nError: {}".format(e))
    script.exit()

# 4. Save to JSON
file_path = forms.save_file(file_ext='json', default_name='Hidden_Elements_Map.json')
if file_path:
    with open(file_path, 'w') as f:
        json.dump(hidden_centroids, f, indent=4)
    forms.alert("Successfully extracted {} hidden element locations.".format(len(hidden_centroids)))