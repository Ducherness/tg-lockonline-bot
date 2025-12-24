from dataclasses import dataclass, field
from typing import List

@dataclass
class Config:
    BOT_TOKEN: str = "."
    MONGO_URI: str = "."
    ADMINS: List[int] = field(default_factory=lambda: [5497807188, 5427382883])
