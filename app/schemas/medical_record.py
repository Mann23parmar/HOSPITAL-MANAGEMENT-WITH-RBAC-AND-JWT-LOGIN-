from pydantic import BaseModel, Field, StrictStr
from app.schemas.update_payload import UpdatePayload


class MedicalRecordCreate(BaseModel):

    patient_id: StrictStr = Field(
        ...,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$",
        examples=["66f123456789abcdef123456"]
    )

    doctor_id: StrictStr = Field(
        ...,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$",
        examples=["66f987654321abcdef654321"]
    )

    appointment_id: StrictStr = Field(
        ...,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$",
        examples=["66f456789012abcdef456789"]
    )

    diagnosis: StrictStr = Field(
        ...,
        min_length=2,
        max_length=300,
        examples=["Mild hypertension"]
    )

    treatment: StrictStr = Field(
        ...,
        min_length=2,
        max_length=500,
        examples=["Medication and regular blood pressure monitoring"]
    )

    notes: StrictStr = Field(
        ...,
        min_length=2,
        max_length=500,
        examples=["Follow-up after two weeks"]
    )


class MedicalRecordUpdate(UpdatePayload):

    patient_id: StrictStr | None = Field(
        default=None,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$"
    )

    doctor_id: StrictStr | None = Field(
        default=None,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$"
    )

    appointment_id: StrictStr | None = Field(
        default=None,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$"
    )

    diagnosis: StrictStr | None = Field(
        default=None,
        min_length=2,
        max_length=300
    )

    treatment: StrictStr | None = Field(
        default=None,
        min_length=2,
        max_length=500
    )

    notes: StrictStr | None = Field(
        default=None,
        min_length=2,
        max_length=500
    )
