"""
core/db.py — Database Facade

Barcha repository'larni birlashtiradi.
config.py da:  db = DB("school.db")
Keyin:         db.get_school(1)  →  SchoolRepo dan
               db.get_teacher(uid)  →  UserRepo dan
"""
from core.repositories.school_repo     import SchoolRepo
from core.repositories.class_repo      import ClassRepo
from core.repositories.user_repo       import UserRepo
from core.repositories.lesson_repo     import LessonRepo
from core.repositories.attendance_repo import AttendanceRepo
from core.repositories.grade_repo      import GradeRepo, ScheduleRepo
from core.repositories.class_group_repo import ClassGroupRepo
from core.database import BaseDB


class DB(
    SchoolRepo,
    ClassRepo,
    UserRepo,
    LessonRepo,
    AttendanceRepo,
    GradeRepo,
    ScheduleRepo,
    ClassGroupRepo,
):
    """
    Yagona DB obyekti — barcha operatsiyalarga kirish nuqtasi.

    Misol:
        from core.db import DB
        db = DB("school.db")
        db.init_tables()

        school = db.get_school(1)
        teacher = db.get_teacher(user_id)
        db.save_attendance(class_id, subject_id, date, data)
    """

    def __init__(self):
        BaseDB.__init__(self)
        self.init_tables()
        self.run_migrations()