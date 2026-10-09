from pydantic import (
    BaseModel,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator
)
from app.schemas.update_payload import UpdatePayload
import re



# Reusable validation functions


def validate_blood_pressure(value):
    if value is None:
        return value

    if not re.fullmatch(r"\d{2,3}/\d{2,3}", value):
        raise ValueError(
            "Blood pressure must be in format like 120/80"
        )

    systolic, diastolic = map(int, value.split("/"))

    if systolic <= diastolic:
        raise ValueError(
            "Systolic blood pressure must be greater than diastolic blood pressure"
        )

    if not 50 <= systolic <= 250:
        raise ValueError(
            "Systolic blood pressure must be between 50 and 250"
        )

    if not 30 <= diastolic <= 150:
        raise ValueError(
            "Diastolic blood pressure must be between 30 and 150"
        )

    return value


def validate_temperature(value):
    if value is None:
        return value

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(
            "Temperature must be a valid number"
        )

    return value


def validate_pulse_rate(value):
    if value is None:
        return value

    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(
            "Pulse rate must be a valid integer"
        )

    return value


def validate_weight(value):
    if value is None:
        return value

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(
            "Weight must be a valid number"
        )

    return value


# =========================================================
# CREATE
# =========================================================

class PatientVitalsCreate(BaseModel):

    patient_id: StrictStr = Field(
        ...,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$",
        examples=["66f123456789abcdef123456"]
    )

    nurse_id: StrictStr = Field(
        ...,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$",
        examples=["66f987654321abcdef654321"]
    )

    blood_pressure: StrictStr = Field(
        ...,
        examples=["120/80"]
    )

    temperature: StrictFloat = Field(
        ...,
        gt=0,
        examples=[98.6]
    )

    pulse_rate: StrictInt = Field(
        ...,
        gt=0,
        examples=[72]
    )

    weight: StrictFloat = Field(
        ...,
        gt=0,
        examples=[65.5]
    )

    @field_validator("blood_pressure")
    @classmethod
    def validate_create_blood_pressure(cls, value):
        return validate_blood_pressure(value)

    @field_validator("temperature", mode="before")
    @classmethod
    def validate_create_temperature(cls, value):
        return validate_temperature(value)

    @field_validator("pulse_rate", mode="before")
    @classmethod
    def validate_create_pulse_rate(cls, value):
        return validate_pulse_rate(value)

    @field_validator("weight", mode="before")
    @classmethod
    def validate_create_weight(cls, value):
        return validate_weight(value)


# =========================================================
# UPDATE
# =========================================================

class PatientVitalsUpdate(UpdatePayload):

    patient_id: StrictStr | None = Field(
        default=None,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$"
    )

    nurse_id: StrictStr | None = Field(
        default=None,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$"
    )

    blood_pressure: StrictStr | None = Field(
        default=None,
        examples=["120/80"]
    )

    temperature: StrictFloat | None = Field(
        default=None,
        gt=0
    )

    pulse_rate: StrictInt | None = Field(
        default=None,
        gt=0
    )

    weight: StrictFloat | None = Field(
        default=None,
        gt=0
    )

    @field_validator("blood_pressure")
    @classmethod
    def validate_update_blood_pressure(cls, value):
        return validate_blood_pressure(value)

    @field_validator("temperature", mode="before")
    @classmethod
    def validate_update_temperature(cls, value):
        return validate_temperature(value)

    @field_validator("pulse_rate", mode="before")
    @classmethod
    def validate_update_pulse_rate(cls, value):
        return validate_pulse_rate(value)

    @field_validator("weight", mode="before")
    @classmethod
    def validate_update_weight(cls, value):
        return validate_weight(value)
