"""utils/keyboards/__init__.py — Barcha klaviaturalarni re-export"""
from .reply_kb import kb_super_admin, kb_school_admin, kb_teacher, kb_student
from .inline_kb import (
    kb_cancel, kb_cancel_teacher, kb_classes, kb_subjects, kb_teacher_subjects,
    kb_dates, kb_schedule_dates, kb_lesson_actions, kb_teacher_files, kb_student_files,
)
from .attendance_kb import kb_student_attendance, kb_teacher_attendance, kb_teacher_att_dates, kb_att_dates_for_class
from .grade_kb import (
    kb_grade_dates,
    kb_grade_criteria, kb_grade_criteria_group,
    kb_grade_students, kb_grade_students_group, kb_grade_score,
    kb_tws_teachers, kb_tws_classes, kb_tws_subjects, kb_tws_weekdays, kb_tws_view_slots,
)