"""Response models for handling time endpoints."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HandlingTimeResponse(BaseModel):
    """Response model for handling time endpoint."""

    is_error: bool = Field(
        False,
        alias="isError",
        description="Indicates if there was an error",
    )
    messages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of messages",
    )
    default_handling_time: int = Field(
        ...,
        alias="defaultHandlingTime",
        description="Default handling time in days",
    )
    max_handling_time: int = Field(
        ...,
        alias="maxHandlingTime",
        description="Maximum handling time in days",
    )
    min_handling_time: int = Field(
        ...,
        alias="minHandlingTime",
        description="Minimum handling time in days",
    )

    model_config = ConfigDict(populate_by_name=True)
