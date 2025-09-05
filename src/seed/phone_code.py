import json
from src.models import PhoneCode 
from pathlib import Path

phone_codes_path = Path(__file__).resolve().parent.parent.parent / "phone_codes.json"

async def seed_phone_codes():
    try:
        # Load phone codes from JSON file
        with open(phone_codes_path, "r", encoding="utf-8") as f:
            phone_codes = json.load(f)

        for  code in phone_codes:
            phone_code = await PhoneCode.create(
                name=code["name"],
                dial_code=code["dial_code"],
                code=code["code"]
            )
           
        print("***Phone codes seeded successfully.")
    except Exception as e:
        print(f"Error seeding phone codes: {e}")

