"""Input validation utilities for rental agent."""

import re
from functools import wraps


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def validate_license_number(license_number: str) -> None:
    """Validate business license number format."""
    if not license_number:
        raise ValidationError("License number cannot be empty")

    if len(license_number) < 5:
        raise ValidationError("License number must be at least 5 characters")

    if len(license_number) > 50:
        raise ValidationError("License number is too long (max 50 characters)")

    # Basic alphanumeric check
    if not re.match(r'^[A-Za-z0-9\-]+$', license_number):
        raise ValidationError("License number contains invalid characters")


def validate_equipment_id(equipment_id: str) -> None:
    """Validate equipment ID format."""
    if not equipment_id:
        raise ValidationError("Equipment ID cannot be empty")

    if len(equipment_id) > 20:
        raise ValidationError("Equipment ID is too long (max 20 characters)")

    # Check format (e.g., ITM001, EQ001)
    if not re.match(r'^[A-Z]{2,4}\d{3,6}$', equipment_id):
        raise ValidationError("Equipment ID must follow format: 2-4 letters followed by 3-6 digits")


def validate_address(address: str) -> None:
    """Validate address format."""
    if not address:
        raise ValidationError("Address cannot be empty")

    if len(address) < 10:
        raise ValidationError("Address seems too short (minimum 10 characters)")

    if len(address) > 200:
        raise ValidationError("Address is too long (max 200 characters)")


def validate_price(price: float, min_value: float = 0, max_value: float = 100000) -> None:
    """Validate price values."""
    if not isinstance(price, (int, float)):
        raise ValidationError("Price must be a number")

    if price < min_value:
        raise ValidationError(f"Price cannot be less than ${min_value}")

    if price > max_value:
        raise ValidationError(f"Price cannot exceed ${max_value}")


def validate_rental_days(days: int) -> None:
    """Validate rental duration."""
    if not isinstance(days, int):
        raise ValidationError("Rental days must be an integer")

    if days < 1:
        raise ValidationError("Rental duration must be at least 1 day")

    if days > 365:
        raise ValidationError("Rental duration cannot exceed 365 days")


def validate_operator_name(name: str) -> None:
    """Validate operator name."""
    if not name:
        raise ValidationError("Operator name cannot be empty")

    if len(name) < 2:
        raise ValidationError("Operator name is too short")

    if len(name) > 100:
        raise ValidationError("Operator name is too long (max 100 characters)")

    # Allow letters, spaces, hyphens, apostrophes
    if not re.match(r"^[A-Za-z\s\-']+$", name):
        raise ValidationError("Operator name contains invalid characters")


def validate_phone_number(phone: str) -> None:
    """Validate phone number format."""
    if not phone:
        raise ValidationError("Phone number cannot be empty")

    # Remove common formatting characters
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)

    if not cleaned.isdigit():
        raise ValidationError("Phone number must contain only digits and formatting characters")

    if len(cleaned) < 10:
        raise ValidationError("Phone number is too short")

    if len(cleaned) > 15:
        raise ValidationError("Phone number is too long")


def validate_policy_number(policy_number: str) -> None:
    """Validate insurance policy number."""
    if not policy_number:
        raise ValidationError("Policy number cannot be empty")

    if len(policy_number) < 5:
        raise ValidationError("Policy number is too short")

    if len(policy_number) > 50:
        raise ValidationError("Policy number is too long (max 50 characters)")

    # Alphanumeric with some special characters
    if not re.match(r'^[A-Za-z0-9\-]+$', policy_number):
        raise ValidationError("Policy number contains invalid characters")
