from typing import List

from ..models.message import MessageModel

class MigrateMessages:
    
    community_id = None
    messages_data = []
    
    def __init__(self, community_id: int, messages_data: List[MessageModel]):
        
        self.community_id = community_id
        self.messages_data = messages_data
        
    def _create_message_in_community(self, req_body):
        
        pass
    
    def create_all_messages(self):
        
        print("*" * 50)
        print(f"Total messages to be added: {len(self.messages_data)}")
        
        for message_data in self.messages_data:
            pass
        
        