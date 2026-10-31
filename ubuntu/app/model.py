from typing import Literal

from pydantic import BaseModel, Field


class MoveRequest(BaseModel):
    direction: Literal["forward", "backward", "left", "right"]
    speed: int = Field(ge=0, le=100)


class TaskRequest(BaseModel):
    task: Literal["forward", "backward", "left", "right", "square"]

