"""Build private wheels that use the existing contrib OpenCV distribution.

Only dependency metadata is changed. Package code and version are unchanged;
the explicit 1hysim wheel build tag and provenance report identify these builds.
"""
import base64
import csv
from email.parser import BytesParser
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name, parse_wheel_filename


def digest(data):
    return hashlib.sha256(data).hexdigest()


def patch_wheel(source, destination):
    with zipfile.ZipFile(source) as archive:
        files = {name: archive.read(name) for name in archive.namelist()
                 if not name.endswith("/")}
    metadata_path = next(name for name in files if name.endswith(".dist-info/METADATA"))
    metadata = BytesParser().parsebytes(files[metadata_path])
    requirements = metadata.get_all("Requires-Dist", [])
    changed = []
    replacements = []
    for value in requirements:
        requirement = Requirement(value)
        if canonicalize_name(requirement.name) in {"opencv-python", "opencv-python-headless"}:
            replacement = value.replace(requirement.name, "opencv-contrib-python", 1)
            changed.append({"original": value, "replacement": replacement})
            replacements.append(replacement)
        else:
            replacements.append(value)
    if not changed:
        return None
    del metadata["Requires-Dist"]
    for value in replacements:
        metadata["Requires-Dist"] = value
    files[metadata_path] = metadata.as_bytes()
    wheel_path = metadata_path.rsplit("/", 1)[0] + "/WHEEL"
    wheel_metadata = BytesParser().parsebytes(files[wheel_path])
    if "Build" in wheel_metadata:
        del wheel_metadata["Build"]
    wheel_metadata["Build"] = "1hysim"
    files[wheel_path] = wheel_metadata.as_bytes()
    record_path = metadata_path.rsplit("/", 1)[0] + "/RECORD"
    record = io.StringIO(newline="")
    writer = csv.writer(record, lineterminator="\n")
    for name, data in sorted(files.items()):
        if name == record_path:
            continue
        value = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        writer.writerow([name, "sha256=" + value, len(data)])
    writer.writerow([record_path, "", ""])
    files[record_path] = record.getvalue().encode("utf-8")
    # All inputs here are untagged upstream wheels produced by pip wheel.
    parts = source.stem.split("-")
    if len(parts) != 5:
        raise ValueError(f"Unexpected upstream wheel build tag: {source.name}")
    target = destination / ("-".join(parts[:2] + ["1hysim"] + parts[2:]) + ".whl")
    parse_wheel_filename(target.name)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    return {"package": metadata["Name"], "version": metadata["Version"],
            "upstream_wheel": source.name, "upstream_sha256": digest(source.read_bytes()),
            "private_wheel": target.name, "private_sha256": digest(target.read_bytes()),
            "dependency_changes": changed, "package_code_changed": False}


def main():
    source, destination, report = map(Path, sys.argv[1:])
    destination.mkdir(parents=True, exist_ok=True)
    records = [record for path in sorted(source.glob("*.whl"))
               if (record := patch_wheel(path, destination)) is not None]
    expected = {"pixeloe", "transparent-background", "albumentations", "albucore"}
    actual = {canonicalize_name(record["package"]) for record in records}
    if actual != expected:
        raise RuntimeError(f"Unexpected OpenCV metadata inputs: {actual}")
    report.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Normalized {len(records)} private wheels to the existing OpenCV contrib package.")


if __name__ == "__main__":
    main()
