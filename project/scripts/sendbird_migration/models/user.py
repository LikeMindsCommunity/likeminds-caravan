from pydantic import BaseModel, Field, model_validator
from utility.time_utilities import TimeUtilities
from typing import List

class UserModel(BaseModel):
    uuid: str = Field(alias="user_id")
    user_name: str = Field(alias="nickname")
    image_url: str = Field(alias="profile_url")
    image: str = None
    created_at: int = TimeUtilities.current_time_in_sec()

    @classmethod
    @model_validator(mode="before")
    def _validate_image_url(cls, data):
        image_url = data.get("image_url") or data["image"] or data["profile_url"]
        data["image_url"] = image_url
        data["image"] = image_url

        return data


class Users(BaseModel):
    users: List[UserModel]