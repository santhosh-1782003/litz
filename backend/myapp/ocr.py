import pytesseract
import cv2
import numpy as np
import os
import re
import shutil

from PIL import Image
from io import BytesIO
from pdf2image import convert_from_bytes
from datetime import datetime
from pathlib import Path


tesseract_cmd = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract")
if not tesseract_cmd:
    tesseract_locations = (
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        / "Tesseract-OCR"
        / "tesseract.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "Tesseract-OCR"
        / "tesseract.exe",
    )
    tesseract_cmd = next(
        (str(path) for path in tesseract_locations if path.is_file()),
        None
    )

if tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


# Image preprocessing
def preprocess_image(image):

    # Convert image into RGB
    image = image.convert("RGB")

    # Convert PIL image into NumPy array
    image_array = np.array(image)

    # Convert RGB to grayscale
    gray = cv2.cvtColor(
        image_array,
        cv2.COLOR_RGB2GRAY
    )

    # Increase image size
    gray = cv2.resize(
        gray,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC
    )

    # Improve image quality
    _, processed = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return processed


# Read uploaded document
def read_document(uploaded_file):

    file_data = uploaded_file.read()

    images = []

    if uploaded_file.name.lower().endswith(".pdf"):

        images = convert_from_bytes(
            file_data,
            first_page=1,
            last_page=2,
            dpi=250
        )

    else:

        image = Image.open(
            BytesIO(file_data)
        )

        images = [image]

    extracted_text = ""

    for image in images:

        processed_image = preprocess_image(image)

        text = pytesseract.image_to_string(
            processed_image,
            config="--psm 6"
        )

        extracted_text += text + "\n"

    return extracted_text


# Extract required Aadhaar details
def extract_aadhaar_details(text):

    details = {

        "name": "",
        "dob": "",
        "gender": "",
        "address": "",
        "pincode": ""

    }

    # Extract date of birth
    dob_pattern = (
        r'(?:DOB|Date of Birth|Birth|D\.O\.B)'
        r'\s*[:\-]?\s*'
        r'(\d{2}[/-]\d{2}[/-]\d{4})'
    )

    dob_match = re.search(
        dob_pattern,
        text,
        re.IGNORECASE
    )

    if dob_match:

        try:

            dob = dob_match.group(1).replace("-", "/")

            details["dob"] = datetime.strptime(
                dob,
                "%d/%m/%Y"
            ).strftime("%Y-%m-%d")

        except ValueError:
            pass


    # Extract gender
    gender_match = re.search(
        r'\b(MALE|FEMALE|TRANSGENDER)\b',
        text,
        re.IGNORECASE
    )

    if gender_match:

        gender = gender_match.group(1).upper()

        if gender == "MALE":
            details["gender"] = "Male"

        elif gender == "FEMALE":
            details["gender"] = "Female"

        else:
            details["gender"] = "Other"


    # Extract PIN code
    pincode_match = re.search(
        r'\b[1-9][0-9]{5}\b',
        text
    )

    if pincode_match:

        details["pincode"] = pincode_match.group(0)


    # Extract name using a label when present
    name_match = re.search(
        r'\bName\b\s*[:\-]?\s*([^\r\n]+)',
        text,
        re.IGNORECASE
    )

    if name_match:

        name = re.split(
            r'\b(?:DOB|Date of Birth|Year of Birth|Gender)\b',
            name_match.group(1),
            maxsplit=1,
            flags=re.IGNORECASE
        )[0].strip(" \t:,-")

        if name:
            details["name"] = name

    # Aadhaar front sides often show the name without a "Name" label.
    if not details["name"]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        metadata_pattern = re.compile(
            r'\b(?:DOB|Date of Birth|Year of Birth|Gender|MALE|FEMALE|'
            r'TRANSGENDER)\b',
            re.IGNORECASE
        )
        excluded_name_pattern = re.compile(
            r'\b(?:government|india|aadhaar|aadhar|identification|'
            r'authority|enrolment|enrollment|unique|dob|gender)\b',
            re.IGNORECASE
        )

        for index, line in enumerate(lines):
            if not metadata_pattern.search(line):
                continue

            for candidate in reversed(lines[max(0, index - 3):index]):
                candidate = candidate.strip(" \t:,-")
                if (
                    candidate
                    and any(character.isalpha() for character in candidate)
                    and not any(character.isdigit() for character in candidate)
                    and not excluded_name_pattern.search(candidate)
                ):
                    details["name"] = candidate
                    break

            if details["name"]:
                break


    # Extract address
    address_match = re.search(
        r'Address\s*[:\-]?\s*(.*?)(?=\n\s*(?:VID|Mobile|'
        r'Government|Unique Identification|Aadhaar\s*(?:No|Number))|$)',
        text,
        re.IGNORECASE | re.DOTALL
    )

    if address_match:

        address = address_match.group(1)

        # Remove possible Aadhaar number
        address = re.sub(
            r'\b\d{4}\s?\d{4}\s?\d{4}\b',
            '',
            address
        )

        details["address"] = " ".join(
            address.split()
        )[:1000]

    return details