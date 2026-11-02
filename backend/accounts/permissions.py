"""Permission codes that can be granted to employees.

Administrators implicitly have every permission. Employees only have the
codes stored on their EmployeeProfile.
"""


class Permission:
    STUDENTS_VIEW = "students.view"
    ROOMS_VIEW = "rooms.view"
    FEES_VIEW = "fees.view"
    ATTENDANCE_VIEW = "attendance.view"
    ATTENDANCE_RECORD = "attendance.record"


ALL_PERMISSIONS = [
    Permission.STUDENTS_VIEW,
    Permission.ROOMS_VIEW,
    Permission.FEES_VIEW,
    Permission.ATTENDANCE_VIEW,
    Permission.ATTENDANCE_RECORD,
]

DEFAULT_EMPLOYEE_PERMISSIONS = list(ALL_PERMISSIONS)
