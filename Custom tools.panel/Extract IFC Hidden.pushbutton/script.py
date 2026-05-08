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
hidden_centroids = []
hidden_ids = []

print("Analyzing visibility for link: {}".format(target_link.Name))

try:
    overrides = active_view.GetLinkOverrides(target_link.Id)
    if overrides:
        hidden_ids = list(overrides.GetHiddenElementIds())
        print("Found {} hidden elements via Link Overrides.".format(len(hidden_ids)))
    else:
        print("GetLinkOverrides returned None. Attempting Deep Scan fallback...")
except Exception as e:
    print("Link Overrides API not available or failed: {}. Attempting Deep Scan...".format(e))

# 3. Fallback: If no hidden IDs found via overrides, try a Deep Scan
# This checks visibility of every element in the link (slower but more resilient)
if not hidden_ids:
    with forms.ProgressBar(title="Deep Scanning Link Visibility...") as pb:
        # Collect all physical elements in the link
        all_linked = FilteredElementCollector(link_doc)\
                        .WhereElementIsNotElementType()\
                        .WhereElementIsViewIndependent()\
                        .ToElements()
        
        count = len(all_linked)
        for i, el in enumerate(all_linked):
            if i % 200 == 0:
                pb.update_progress(i, count)
            
            # Check if element is hidden in the active view
            # Note: el.IsHidden(view) is the most reliable check for individual 'Hide in View'
            try:
                if el.IsHidden(active_view):
                    hidden_ids.append(el.Id)
            except:
                # Fallback to general visibility check if IsHidden fails
                try:
                    if not active_view.IsElementVisibleInView(el):
                        hidden_ids.append(el.Id)
                except:
                    pass

if not hidden_ids:
    forms.alert("No individually hidden elements were detected in this link.\n\n"
                "If you have hidden elements, ensure they were hidden using 'Hide in View > Elements' "
                "in the current active view.")
    script.exit()

# 4. Process the identified hidden elements
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