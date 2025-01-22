from pydantic import BaseModel, Field, model_validator
from typing import List

from .user import UserModel

from utility.states import card_types


class ChannelModel(BaseModel):
    channel_url: str
    header: str = Field(alias="name")
    title: str = Field(alias="name")
    chatroom_image_url: str = Field(alias="cover_url")
    created_at: int
    is_secret: bool = False
    members: List[UserModel] = []
    uuids: list = []
    members_can_message: bool = True
    type: int = card_types.CARD_NORMAL

    @classmethod
    @model_validator(mode="before")
    def _validate_members(cls, data):
        if data.get("is_public") is None:
            data["members"] = data.get("participants")

        return data

    @classmethod
    @model_validator(mode="before")
    def _validate_is_secret(cls, data):
        data["is_secret"] = not data.get("is_public", True)
        return data

    @classmethod
    @model_validator(mode="before")
    def _validate_members_can_message(cls, data):
        data["members_can_message"] = not data.get("freeze", False)
        return data

    @model_validator(mode="after")
    def _fill_uuids(self):
        if self.members:

            for user_data in self.members:
                self.uuids.append(user_data.uuid)

        self.uuids = list(set(self.uuids))

        return self


class Channels(BaseModel):
    channels: List[ChannelModel]
