from typing import NamedTuple
from enum import Enum 


class SiteDetails(NamedTuple):
    name: str
    fullName: str

class TrialDetails(NamedTuple):
    name: str
    fullName: str

class UploadPacketType(Enum):
    ANY = 0
    PROCESSED = 1
    UNPROCESSED = 2
    UNKNOWN = 3

class DBUpdateResult(NamedTuple):
    success: bool
    rowsUpdated: int
    message: str
