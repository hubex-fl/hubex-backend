from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DeviceListItem(BaseModel):
    id: int
    device_uid: str
    claimed: bool
    last_seen: Optional[datetime]
    online: bool
