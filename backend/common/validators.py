from django.core.validators import RegexValidator

phone_validator = RegexValidator(
    regex=r"^\+?[0-9]{7,15}$",
    message="Enter a valid phone number: digits only, optional leading +, 7 to 15 digits.",
)
