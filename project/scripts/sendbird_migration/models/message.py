from typing import List
from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError

from user import UserModel
from channels import ChannelModel

from utility.time_utilities import TimeUtilities
from utility.states import conversation_states, card_types

class MessageModel(BaseModel):
    message_id: int
    answer: str = Field(alias="message")
    state: int = 0
    created_at: int
    user: UserModel
    is_deleted: bool = Field(alias="is_removed")

    @staticmethod
    def _validate_state(data):
        # Validate the state
        conversation_states_dict = {"MESG": conversation_states.ANSWER}

        if not (data.get("type") and data.get("type") in conversation_states_dict):
            raise PydanticCustomError("invalid_message_type", "Invalid message type.")

        data["state"] = conversation_states_dict[data.get("type")]
        return data

    @classmethod
    @model_validator(mode="before")
    def _validate(cls, data):
        data = cls._validate_state(data)

        return data
