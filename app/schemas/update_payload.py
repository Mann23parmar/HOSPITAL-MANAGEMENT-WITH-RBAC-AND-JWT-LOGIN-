from typing import Any

from pydantic import BaseModel, model_validator


class UpdatePayload(BaseModel):
    """Base for partial updates that allow omission but not explicit nulls."""

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_nulls(cls, values: Any) -> Any:
        if isinstance(values, dict):
            null_fields = [name for name, value in values.items() if value is None]
            if null_fields:
                fields = ", ".join(null_fields)
                raise ValueError(f"Fields cannot be null: {fields}")
        return values
