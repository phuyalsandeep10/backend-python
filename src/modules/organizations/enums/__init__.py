from enum import Enum


class ShiftType(str, Enum):
    MORNING = "morning" 
    DAY = "day"
    NIGHT = "night"


class WeekDay(str, Enum):
    SUNDAY = "Sunday" 
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"

class AccessLevel(str, Enum):
    LEAD = "Lead"
    ADMIN = "Admin"
    MODERATOR = "Moderator"
    AGENT = "Agent"
    MEMBER = "Member"
