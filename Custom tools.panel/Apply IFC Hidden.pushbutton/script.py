# Apply IFC Hidden property into new IFC revision

from pyrevit import revit, forms
from pyrevit import script
import json
import math
from Autodesk.Revit.DB import *

doc = revit.doc
active_view = doc.ActiveView

# Convert 50mm tolerance to Decimal Feet for the Revit API
TOLERANCE_FEET = 50 / 304.8

def get_centroid(bbox):
    if not bbox:
        return None
    return XYZ((bbox.Min.X + bbox.Max.X)/2, 
               (bbox.Min.Y + bbox.Max.Y)/2, 
               (bbox.Min.Z + bbox.Max.Z)/2)

def distance(pt1, pt2):
    return math.sqrt((pt1.X - pt2.X)**2 + (pt1.Y - pt2.Y)**2 + (pt1.Z - pt2.Z)**2)

# 1. Load the JSON mapping
file_path = forms.pick_file(file_ext='json')
if not file_path:
    script.exit()

with open(file_path, 'r') as f:
    hidden_data = json.load(f)

# 2. Find the linked IFC document
link_instances = FilteredElementCollector(doc).OfClass(RevitLinkInstance).ToElements()
if not link_instances:
    forms.alert("No linked models found.")
    script.exit()

if len(link_instances) > 1:
    target_link = forms.select_revit_links(title="Select the target linked IFC")
else:
    target_link = link_instances[0]

if not target_link:
    script.exit()

link_doc = target_link.GetLinkDocument()
transform = target_link.GetTotalTransform()

# 3. Collect ALL physical elements in the NEW link (Work with ANY object)
linked_elements = FilteredElementCollector(link_doc)\
                    .WhereElementIsNotElementType()\
                    .WhereElementIsViewIndependent()\
                    .ToElements()

elements_to_hide = []

# 4. Compare spatial coordinates
with forms.ProgressBar(title="Matching geometric locations...") as pb:
    count = len(linked_elements)
    for i, el in enumerate(linked_elements):
        if i % 100 == 0:
            pb.update_progress(i, count)
            
        bbox = el.get_BoundingBox(None)
        centroid = get_centroid(bbox)
        
        if centroid:
            host_centroid = transform.OfPoint(centroid)
            
            # Check if this centroid is near any of our saved coordinates
            for saved_pt in hidden_data:
                target_xyz = XYZ(saved_pt['x'], saved_pt['y'], saved_pt['z'])
                if distance(host_centroid, target_xyz) <= TOLERANCE_FEET:
                    elements_to_hide.append(el.Id)
                    break 

# 5. Hide the elements in the active view using Link Overrides
if elements_to_hide:
    from System.Collections.Generic import List
    
    t = Transaction(doc, "Apply Geometric Hide")
    t.Start()
    
    try:
        # The most robust way to hide linked elements (Revit 2022+)
        overrides = active_view.GetLinkOverrides(target_link.Id)
        if not overrides:
            overrides = RevitLinkGraphicsSettings()
        
        # Get existing hidden IDs and merge with new ones
        hidden_set = set(overrides.GetHiddenElementIds())
        for eid in elements_to_hide:
            hidden_set.add(eid)
            
        id_list = List[ElementId]()
        for eid in hidden_set:
            id_list.Add(eid)
            
        overrides.SetHiddenElementIds(id_list)
        active_view.SetLinkOverrides(target_link.Id, overrides)
        
        t.Commit()
        forms.alert("Successfully hid {} elements based on spatial coordinates.".format(len(elements_to_hide)))
    except Exception as e:
        t.RollBack()
        forms.alert("Failed to apply visibility overrides.\n\nError: {}".format(e))
else:
    forms.alert("No matching elements found in the new link within the tolerance.")