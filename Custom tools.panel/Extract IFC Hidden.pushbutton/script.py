# -*- coding: utf-8 -*-
# Extract_Hidden_All_Views.py
from pyrevit import revit, forms, script, output
import json
from Autodesk.Revit.DB import *

doc = revit.doc
active_view = revit.active_view
def get_centroid(bbox):
    if not bbox:
        return None
    return XYZ((bbox.Min.X + bbox.Max.X)/2, 
               (bbox.Min.Y + bbox.Max.Y)/2, 
               (bbox.Min.Z + bbox.Max.Z)/2)

# 1. Collect all linked models
link_instances = FilteredElementCollector(doc).OfClass(RevitLinkInstance).ToElements()
if not link_instances:
    forms.alert("No linked models found.")
    script.exit()

loaded_links = [l for l in link_instances if l.GetLinkDocument()]
if not loaded_links:
    forms.alert("No loaded linked models found.")
    script.exit()

if len(loaded_links) > 1:
    target_link = forms.select_revit_links(title="Select the linked model to analyze")
else:
    target_link = loaded_links[0]

if not target_link:
    script.exit()

link_doc = target_link.GetLinkDocument()
transform = target_link.GetTotalTransform()

# 2. Collect Relevant Views
all_views = FilteredElementCollector(doc).OfClass(View).ToElements()
valid_types = [ViewType.FloorPlan, ViewType.ThreeD, ViewType.Section, ViewType.Elevation, ViewType.CeilingPlan]
relevant_views = [v for v in all_views if not v.IsTemplate and v.ViewType in valid_types]

hidden_ids = set()
hidden_centroids = []

print("Scanning {} views for hidden elements in link: {}...".format(len(relevant_views), target_link.Name))




# 3. Deep Automated Detection across ALL Views
# We collect all physical elements once
all_elements = FilteredElementCollector(link_doc)\
                .WhereElementIsNotElementType()\
                .WhereElementIsViewIndependent()\
                .ToElements()

with forms.ProgressBar(title="Deep Scanning All Views...") as pb:
    view_count = len(relevant_views)
    for i, view in enumerate(relevant_views):
        pb.update_progress(i, view_count)
        
        for el in all_elements:
            if el.Id not in hidden_ids:
                # 'view.IsElementHidden' does not exist in this Revit API version.
                # The correct method is 'element.IsHidden(view)'.
                # Letting errors surface for debugging as requested.
                if el.IsHidden(view):
                    hidden_ids.add(el.Id)

# 4. Process the unique hidden IDs
for eid in hidden_ids:
    el = link_doc.GetElement(eid)
    if not el:
        continue
        
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

# 5. Save to JSON
if hidden_centroids:
    file_path = forms.save_file(file_ext='json', default_name='Hidden_Elements_Map.json')
    if file_path:
        with open(file_path, 'w') as f:
            json.dump(hidden_centroids, f, indent=4)
        forms.alert("Successfully extracted {} hidden element locations from {} views.".format(len(hidden_centroids), len(relevant_views)))
else:
    forms.alert("No hidden elements were detected across all scanned views.")