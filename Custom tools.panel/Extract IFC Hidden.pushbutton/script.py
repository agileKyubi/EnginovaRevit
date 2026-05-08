# -*- coding: utf-8 -*-
# Extract_Hidden_Automated.py
from pyrevit import revit, forms, script
import json
from Autodesk.Revit.DB import *

doc = revit.doc
active_view = doc.ActiveView

def get_centroid(bbox):
    if not bbox:
        return None
    return XYZ((bbox.Min.X + bbox.Max.X)/2, 
               (bbox.Min.Y + bbox.Max.Y)/2, 
               (bbox.Min.Z + bbox.Max.Z)/2)

# 1. Find all linked IFC/Revit documents
link_instances = FilteredElementCollector(doc).OfClass(RevitLinkInstance).ToElements()
if not link_instances:
    forms.alert("No linked models found in this project.")
    script.exit()

# If multiple links, let the user select which one to analyze or analyze all?
# The user said "without the user needing to select it" which could mean the link too.
# But usually you want to target a specific IFC revision. 
# I'll analyze all links but keep them separate or merge them.
# Given the "Apply" script usually targets one link, I'll prompt for the link selection 
# but automate the element detection inside it.

if len(link_instances) > 1:
    target_link = forms.select_revit_links(title="Select the linked model to extract hidden elements from")
else:
    target_link = link_instances[0]

if not target_link:
    script.exit()

link_doc = target_link.GetLinkDocument()
if not link_doc:
    forms.alert("The selected link is not loaded.")
    script.exit()

transform = target_link.GetTotalTransform()

hidden_centroids = []

# 2. Automated Detection of Hidden Elements
# We check the Link Overrides first (fastest)
# Then fallback to a Deep Scan if needed.

hidden_ids = []
overrides = active_view.GetLinkOverrides(target_link.Id)
if overrides:
    hidden_ids = list(overrides.GetHiddenElementIds())

if not hidden_ids:
    # Deep Scan Fallback
    # Collect all physical, view-independent elements in the link
    with forms.ProgressBar(title="Deep Scanning for Hidden Elements (Any Category)...") as pb:
        all_linked = FilteredElementCollector(link_doc)\
                        .WhereElementIsNotElementType()\
                        .WhereElementIsViewIndependent()\
                        .ToElements()
        
        count = len(all_linked)
        for i, el in enumerate(all_linked):
            if i % 500 == 0:
                pb.update_progress(i, count)
            
            # Use IsHidden check - this works for individually hidden elements
            try:
                if el.IsHidden(active_view):
                    hidden_ids.append(el.Id)
            except:
                # If IsHidden fails, we could try IsElementVisibleInView
                # but that's often less accurate for "individually hidden"
                pass

if hidden_ids:
    for eid in hidden_ids:
        el = link_doc.GetElement(eid)
        if not el:
            continue
            
        # WORK WITH ANY OBJECT (No category filter)
        bbox = el.get_BoundingBox(None)
        centroid = get_centroid(bbox)
        
        if centroid:
            host_centroid = transform.OfPoint(centroid)
            hidden_centroids.append({
                "id": el.Id.IntegerValue,
                "category": el.Category.Name if el.Category else "Unknown",
                "x": host_centroid.X,
                "y": host_centroid.Y,
                "z": host_centroid.Z
            })

# 3. Save to JSON
if hidden_centroids:
    file_path = forms.save_file(file_ext='json', default_name='Hidden_Elements_Map.json')
    if file_path:
        with open(file_path, 'w') as f:
            json.dump(hidden_centroids, f, indent=4)
        forms.alert("Successfully extracted {} hidden element locations (All Categories).".format(len(hidden_centroids)))
else:
    forms.alert("No hidden elements were detected in the selected link.")