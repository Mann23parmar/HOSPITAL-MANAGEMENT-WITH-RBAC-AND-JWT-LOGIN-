from pydantic import BaseModel, Field, StrictStr
from app.schemas.update_payload import UpdatePayload


class PrescriptionCreate(BaseModel):

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

    medical_record_id: StrictStr = Field(
        ...,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$",
        examples=["66f456789012abcdef456789"]
    )

    medicine_id: StrictStr = Field(
        ...,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$",
        examples=["66f789012345abcdef789012"]
    )

    quantity: int = Field(
        ...,
        gt=0,
        examples=[5]
    )

    dosage: StrictStr = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["500 mg"]
    )

    frequency: StrictStr = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Twice a day"]
    )

    duration: StrictStr = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["5 days"]
    )

    instructions: StrictStr = Field(
        ...,
        min_length=2,
        max_length=300,
        examples=["Take after meals"]
    )


class PrescriptionUpdate(UpdatePayload):

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

    medical_record_id: StrictStr | None = Field(
        default=None,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$"
    )

    medicine_id: StrictStr | None = Field(
        default=None,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$"
    )

    dosage: StrictStr | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    frequency: StrictStr | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    duration: StrictStr | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    instructions: StrictStr | None = Field(
        default=None,
        min_length=2,
        max_length=300
    )
