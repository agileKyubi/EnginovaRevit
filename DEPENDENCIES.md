# Project Dependencies

This project relies on two distinct environments to function:

## 1. pyRevit Environment
Most scripts run within the **pyRevit** (IronPython) environment inside Autodesk Revit.
- **pyRevit**: [v4.8.14+](https://github.com/eirannejad/pyRevit)
- **Autodesk Revit**: 2020 or newer recommended.

## 2. Python 3 External Environment
The PDF extraction logic (`logic.py`) requires a standard Python 3 installation to handle modern PDF parsing libraries.
- **Python**: 3.7 or newer.
- **PyMuPDF (fitz)**: Used for high-performance PDF text extraction.

### Installing Python 3 Dependencies
Run the following command in your terminal:
```bash
pip install -r requirements.txt
```

---

## Component Breakdown
| Tool | Environment | Main Dependencies |
| :--- | :--- | :--- |
| **Export PDF Labels** | pyRevit (Subprocess) | Python 3, PyMuPDF |
| **Import Labels** | pyRevit | Revit API, pyRevit UI |
| **Export Labels to CSV** | pyRevit | Revit API |
