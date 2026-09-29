from pydantic import BaseModel, Field


class MedicalRecordCreate(BaseModel):

    patient_id: str = Field(
        ...,
        min_length=24,
        max_length=24,
        examples=["66f123456789abcdef123456"]
    )

    doctor_id: str = Field(
        ...,
        min_length=24,
        max_length=24,
        examples=["66f987654321abcdef654321"]
    )

    appointment_id: str = Field(
        ...,
        min_length=24,
        max_length=24,
        examples=["66f456789012abcdef456789"]
    )

    diagnosis: str = Field(
        ...,
        min_length=2,
        max_length=300,
        examples=["Mild hypertension"]
    )

    treatment: str = Field(
        ...,
        min_length=2,
        max_length=500,
        examples=["Medication and regular blood pressure monitoring"]
    )

    notes: str = Field(
        ...,
        min_length=2,
        max_length=500,
        examples=["Follow-up after two weeks"]
    )


class MedicalRecordUpdate(BaseModel):

    patient_id: str = Field(
        ...,
        min_length=24,
        max_length=24
    )

    doctor_id: str = Field(
        ...,
        min_length=24,
        max_length=24
    )

    appointment_id: str = Field(
        ...,
        min_length=24,
        max_length=24
    )

    diagnosis: str = Field(
        ...,
        min_length=2,
        max_length=300
    )

    treatment: str = Field(
        ...,
        min_length=2,
        max_length=500
    )

    notes: str = Field(
        ...,
        min_length=2,
        max_length=500
    )