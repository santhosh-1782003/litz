from rest_framework import serializers
from .models import AadhaarDetails
from datetime import date
import re


class OptionalDateField(serializers.DateField):
    def to_internal_value(self, value):
        if value == "":
            return None
        return super().to_internal_value(value)


class AadhaarSerializer(serializers.ModelSerializer):
    dob = OptionalDateField(required=False, allow_null=True)

    class Meta:
        model = AadhaarDetails
        fields = [
            'id',
            'name',
            'dob',
            'gender',
            'address',
            'pincode',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate_name(self, value):
        return value.strip()

    def validate_dob(self, value):

        if value and value > date.today():
            raise serializers.ValidationError(
                "Date of birth cannot be in the future"
            )

        return value

    def validate_gender(self, value):

        if not value:
            return value

        if value not in ['Male', 'Female', 'Other']:
            raise serializers.ValidationError(
                "Invalid gender"
            )

        return value

    def validate_pincode(self, value):

        if not value:
            return value

        if not re.fullmatch(r'[1-9][0-9]{5}', value):
            raise serializers.ValidationError(
                "Enter valid 6 digit PIN code"
            )

        return value