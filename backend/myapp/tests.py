from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from pytesseract.pytesseract import TesseractNotFoundError
from rest_framework.test import APIClient

from .ocr import extract_aadhaar_details


class AadhaarApiTests(TestCase):
    def test_create_record_with_all_fields_empty(self):
        response = APIClient().post(
            reverse("save_aadhaar"),
            {
                "name": "",
                "dob": "",
                "gender": "",
                "address": "",
                "pincode": "",
            },
            format="json"
        )

        self.assertEqual(response.status_code, 201)
        record = APIClient().get(reverse("aadhaar_list")).data[0]
        self.assertEqual(record["name"], "")
        self.assertIsNone(record["dob"])
        self.assertEqual(record["gender"], "")
        self.assertEqual(record["address"], "")
        self.assertEqual(record["pincode"], "")

    def test_extracts_name_without_name_label_and_multiline_address(self):
        details = extract_aadhaar_details(
            "Government of India\n"
            "Ravi Kumar\n"
            "DOB: 02/01/1990\n"
            "MALE\n"
            "Address:\n"
            "S/O Ramesh Kumar,\n"
            "12 Main Road, Chennai - 600001\n"
            "VID: 1234"
        )

        self.assertEqual(details["name"], "Ravi Kumar")
        self.assertEqual(
            details["address"],
            "S/O Ramesh Kumar, 12 Main Road, Chennai - 600001"
        )

    @patch("myapp.views.read_document", side_effect=TesseractNotFoundError())
    def test_ocr_reports_missing_tesseract(self, _read_document):
        response = APIClient().post(
            reverse("aadhaar_ocr"),
            {
                "file": SimpleUploadedFile(
                    "card.jpg",
                    b"\xff\xd8\xfftest",
                    content_type="image/jpeg"
                )
            },
            format="multipart"
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("Tesseract OCR is not installed", response.data["error"])

    def test_create_list_update_and_delete_aadhaar_record(self):
        client = APIClient()
        details = {
            "name": "Test Person",
            "dob": "1990-01-02",
            "gender": "Other",
            "address": "Test address",
            "pincode": "600001",
        }

        created = client.post(
            reverse("save_aadhaar"),
            details,
            format="json"
        )
        self.assertEqual(created.status_code, 201)

        record_id = created.data["id"]
        listed = client.get(reverse("aadhaar_list"))
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data[0]["id"], record_id)

        updated = client.patch(
            reverse("aadhaar_detail", args=[record_id]),
            {"address": "Updated address"},
            format="json"
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["address"], "Updated address")

        deleted = client.delete(
            reverse("aadhaar_detail", args=[record_id])
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(client.get(reverse("aadhaar_list")).data, [])
