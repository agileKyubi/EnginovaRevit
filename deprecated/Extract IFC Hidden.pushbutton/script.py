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




# 2. Interactive Detection (Category-Agnostic)
# Due to Revit API limitations in older versions, automated detection of individually 
# hidden linked elements is impossible (GetLinkOverrides returns None, and IsHidden fails across links).
# We must use interactive selection in 'Reveal Hidden Elements' mode.

uidoc = revit.uidoc

forms.alert("Automated detection of hidden linked elements is not supported in this Revit version's API.\n\n"
            "Instructions:\n"
            "1. Ensure 'Reveal Hidden Elements' (the lightbulb) is turned ON.\n"
            "2. Click OK, then window-select the pink hidden elements in the linked IFC.\n"
            "3. Click 'Finish' on the top-left Options Bar.", title="Extract Hidden Elements")

try:
    # ObjectType.LinkedElement allows selecting nested elements inside the link
    from Autodesk.Revit.UI.Selection import ObjectType
    refs = uidoc.Selection.PickObjects(ObjectType.LinkedElement, "Select the hidden elements, then click Finish")
except:
    script.exit() # Exits cleanly if user hits ESC or Cancel

hidden_centroids = []

# 3. Process the selected linked elements (ANY object)
with forms.ProgressBar(title="Processing Selected Elements...") as pb:
    count = len(refs)
    for i, ref in enumerate(refs):
        pb.update_progress(i, count)
        
        # Get the link instance to get its coordinate transform
        link_instance = doc.GetElement(ref.ElementId)
        if isinstance(link_instance, RevitLinkInstance):
            link_doc = link_instance.GetLinkDocument()
            transform = link_instance.GetTotalTransform()
            
            # Get the actual nested element inside the IFC link
            linked_element = link_doc.GetElement(ref.LinkedElementId)
            
            if linked_element:
                bbox = linked_element.get_BoundingBox(None)
                centroid = get_centroid(bbox)
                
                if centroid:
                    # Transform the coordinates back to host world space
                    host_centroid = transform.OfPoint(centroid)
                    hidden_centroids.append({
                        "id": linked_element.Id.IntegerValue,
                        "category": linked_element.Category.Name if linked_element.Category else "Unknown",
                        "x": host_centroid.X,
                        "y": host_centroid.Y,
                        "z": host_centroid.Z
                    })

# 4. Save to JSON
if hidden_centroids:
    file_path = forms.save_file(file_ext='json', default_name='Hidden_Elements_Map.json')
    if file_path:
        with open(file_path, 'w') as f:
            json.dump(hidden_centroids, f, indent=4)
        forms.alert("Successfully extracted {} hidden element locations (All Categories).".format(len(hidden_centroids)))
else:
    forms.alert("No elements were successfully processed from your selection.")