"""Fill the database with realistic demo data for screenshots and manual testing.

    python manage.py seed_demo

Requires an existing administrator (python manage.py createsuperuser).
Safe to run twice: it does nothing if demo students already exist.
Creates no user accounts and no passwords.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Role, User
from attendance.models import Attendance
from fees.models import FeeStructure, Payment, StudentFee
from rooms.models import Room, RoomAllocation
from students.models import Student

FIRST = ["Asha", "Rohan", "Meera", "Kabir", "Isha", "Aarav", "Neha", "Vikram", "Sana", "Arjun", "Priya", "Dev"]
LAST = ["Patil", "Deshmukh", "Kulkarni", "Joshi", "Shah", "Iyer", "Khan", "Pawar", "More", "Naik", "Jadhav", "Gupta"]


class Command(BaseCommand):
    help = "Create demo rooms, students, fees, payments and attendance."

    @transaction.atomic
    def handle(self, *args, **options):
        admin = User.objects.filter(role=Role.ADMIN, is_active=True).first()
        if not admin:
            raise CommandError("Create an administrator first: python manage.py createsuperuser")
        if Student.objects.filter(enrollment_no__startswith="DEMO-").exists():
            self.stdout.write("Demo data already present; nothing to do.")
            return

        rnd = random.Random(7)
        today = timezone.localdate()

        rooms = []
        for block in ("A", "B"):
            for floor in (1, 2):
                for n in (1, 2, 3):
                    cap = {1: 2, 2: 3, 3: 4}[n]
                    rooms.append(Room.objects.create(
                        room_number=f"{block}{floor}0{n}", room_type={2: "double", 3: "triple", 4: "dormitory"}[cap],
                        block=block, floor=floor, capacity=cap, monthly_rate=Decimal(3000 + cap * 500),
                    ))
        Room.objects.filter(room_number="B203").update(is_active=False)

        structure = FeeStructure.objects.create(name="Monthly hostel fee", amount=Decimal("4500.00"), frequency="monthly",
                                                description="Room rent and mess charges")
        students = []
        for i, (first, last) in enumerate(zip(FIRST, LAST), start=1):
            students.append(Student.objects.create(
                enrollment_no=f"DEMO-{i:03d}", full_name=f"{first} {last}", email=f"{first.lower()}.{last.lower()}@example.com",
                phone=f"+9198000{i:05d}", gender=rnd.choice(["male", "female"]), address=f"{i} College Road, Pune",
                guardian_name=f"{last} Senior", guardian_phone=f"+9197000{i:05d}", admission_date=today - timedelta(days=rnd.randint(20, 200)),
            ))

        open_rooms = [r for r in rooms if r.is_active]
        for i, student in enumerate(students[:10]):
            RoomAllocation.objects.create(student=student, room=open_rooms[i // 2], start_date=student.admission_date)

        for i, student in enumerate(students):
            due = today.replace(day=1) + timedelta(days=9)
            fee = StudentFee.objects.create(student=student, structure=structure, amount_due=structure.amount,
                                            due_date=due, description=due.strftime("%B %Y"))
            if i % 3 == 0:
                Payment.objects.create(fee=fee, amount=structure.amount, payment_date=min(today, due), method="upi",
                                       transaction_reference=f"DEMO-UPI-{i:04d}", recorded_by=admin)
            elif i % 3 == 1:
                Payment.objects.create(fee=fee, amount=Decimal("2000.00"), payment_date=min(today, due), method="cash", recorded_by=admin)

        for back in range(1, 8):
            day = today - timedelta(days=back)
            for student in students:
                Attendance.objects.create(student=student, date=day, recorded_by=admin,
                                          status=rnd.choices(["present", "absent", "leave"], [8, 1, 1])[0])

        self.stdout.write(self.style.SUCCESS(
            f"Created {len(rooms)} rooms, {len(students)} students, fees, payments and a week of attendance."))
