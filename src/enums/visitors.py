from enum import Enum

class VisitorFilter(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    ENGAGED = "Engaged"
    GUEST = "Guest"
    RECENTLY_REGISTERED = "recently_registered"


class VisitorSort(str, Enum):
    A_Z = "A-Z"
    Z_A = "Z-A"
    NEWEST = "Newest"
    OLDEST = "Oldest"
    MOST_ENGAGED = "most_engaged"

