import asyncio
from src.models import Country, Timezone

# ---------------- Countries ----------------
COUNTRIES = [
    ("Nepal", "NP", "NPL", "+977"),
    ("United States", "US", "USA", "+1"),
    ("United Kingdom", "GB", "GBR", "+44"),
    ("Japan", "JP", "JPN", "+81"),
    ("Germany", "DE", "DEU", "+49"),
    ("India", "IN", "IND", "+91"),
    ("Australia", "AU", "AUS", "+61"),
    ("Canada", "CA", "CAN", "+1"),
    ("France", "FR", "FRA", "+33"),
    ("Brazil", "BR", "BRA", "+55"),
]

# ---------------- Seed Timezones ----------------
TIMEZONES = [
    ("Asia/Kathmandu", "Nepal Time", 1),
    ("America/New_York", "Eastern Time", 2),
    ("America/Los_Angeles", "Pacific Time", 2),
    ("Europe/London", "Greenwich Mean Time", 3),
    ("Europe/Berlin", "Central European Time", 5),
    ("Asia/Tokyo", "Japan Standard Time", 4),
    ("Asia/Kolkata", "India Standard Time", 6),
    ("Australia/Sydney", "Australian Eastern Time", 7),
    ("America/Toronto", "Eastern Time", 8),
    ("America/Sao_Paulo", "Brasilia Time", 10),
]

# ---------------- Seed Countries ----------------
async def seed_countries():
    print("****Seeding Countries")
    for name, iso2, iso3, phone in COUNTRIES:
        country = await Country.create(
            name=name,
            iso_code_2=iso2,
            iso_code_3=iso3,
            phone_code=phone
        )
        print(f"Created Country: {country.name} ({country.id})")

# ---------------- Seed Timezones ----------------
async def seed_timezones():
    print("****Seeding Timezones")
    for name, display, country_id in TIMEZONES:
        tz = await Timezone.create(
            name=name,
            display_name=display,
            country_id=country_id
        )
        print(f"Created Timezone: {tz.name} for Country ID: {tz.country_id}")
