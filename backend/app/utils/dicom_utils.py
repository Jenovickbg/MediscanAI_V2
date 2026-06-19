from pathlib import Path


def is_dicom_file(filename: str) -> bool:
    lower = filename.lower()
    return lower.endswith(".dcm") or lower.endswith(".dicom") or "." not in Path(filename).name
