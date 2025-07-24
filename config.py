from dataclasses import dataclass, field
from typing import List

@dataclass
class Config:
    BOT_TOKEN: str = "7998596142:AAESeko15GXQ29wsxuFTxqIUSIZ61EcTCkY"
    MONGO_URI: str = "mongodb+srv://reposgithub0:TNNr3YsOq8XVFDGF@cluster0.di9v5tu.mongodb.net/"
    ADMINS: List[int] = field(default_factory=lambda: [5497807188, 5427382883])