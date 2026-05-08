# -*- coding: utf-8 -*-
import json
from pyrevit import revit, forms, DB

# --- CONFIGURATION ---
IFC_GUID_PARAM = "IfcGuid"

def run():
    doc = revit.doc
    view = doc.ActiveView

    # 1. Load JSON
    json_path = forms.pick_file(file_ext='json', title="Select IFC Visibility JSON")
    if not json_path:
        return

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        forms.alert("Failed to load JSON:\n" + str(e), exitscript=True)

    target_guids = set(data.get("guids", []))
    if not target_guids:
        forms.alert("No IDs found in the JSON file.", exitscript=True)

    # 2. Select Target Link
    links = DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance).ToElements()
    if not links:
        forms.alert("No linked files found.", exitscript=True)

    link = forms.select_revit_links(title="Select Target Link to Apply Visibility")
    if not link:
        return

    link_doc = link.GetLinkDocument()
    if not link_doc:
        forms.alert("Selected link is not loaded.", exitscript=True)

    # 3. Find elements in the link that match the GUIDs
    collector = DB.FilteredElementCollector(link_doc)\
                  .WhereElementIsNotElementType()\
                  .WhereElementIsViewIndependent()
    
    ids_to_hide = []
    
    with forms.ProgressBar(title="Matching Elements...") as pb:
        elements = list(collector)
        count = len(elements)
        for i, el in enumerate(elements):
            if i % 100 == 0:
                pb.update_progress(i, count)
            
            # Check IfcGuid or UniqueId
            guid = None
            param = el.LookupParameter(IFC_GUID_PARAM)
            if param and param.HasValue:
                guid = param.AsString()
            else:
                guid = el.UniqueId
            
            if guid in target_guids:
                ids_to_hide.append(el.Id)

    if not ids_to_hide:
        forms.alert("No matching elements found in the target link.", exitscript=True)

    # 4. Apply Visibility
    # Note: Hiding elements from a link in a host view is tricky via the API.
    # We will try to hide them. If the standard HideElements fails, 
    # we might need to use a different strategy.
    
    with revit.Transaction("Apply IFC Visibility Filtering"):
        try:
            # We need to hide the elements. In Revit API, hiding linked elements
            # is done by passing the ElementId from the link document? 
            # No, that usually doesn't work.
            # However, in some versions/contexts, you can use:
            # view.HideElements(ids_to_hide)
            
            # Fallback: We'll try to hide them and catch errors.
            success_count = 0
            fail_count = 0
            
            # Standard HideElements often fails for links.
            # A more reliable way is to use the ElementId from the link?
            # Actually, the only way to hide linked elements individually 
            # is to use a filter OR hide them in the linked view.
            
            # Let's try the direct approach first.
            from System.Collections.Generic import List
            id_list = List[DB.ElementId]()
            for eid in ids_to_hide:
                id_list.Add(eid)
            
            try:
                view.HideElements(id_list)
                success_count = len(ids_to_hide)
            except:
                # If direct hide fails, it's likely because they are linked.
                forms.alert("Direct hiding of linked elements is not supported in this Revit version/view.\n"
                            "Consider using a Filter or Linked View override.", title="API Limitation")
                return

            forms.alert("Successfully hidden {} elements in the current view.".format(success_count))
            
        except Exception as e:
            forms.alert("Error applying visibility:\n" + str(e))

if __name__ == "__main__":
    run()
