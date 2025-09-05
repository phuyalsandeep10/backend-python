from .models import CustomerVisitLogs
from src.services.ip_service import IPService
from typing import List, Optional
from .schema import VisitorLogsSchema

from datetime import datetime
from .schema import VisitorSchema
from src.enums import VisitorFilter, VisitorSort
from src.models import CustomerActivities

async def save_log(ip: str, customer_id: int, request):
    data = {}

    data = await IPService.get_ip_info(ip)

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

def filter_and_sort_visitors(
    visitors: List[VisitorLogsSchema],
    visitors_data: List[dict],
    status_filters: List[str] = [],
    sort_by: Optional[str] = None,
    match_mode: str = "or",
) -> List[VisitorLogsSchema]:
    """
    Filters and sorts visitors based on given criteria
    """
    def matches_filter(v, filter_type: VisitorFilter) -> bool:
        """Check if a visitor matches a single filter"""
        if filter_type == VisitorFilter.ACTIVE:
            return v.status == "Active"
        if filter_type == VisitorFilter.INACTIVE:
            return v.status == "Inactive"
        if filter_type == VisitorFilter.ENGAGED:
            return v.engagged == "YES"
        if filter_type == VisitorFilter.GUEST:
            return v.visitor_name and v.visitor_name.startswith("guest")
        if filter_type == VisitorFilter.RECENTLY_REGISTERED:
            cust = next((c for c in visitors_data if c["customer_id"] == v.customer_id), None)
            if cust and cust.get("created_at"):
                try:
                    created_at = datetime.fromisoformat(cust["created_at"])
                    return (datetime.utcnow() - created_at).days <= 1
                except ValueError:
                    return False
            return False
        return False

    # -------- FILTER --------
    if status_filters:
        filtered = []
        for v in visitors:
            matches = [matches_filter(v, f) for f in status_filters]
            if match_mode == "or" and any(matches):  # if matches at least one filter
                filtered.append(v)
            elif match_mode == "and" and all(matches):  # must match all filters
                filtered.append(v)
        visitors = filtered

    # -------- SORT --------
    if sort_by:
        customer_created_at_map = {
            c["customer_id"]: datetime.fromisoformat(c["created_at"])
            for c in visitors_data
            if c.get("created_at")
        }

        if sort_by == VisitorSort.A_Z:
            visitors.sort(key=lambda v: v.visitor_name or "")
        elif sort_by == VisitorSort.Z_A:
            visitors.sort(key=lambda v: v.visitor_name or "", reverse=True)
        elif sort_by == VisitorSort.NEWEST:
            visitors.sort(
                key=lambda v: customer_created_at_map.get(v.customer_id, datetime.min),
                reverse=True,
            )
        elif sort_by == VisitorSort.OLDEST:
            visitors.sort(
                key=lambda v: customer_created_at_map.get(v.customer_id, datetime.max)
            )
        elif sort_by == VisitorSort.MOST_ENGAGED:
            visitors.sort(key=lambda v: v.num_of_visits, reverse=True)

    return visitors

    

def build_log_list(visitors_data,customer_visit_count):
    visitors=[]
    for log in visitors_data:
        customer_id = log.get("customer_id")
        join_at = datetime.fromisoformat(log["join_at"])
        left_at = log.get("left_at")
        if left_at:
            left_at = datetime.fromisoformat(left_at)
        last_active = left_at or datetime.utcnow()
        active_duration = last_active - join_at
        status = "Active" if left_at is None else "Inactive"
        engaged = "YES" if status == "Active" else "NO"

        visitors.append(
            VisitorLogsSchema(
                id=log["id"],
                customer_id=customer_id,
                visitor_name=log["customer_name"],
                status=status,
                last_active=last_active.isoformat(),
                active_duration=str(active_duration),
                num_of_visits=customer_visit_count[customer_id],
                engagged=engaged,
                ip_address=log.get("ip_address") or "",
            )
        )
    
    return visitors


def get_visitors_by_location(visitor_data):
    location_count = {}     
    for log in visitor_data:
        key = (log.get("latitude"), log.get("longitude"))
        if key not in location_count:
            location_count[key] = 0
        location_count[key] += 1

    visitors_by_location = [
        {"latitude": lat, "longitude": lon, "count": count}
        for (lat, lon), count in location_count.items()
        if lat is not None and lon is not None
    ]

    return visitors_by_location

async def get_visitors_data(visit_log,customer):
    engaged = "YES" if visit_log and visit_log.left_at is None else "NO"
    ip_address = visit_log.ip_address if visit_log else customer.ip_address or ""
    location = ""
    if visit_log:
        parts = [visit_log.city, visit_log.country]
        location = ", ".join(filter(None, parts))
    browser = visit_log.browser if visit_log else ""
    login_time = visit_log.join_at.isoformat() if visit_log else ""

    picture = customer.attributes.get("picture") if customer.attributes else ""

    # Fetch recent activities
    activities = await CustomerActivities.get_all(where={"customer_id": customer.id})
    activity_list = [act.to_json() for act in activities]

    visitor_data = VisitorSchema(
        customer_id=customer.id,
        email=customer.email or "",
        picture=picture or "",
        engagged=engaged,
        ip_address=ip_address,
        location=location,
        browser=browser or "",
        login_time=login_time or "",
        activities=activity_list,
    )

    return visitor_data