from dataclasses import dataclass
from typing import Dict, Optional
from pydantic import BaseModel

@dataclass
class CallSession:
    target_id: str
    target_name: str
    target_details: str
    target_call_agenda: str
    target_extra_details: str
    org_name: str
    org_about: str
    transcript: list
    call_uuid: Optional[str] = None
    stream_id: Optional[str] = None
    websocket_connections: Dict = None

    def __post_init__(self):
        if self.websocket_connections is None:
            self.websocket_connections = {}

class data(BaseModel):
    target_id: str

active_calls: Dict[str, CallSession] = {}