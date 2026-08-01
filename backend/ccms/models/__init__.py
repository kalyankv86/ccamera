"""Import every model so Base.metadata and Alembic autogenerate see them all."""

from ccms.models.alert import Alert, Escalation
from ccms.models.audit import AuditLog
from ccms.models.check_result import CheckResult, CheckResultDaily
from ccms.models.device import Credential, Device
from ccms.models.maintenance import MaintenanceWindow
from ccms.models.notification import NotificationLog
from ccms.models.settings import Setting
from ccms.models.status_event import StatusEvent
from ccms.models.user import User
from ccms.models.vendor import Vendor

__all__ = [
    "Alert",
    "AuditLog",
    "CheckResult",
    "CheckResultDaily",
    "Credential",
    "Device",
    "Escalation",
    "MaintenanceWindow",
    "NotificationLog",
    "Setting",
    "StatusEvent",
    "User",
    "Vendor",
]
