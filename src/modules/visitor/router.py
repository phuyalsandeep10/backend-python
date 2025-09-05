from fastapi import APIRouter, Depends
from fastapi import Request
from src.common.dependencies import get_current_user
from src.models import Conversation, Customer, CustomerVisitLogs, CustomerActivities
from src.modules.organizations.models import Organization
from src.utils.response import CustomResponse as cr
from src.utils.common import get_location
from src.modules.chat.services.message_service import MessageService
from src.modules.chat.schema import MessageSchema, EditMessageSchema
from .schema import CustomerEmailSchema
from src.common.context import UserContext, TenantContext
from src.websocket.services.conversation_service import ConversationService
from src.tasks.organization_task import send_customer_welcome_mail
#customer router
from src.modules.chat.models.message import Message
from .services import save_log, filter_and_sort_visitors, get_visitors_data, get_visitors_by_location,build_log_list
from .schema import (
    VisitorsResponseSchema,
    VisitorSchema,

)

from fastapi.encoders import jsonable_encoder


router = APIRouter()


@router.post("/create")
async def create_customer( request: Request):
    organizationId = TenantContext.get()

    header = request.headers.get("X-Forwarded-For")
    organizationId = TenantContext.get()

    ip = header.split(",")[0].strip() if header else request.client.host

    print(f"create customer api {ip}")

    result = await Customer.sql(
        f"select count(*) from org_customers where organization_id={organizationId}"
    )
    customer_count = result[0]["count"]
    customer_count += 1

    customer = await Customer.create(
        name=f"guest-{customer_count}", ip_address=ip, organization_id=organizationId
    )

 

    await save_log(ip, customer.id, request)

    return cr.success(
        data={"customer": customer.to_json()}
    )


async def save_log(ip: str, customer_id: int, request):
    data = {}

    data = await get_location(ip)

    city = data.get("city")
    country = data.get("country")
    latitude = data.get("lat")
    longitude = data.get("lon")

    user_agent = request.headers.get("User-Agent", "")
    browser = user_agent.split(" ")[0]
    os = user_agent.split(" ")[1]
    device_type = user_agent.split(" ")[2]
    device = user_agent.split(" ")[3]
    referral_from = request.headers.get("Referer") or None

    log = await CustomerVisitLogs.create(
        customer_id=customer_id,
        ip_address=ip,
        city=city,
        country=country,
        latitude=latitude,
        longitude=longitude,
        device=device,
        browser=browser,
        os=os,
        device_type=device_type,
        referral_from=referral_from,
    )
    return log


@router.put('/{customer_id}/customer-email')
async def customer_email_update(customer_id:int,body:CustomerEmailSchema):
    """update customer email"""
    organization_id = TenantContext.get()
    customer = await Customer.find_one({
        "id":customer_id,
        "organization_id":organization_id
    })
    if not customer:
        return cr.error(data='Not found')
    
    customer = await Customer.update(customer.id,email=body.email)
    organization = await Organization.get(organization_id)
    send_customer_welcome_mail.send(email=body.email,organization=organization.name)

    return cr.success(data=customer.to_json())


    

@router.get("/visitors")
async def get_visitors(user=Depends(get_current_user)):
    """Get all visitor logs for the current organization"""
    organization_id = TenantContext.get()

    query = f"""
    SELECT logs.*, cust.name AS customer_name, cust.email AS customer_email, cust.created_at
    FROM org_customer_logs AS logs
    JOIN org_customers AS cust
      ON logs.customer_id = cust.id
    WHERE cust.organization_id = {organization_id}
      AND cust.deleted_at IS NULL   
      AND logs.deleted_at IS NULL 
    ORDER BY logs.join_at DESC
    """

    visitors_data = await CustomerVisitLogs.sql(query)

    # Compute number of visits per customer
    customer_visit_count = {}
    for log in visitors_data:
        cid = log["customer_id"]
        customer_visit_count[cid] = customer_visit_count.get(cid, 0) + 1

    # Compute visits by location
    visitors_by_location=get_visitors_by_location(visitors_data)
    

    # Build visitors log list
    visitors=build_log_list(visitors_data,customer_visit_count)

    # Apply filtering and sorting
    visitors = filter_and_sort_visitors(
        visitors, visitors_data
    )

    response_data = VisitorsResponseSchema(
        visitors=visitors, visitors_by_location=visitors_by_location
    )

    return cr.success(
        data=jsonable_encoder(response_data),
        message="Successfully retrieved visitors data",
    )


@router.get("/visitor", response_model=VisitorSchema)
async def get_visitor(customer_id: int, user=Depends(get_current_user)):
    organization_id = TenantContext.get()

    # Fetch customer
    customer = await Customer.find_one(where={"id": customer_id})
    if not customer:
        return cr.failed(message="Customer not found")

    # Fetch latest visit log
    visit_log = await CustomerVisitLogs.find_one(where={"customer_id": customer_id})

    # Compute fields
    visitors_data=get_visitors_data(visit_log,customer)

    return cr.success(data=jsonable_encoder(visitors_data))


@router.post("/delete-logs")
async def delete_logs(log_id: int, user=Depends(get_current_user)):
    visit_log=await CustomerVisitLogs.find_one(where={'id':log_id})
    if visit_log:
        await CustomerVisitLogs.soft_delete(where={"id": visit_log.id})
        return cr.success(message="Visit Log deleted successfully")
    
    return cr.error(message="Visit Log not found or already deleted")

    
@router.post("/{customer_id}/visit")
async def customer_visit(customer_id: int, request: Request):
    header = request.headers.get("X-Forwarded-For")
    ip = header.split(",")[0].strip() if header else request.client.host
    print(f"visit api {ip}")

    customer = await Customer.get(customer_id)
    if not customer:
        return cr.error(message="Customer Not found")

    log = await save_log(ip, customer_id, request)

    return cr.success(data=log.to_json())



@router.get("/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: int):
    messages = await Message.filter(where={"conversation_id": conversation_id})

    return cr.success(data= [msg.to_json() for msg in messages])


@router.post("/conversations/{conversation_id}/messages")
async def create_conversation_message(conversation_id: int, payload: MessageSchema):
    organizationId = TenantContext.get()
    userId = UserContext.get()
    service = MessageService(organization_id=organizationId, user_id=userId, payload=payload)
    response =  await service.create(conversation_id)
    return cr.success(data=response)


@router.get("/agents")
async def get_organization_agents():
    organization_id = TenantContext.get()
    print(f"organization_id {organization_id}")
    from src.models import User
    records = await User.filter({"organization_id": organization_id})
    return cr.success(data=[record.to_json() for record in records])
# edit the message
@router.put("/{organization_id}/messages/{message_id}")
async def edit_message(message_id: int, payload: EditMessageSchema):
    organizationId = TenantContext.get()
    print(f"organizationId {organizationId}")

    userId = UserContext.get()

    service = MessageService(organizationId, payload, userId)
    record = await service.edit(message_id)

    return cr.success(data=record.to_json())

@router.post('/{customer_id}/initialize-conversation')
async def initialize_conversation(customer_id: int,payload:MessageSchema):
    organizationId = TenantContext.get()
    payload.customer_id = customer_id
    record = await Conversation.create(
        customer_id=customer_id,
        organization_id=organizationId,
    )
    service = MessageService(organization_id=organizationId, payload=payload)
    message = await service.create(record.id)
    await ConversationService().customer_join_conversation(customer_id=customer_id, conversation_id=record.id)

    

    
    
    return cr.success(data={
        "conversation":record.to_json(),
        "message":message
    })