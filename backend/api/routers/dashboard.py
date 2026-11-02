from fastapi import APIRouter, Depends

from accounts.models import Role, User
from api.core.db import DBRoute
from api.dependencies import get_current_user, verify_csrf
from api.schemas.dashboard import DashboardSummary
from api.services import dashboard as svc

router = APIRouter(prefix="/dashboard", tags=["Dashboard"], route_class=DBRoute, dependencies=[Depends(verify_csrf)])


@router.get("/summary", response_model=DashboardSummary, summary="Dashboard numbers for the current role",
            description="Roles: any signed-in user. Administrators get the full hostel overview; employees only get figures "
                        "their permissions allow. Every number is calculated from the database.")
def summary(user: User = Depends(get_current_user)):
    return svc.admin_summary(user) if user.role == Role.ADMIN else svc.employee_summary(user)
