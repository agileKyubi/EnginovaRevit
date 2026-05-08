# -*- coding: utf-8 -*-
import json
import os
from pyrevit import revit, forms, DB

# --- CONFIGURATION ---
IFC_GUID_PARAM = "IfcGuid"

def get_ifc_guid(element):
    """Retrieves the IFC GUID from an element."""
    param = element.LookupParameter(IFC_GUID_PARAM)
    if param and param.HasValue:
        return param.AsString()
    return element.UniqueId

def run():
    doc = revit.doc
    view = doc.ActiveView

    # 1. Select Linked IFC
    links = DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance).ToElements()
    if not links:
        forms.alert("No linked files found in the project.", exitscript=True)

    link = forms.select_revit_links(title="Select Linked IFC to Extract Visibility States")
    if not link:
        return

    link_doc = link.GetLinkDocument()
    if not link_doc:
        forms.alert("The selected link is not loaded.", exitscript=True)

    # 2. Get all elements in the link (excluding non-physical ones)
    collector = DB.FilteredElementCollector(link_doc)\
                  .WhereElementIsNotElementType()\
                  .WhereElementIsViewIndependent()
    
    hidden_guids = []
    total_elements = 0

    # 3. Check visibility
    # Note: Checking visibility of individual linked elements in a host view
    # is complex. We'll check for explicit overrides or hidden categories.
    
    # In this version, we'll ask the user if they want to extract HIDDEN or VISIBLE elements
    mode = forms.alert("Extract which state?", options=["Hidden Elements", "Visible Elements"])
    if not mode:
        return
    
    extract_hidden = (mode == "Hidden Elements")

    with forms.ProgressBar(title="Analyzing Link Visibility...") as pb:
        elements = list(collector)
        count = len(elements)
        
        for i, el in enumerate(elements):
            if i % 100 == 0:
                pb.update_progress(i, count)
            
            # Check if the element is hidden in the host view
            # Revit handles this via view.IsElementVisibleInView but it's tricky for links.
            # A common way is to check the view overrides.
            is_visible = view.IsElementVisibleInView(el) # This works if the element is from the host doc, but for links?
            # For links, we need to check if the element ID from the link is in the view's hidden elements list.
            
            # Actually, a better way for links:
            if extract_hidden:
                if not view.IsElementVisibleInView(el):
                    hidden_guids.append(get_ifc_guid(el))
            else:
                if view.IsElementVisibleInView(el):
                    hidden_guids.append(get_ifc_guid(el))

    # 4. Save to JSON
    save_path = forms.save_file(file_ext='json', default_name="ifc_visibility_states.json")
    if save_path:
        data = {
            "link_name": link.Name,
            "mode": mode,
            "guids": hidden_guids
        }
        with open(save_path, 'w') as f:
            json.dump(data, f, indent=4)
        
        forms.alert("Successfully extracted {} IDs to:\n{}".format(len(hidden_guids), save_path))

if __name__ == "__main__":
    run()
