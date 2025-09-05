from src.models import Conversation, Customer, CustomerVisitLogs, Organization


async def create_customer_seed():
    print("Creating customer seed")
    customer = {
        "ip_address": "203.0.113.1",
        "email": "customer@chatboq.com",
        "phone": "1234567890",
        "name": "Guest-1",
    }
    customer2 = {
        "ip_address": "203.0.113.1",
        "email": None,
        "phone": None,
        "name": "Guest-1",
    }
    org = await Organization.first()
    if not org:
        print("Organization not found")
        return
    customer["organization_id"] = org.id
    customer2["organization_id"] = org.id
    customer1 = await Customer.create(**customer)
    customersecond = await Customer.create(**customer2)
    print("Customer created")

    conversation = {
        "ip_address": "203.0.113.1",
        "customer_id": customer1.id,
        "organization_id": org.id,
    }
    conversation = await Conversation.create(**conversation)
    print("Conversation created")


