import logging

from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework.decorators import (
    api_view,
    permission_classes,
    parser_classes
)

from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser

from rest_framework.response import Response
from rest_framework import status
from pdf2image.exceptions import PDFInfoNotInstalledError, PopplerNotInstalledError
from pytesseract.pytesseract import TesseractNotFoundError

from .models import AadhaarDetails
from .serializers import AadhaarSerializer
from .ocr import read_document, extract_aadhaar_details

logger = logging.getLogger(__name__)


# Check uploaded file
def validate_file(file):

    if file.size > 5 * 1024 * 1024:

        return False, "File size must be below 5 MB"

    extension = file.name.lower().split(".")[-1]

    if extension not in ["jpg", "jpeg", "png", "pdf"]:

        return False, "Only JPG, JPEG, PNG and PDF allowed"

    header = file.read(8)

    file.seek(0)

    if extension in ["jpg", "jpeg"]:

        valid = header.startswith(b"\xff\xd8\xff")

    elif extension == "png":

        valid = header.startswith(b"\x89PNG\r\n\x1a\n")

    else:

        valid = header.startswith(b"%PDF-")

    if not valid:

        return False, "Invalid file format"

    return True, ""


# API 1: OCR processing
@api_view(["POST"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def aadhaar_ocr(request):

    uploaded_file = request.FILES.get("file")

    if not uploaded_file:

        return Response(
            {"error": "Please upload a document"},
            status=status.HTTP_400_BAD_REQUEST
        )

    valid, message = validate_file(uploaded_file)

    if not valid:

        return Response(
            {"error": message},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:

        # Read document using OCR
        extracted_text = read_document(uploaded_file)

        # Extract required details
        details = extract_aadhaar_details(
            extracted_text
        )

        if not any(details.values()):

            return Response(
                {
                    "error": "Unable to read document. Upload a clear image."
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        return Response(
            {
                "message": "OCR completed successfully",
                "data": details
            },
            status=status.HTTP_200_OK
        )

    except TesseractNotFoundError:
        logger.exception("Tesseract OCR executable is unavailable")
        return Response(
            {
                "error": (
                    "Tesseract OCR is not installed or configured. Install "
                    "Tesseract and add it to PATH, or set TESSERACT_CMD to "
                    "the full path of tesseract.exe, then restart the backend."
                )
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    except (PDFInfoNotInstalledError, PopplerNotInstalledError):
        logger.exception("Poppler is unavailable for PDF OCR")
        return Response(
            {
                "error": (
                    "Poppler is required to read PDF documents. Install "
                    "Poppler and add its bin folder to PATH, then restart "
                    "the backend."
                )
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    except Exception:
        logger.exception("Unexpected OCR processing failure")

        return Response(
            {
                "error": "OCR processing failed. Please try another document."
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# API 2: Save verified information
@api_view(["POST"])
@permission_classes([AllowAny])
def save_aadhaar(request):

    serializer = AadhaarSerializer(
        data=request.data
    )

    if serializer.is_valid():

        data = serializer.validated_data

        # Check possible duplicate
        duplicate = False
        if data.get("name") and data.get("dob") and data.get("pincode"):
            duplicate = AadhaarDetails.objects.filter(
                name__iexact=data["name"],
                dob=data["dob"],
                pincode=data["pincode"]
            ).exists()

        if duplicate:

            return Response(
                {
                    "error": "This record may already exist"
                },
                status=status.HTTP_409_CONFLICT
            )

        with transaction.atomic():

            record = serializer.save()

        return Response(
            {
                "message": "Aadhaar details saved successfully",
                "id": record.id
            },
            status=status.HTTP_201_CREATED
        )

    return Response(
        {
            "error": "Invalid form data",
            "details": serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def aadhaar_list(request):

    records = AadhaarDetails.objects.all().order_by("-created_at")
    serializer = AadhaarSerializer(records, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def aadhaar_detail(request, pk):

    record = get_object_or_404(AadhaarDetails, pk=pk)

    if request.method == "DELETE":
        record.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if request.method == "GET":
        return Response(AadhaarSerializer(record).data)

    serializer = AadhaarSerializer(
        record,
        data=request.data,
        partial=request.method == "PATCH"
    )

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(
        {
            "error": "Invalid form data",
            "details": serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )