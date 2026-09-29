from pydantic import BaseModel, Field


class PrescriptionCreate(BaseModel):

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

    medical_record_id: str = Field(
        ...,
        min_length=24,
        max_length=24,
        examples=["66f456789012abcdef456789"]
    )

    medicine_id: str = Field(
        ...,
        min_length=24,
        max_length=24,
        examples=["66f789012345abcdef789012"]
    )

    dosage: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["500 mg"]
    )

    frequency: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Twice a day"]
    )

    duration: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["5 days"]
    )

    instructions: str = Field(
        ...,
        min_length=2,
        max_length=300,
        examples=["Take after meals"]
    )


class PrescriptionUpdate(BaseModel):

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

    medical_record_id: str = Field(
        ...,
        min_length=24,
        max_length=24
    )

    medicine_id: str = Field(
        ...,
        min_length=24,
        max_length=24
    )

    dosage: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    frequency: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    duration: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    instructions: str = Field(
        ...,
        min_length=2,
        max_length=300
    )