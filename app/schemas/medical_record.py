from pydantic import BaseModel, Field


# This schema is for creating a medical record
class MedicalRecordCreate(BaseModel):

    patient_id: str = Field(
        ...,
        min_length=24,
        max_length=24,
        description="MongoDB patient ID",
        examples=["6ab4bf465142012b9d33db70"]
    )

    doctor: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Doctor name",
        examples=["Dr. Patel"]
    )

    diagnosis: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Patient diagnosis",
        examples=["Fever"]
    )

    treatment: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Treatment given to the patient",
        examples=["Paracetamol and rest"]
    )

    notes: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Additional medical notes",
        examples=["Follow-up after 3 days"]
    )


# This schema is for updating a medical record
class MedicalRecordUpdate(BaseModel):

    patient_id: str = Field(
        ...,
        min_length=24,
        max_length=24,
        description="MongoDB patient ID",
        examples=["6ab4bf465142012b9d33db70"]
    )

    doctor: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Dr. Patel"]
    )

    diagnosis: str = Field(
        ...,
        min_length=2,
        max_length=200,
        examples=["Fever"]
    )

    treatment: str = Field(
        ...,
        min_length=2,
        max_length=500,
        examples=["Paracetamol and rest"]
    )

    notes: str = Field(
        ...,
        min_length=2,
        max_length=500,
        examples=["Follow-up after 3 days"]
    )