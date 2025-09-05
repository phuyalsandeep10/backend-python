from enum import Enum
from .organization import InvitationStatus
from .visitors import VisitorFilter, VisitorSort

class ProviderEnum(str, Enum):
    GOOGLE = "google"
    APPLE = "apple"
