from django.urls import path
from . import views

urlpatterns = [
    path('aadhaar-ocr/', views.aadhaar_ocr, name='aadhaar_ocr'),
    path('save-aadhaar/', views.save_aadhaar, name='save_aadhaar'),
    path('aadhaar/', views.aadhaar_list, name='aadhaar_list'),
    path('aadhaar/<int:pk>/', views.aadhaar_detail, name='aadhaar_detail'),
]