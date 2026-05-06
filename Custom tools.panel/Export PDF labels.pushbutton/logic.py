# -*- coding: utf-8 -*-
import fitz  # PyMuPDF
import json
import math
import sys
import os

def clean_text(text):
    # Replaces common PDF ligatures with standard characters
    if not text:
        return ""
    return text.replace(u'\ufb01', 'fi').replace(u'\ufb02', 'fl')

def extract(pdf_path, grid_dist_mm, filter_keywords, grid_a_label, grid_b_label):
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        text_instances = page.get_text("dict")["blocks"]

        # 1. Find Anchors
        anchors = {}
        for block in text_instances:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    txt = clean_text(span["text"].strip().upper())
                    if txt in [grid_a_label, grid_b_label]:
                        bbox = span["bbox"]
                        anchors[txt] = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)

        if len(anchors) < 2:
            return {"error": "Could not find grid anchors '{}' and '{}' on the first page.".format(grid_a_label, grid_b_label)}

        # 2. Calibrate Scale
        p1, p2 = anchors[grid_a_label], anchors[grid_b_label]
        pixel_dist = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
        mm_per_pt = grid_dist_mm / pixel_dist
        
        # 3. Extract Rooms
        rooms = []
        anchor_a = anchors[grid_a_label]
        for block in text_instances:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    text = clean_text(span["text"].strip())
                    if any(k in text.upper() for k in filter_keywords):
                        bbox = span["bbox"]
                        # Relative to Anchor A, Y flipped for Revit
                        rel_x = ((bbox[0] + bbox[2]) / 2) - anchor_a[0]
                        rel_y = anchor_a[1] - ((bbox[1] + bbox[3]) / 2)
                        
                        rooms.append({
                            "Room_Name": text,
                            "X_Relative": rel_x,
                            "Y_Relative": rel_y,
                            "Scale_Factor": mm_per_pt * 0.00328084
                        })
        
        return {"success": True, "rooms": rooms}

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Expecting: pdf_path, grid_dist, labels_json, gridA, gridB
    if len(sys.argv) < 6:
        print(json.dumps({"error": "Insufficient arguments"}))
        sys.exit(1)

    pdf_path = sys.argv[1]
    grid_dist = float(sys.argv[2])
    filter_keywords = json.loads(sys.argv[3])
    grid_a = sys.argv[4]
    grid_b = sys.argv[5]

    result = extract(pdf_path, grid_dist, filter_keywords, grid_a, grid_b)
    print(json.dumps(result))
