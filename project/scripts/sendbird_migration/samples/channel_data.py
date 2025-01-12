open_channel_sample = {
    "channel_url": "only needed in migration for mapping | unique url of the channel | str",
    "name": "needed | Name of the channel | str",
    "cover_url": "needed | channel image | str",
    "created_at": "needed | Channel creation time | epoch int",
    "freeze": "needed | Indicates whether the channel is currently frozen. The value of true indicates that only "
    "operators can send messages to the channel. | bool",
}

group_channel_sample = {
    "channel_url": "only needed in migration for mapping | unique url of the channel | str",
    "name": "needed | Name of the channel | str",
    "cover_url": "needed | channel image | str",
    "created_at": "needed | Channel creation time | epoch int",
    "is_public": "need to ask | Indicates whether to allow a user to join the channel without an invitation. | bool",
    "freeze": "needed | Indicates whether the channel is currently frozen. The value of true indicates that only "
    "operators can send messages to the channel. | bool",
}
