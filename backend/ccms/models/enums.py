import enum


class DeviceType(str, enum.Enum):
    CAMERA = "camera"
    NVR = "nvr"
    SWITCH = "switch"


class Criticality(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"


class DeviceState(str, enum.Enum):
    UP = "UP"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    MAINTENANCE = "MAINTENANCE"
    UNKNOWN = "UNKNOWN"


class CheckType(str, enum.Enum):
    PING = "PING"
    RTSP = "RTSP"
    IMAGE = "IMAGE"
    NVR = "NVR"
    SNMP = "SNMP"


class CheckStatus(str, enum.Enum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    FAIL = "FAIL"
    ERROR = "ERROR"


class AlertSeverity(str, enum.Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertState(str, enum.Enum):
    OPEN = "open"
    ACKED = "acked"
    CLOSED = "closed"


class Role(str, enum.Enum):
    ADMIN = "admin"
    SECURITY_OFFICER = "security_officer"
    TECHNICIAN = "technician"
    VIEWER = "viewer"


class MaintenanceScope(str, enum.Enum):
    DEVICE = "device"
    GROUP = "group"
    BUILDING = "building"
    CAMPUS = "campus"


class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"


class NotificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED_NOT_CONFIGURED = "SKIPPED_NOT_CONFIGURED"
