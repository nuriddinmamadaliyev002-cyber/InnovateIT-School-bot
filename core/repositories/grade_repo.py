"""
core/repositories/grade_repo.py — Baholar

Yangiliklar (v2):
  save_grade()                — comment parametri qo'shildi
  get_submission_grade()      — topshirmaga bog'liq baho (student+subject+date)
  save_submission_grade()     — topshirmani ko'rib baho + izoh qo'yish
"""
from core.database import BaseDB


class GradeRepo(BaseDB):

    def save_grade(self, student_id: int, teacher_id: int, subject_id: int,
                   class_id: int, criteria: str, score: int, date: str,
                   comment: str = None, comment_file_id: str = None,
                   comment_file_type: str = None):
        with self.conn() as c:
            c.execute("""
                INSERT INTO grades
                    (student_id, teacher_id, subject_id, class_id,
                     criteria, score, date, comment,
                     comment_file_id, comment_file_type)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(student_id, subject_id, criteria, date)
                DO UPDATE SET score=excluded.score,
                              teacher_id=excluded.teacher_id,
                              comment=excluded.comment,
                              comment_file_id=excluded.comment_file_id,
                              comment_file_type=excluded.comment_file_type
            """, (student_id, teacher_id, subject_id, class_id,
                  criteria, score, date, comment,
                  comment_file_id, comment_file_type))

    def get_grades_for_class(self, class_id: int, subject_id: int,
                              criteria: str, date: str) -> list:
        with self.conn() as c:
            return c.execute("""
                SELECT g.*, w.full_name AS student_name
                FROM grades g JOIN whitelist w ON g.student_id=w.telegram_id
                WHERE g.class_id=? AND g.subject_id=? AND g.criteria=? AND g.date=?
            """, (class_id, subject_id, criteria, date)).fetchall()

    def get_student_grades(self, student_id: int,
                           subject_id: int = None, month: str = None) -> list:
        where, params = ["g.student_id=?"], [student_id]
        if subject_id:
            where.append("g.subject_id=?"); params.append(subject_id)
        if month:
            where.append("strftime('%Y-%m', g.date)=?"); params.append(month)
        with self.conn() as c:
            return c.execute(f"""
                SELECT g.*, sub.name AS subject_name
                FROM grades g JOIN subjects sub ON g.subject_id=sub.id
                WHERE {' AND '.join(where)}
                ORDER BY g.date DESC
            """, params).fetchall()

    def get_submission_grade(self, student_id: int,
                              subject_id: int, date: str):
        """
        O'quvchining vazifa topshirmasi uchun baho (criteria='homework').
        O'quvchi 'Hamma vazifalar' da bahoni ko'rish uchun.
        """
        with self.conn() as c:
            return c.execute("""
                SELECT * FROM grades
                WHERE student_id=? AND subject_id=? AND date=? AND criteria='homework'
                ORDER BY date DESC LIMIT 1
            """, (student_id, subject_id, date)).fetchone()

    def get_class_rating(self, class_id: int, subject_id: int) -> list:
        with self.conn() as c:
            return c.execute("""
                SELECT w.telegram_id, w.full_name,
                       ROUND(AVG(g.score), 2) AS avg_score,
                       COUNT(g.id) AS total_grades
                FROM whitelist w
                LEFT JOIN grades g ON g.student_id=w.telegram_id
                    AND g.subject_id=? AND g.class_id=?
                WHERE w.class_id=?
                GROUP BY w.telegram_id
                ORDER BY avg_score DESC NULLS LAST
            """, (subject_id, class_id, class_id)).fetchall()


class ScheduleRepo(BaseDB):
    """O'qituvchi haftalik jadval va Sinf dars jadvali"""

    # ══════════════════════════════════════════════
    #  SINF DARS JADVALI (schedules jadvali)
    # ══════════════════════════════════════════════

    def get_schedule(self, school_id: int = None, class_id: int = None):
        """
        Sinf dars jadvalini olish.
        school_id va class_id bo'yicha qidirish.
        """
        with self.conn() as c:
            if class_id:
                return c.execute("""
                    SELECT * FROM schedules
                    WHERE class_id=?
                    ORDER BY uploaded_at DESC LIMIT 1
                """, (class_id,)).fetchone()
            elif school_id:
                return c.execute("""
                    SELECT * FROM schedules
                    WHERE school_id=?
                    ORDER BY uploaded_at DESC LIMIT 1
                """, (school_id,)).fetchone()
            return None

    def save_schedule(self, school_id: int, class_id: int, 
                      file_id: str, file_type: str = 'photo'):
        """
        Sinf dars jadvalini saqlash yoki yangilash.
        """
        with self.conn() as c:
            # Eski jadvallarni o'chirish
            c.execute("DELETE FROM schedules WHERE class_id=?", (class_id,))
            # Yangi jadval qo'shish
            c.execute("""
                INSERT INTO schedules (school_id, class_id, file_id, file_type)
                VALUES (?,?,?,?)
            """, (school_id, class_id, file_id, file_type))

    def delete_schedule(self, class_id: int):
        """Sinf dars jadvalini o'chirish."""
        with self.conn() as c:
            c.execute("DELETE FROM schedules WHERE class_id=?", (class_id,))

    # ══════════════════════════════════════════════
    #  O'QITUVCHI HAFTALIK JADVALI
    # ══════════════════════════════════════════════

    def add_slot(self, teacher_id: int, class_id: int, subject_id: int,
                 weekday: int, start_time: str, end_time: str, school_id: int) -> bool:
        with self.conn() as c:
            try:
                c.execute("""
                    INSERT OR IGNORE INTO teacher_weekly_schedule
                        (teacher_id, class_id, subject_id, weekday,
                         start_time, end_time, school_id)
                    VALUES (?,?,?,?,?,?,?)
                """, (teacher_id, class_id, subject_id, weekday,
                      start_time, end_time, school_id))
                return True
            except Exception:
                return False

    def get_slots(self, teacher_id: int = None, school_id: int = None) -> list:
        with self.conn() as c:
            if teacher_id:
                return c.execute("""
                    SELECT ws.*, c.name AS class_name, s.name AS subject_name,
                           t.full_name AS teacher_name, sc.name AS school_name
                    FROM teacher_weekly_schedule ws
                    JOIN classes  c  ON ws.class_id=c.id
                    JOIN subjects s  ON ws.subject_id=s.id
                    JOIN teachers t  ON ws.teacher_id=t.id
                    JOIN schools  sc ON ws.school_id=sc.id
                    WHERE ws.teacher_id=?
                    ORDER BY ws.weekday, ws.start_time
                """, (teacher_id,)).fetchall()
            if school_id:
                return c.execute("""
                    SELECT ws.*, c.name AS class_name, s.name AS subject_name,
                           t.full_name AS teacher_name
                    FROM teacher_weekly_schedule ws
                    JOIN classes  c ON ws.class_id=c.id
                    JOIN subjects s ON ws.subject_id=s.id
                    JOIN teachers t ON ws.teacher_id=t.id
                    WHERE ws.school_id=?
                    ORDER BY ws.weekday, ws.start_time
                """, (school_id,)).fetchall()
            return []

    def get_slot(self, slot_id: int):
        with self.conn() as c:
            return c.execute("""
                SELECT ws.*, c.name AS class_name, s.name AS subject_name,
                       t.full_name AS teacher_name
                FROM teacher_weekly_schedule ws
                JOIN classes  c ON ws.class_id=c.id
                JOIN subjects s ON ws.subject_id=s.id
                JOIN teachers t ON ws.teacher_id=t.id
                WHERE ws.id=?
            """, (slot_id,)).fetchone()

    def update_slot_time(self, slot_id: int, start_time: str, end_time: str):
        with self.conn() as c:
            c.execute(
                "UPDATE teacher_weekly_schedule SET start_time=?, end_time=? WHERE id=?",
                (start_time, end_time, slot_id)
            )

    def delete_slot(self, slot_id: int):
        with self.conn() as c:
            c.execute("DELETE FROM teacher_weekly_schedule WHERE id=?", (slot_id,))

    def get_teacher_class_subject_dates(
        self, teacher_id: int, class_id: int, subject_id: int,
        days_back: int = 21, days_forward: int = 7
    ) -> list:
        """
        O'qituvchining berilgan sinf+fan uchun haftalik jadval asosida
        faqat quyidagi sanalarni qaytaradi:
          - Bugun (agar bugun dars bo'lsa)
          - O'tgan eng so'nggi 2 ta dars sanasi

        Qaytaradi: [{'date': 'YYYY-MM-DD', 'weekday': int,
                     'start_time': str, 'end_time': str}, ...]
        yangi sana → eski tartibda (bugun eng yuqorida).
        """
        import datetime
        with self.conn() as c:
            slots = c.execute("""
                SELECT weekday, start_time, end_time
                FROM teacher_weekly_schedule
                WHERE teacher_id=? AND class_id=? AND subject_id=?
                ORDER BY weekday
            """, (teacher_id, class_id, subject_id)).fetchall()

        if not slots:
            return []

        lesson_weekdays = {s['weekday']: s for s in slots}
        today = datetime.date.today()
        today_wd = today.weekday()

        result = []

        # 1. Bugun dars bo'lsa — qo'shamiz
        if today_wd in lesson_weekdays:
            slot = lesson_weekdays[today_wd]
            result.append({
                'date':       today.isoformat(),
                'weekday':    today_wd,
                'start_time': slot['start_time'] or '',
                'end_time':   slot['end_time']   or '',
            })

        # 2. O'tgan 2 ta dars sanasini topamiz (kechadan boshlab)
        past = []
        for delta in range(1, 90):          # 90 kun orqaga — yetarli
            d  = today - datetime.timedelta(days=delta)
            wd = d.weekday()
            if wd in lesson_weekdays:
                slot = lesson_weekdays[wd]
                past.append({
                    'date':       d.isoformat(),
                    'weekday':    wd,
                    'start_time': slot['start_time'] or '',
                    'end_time':   slot['end_time']   or '',
                })
            if len(past) == 2:
                break

        result.extend(past)
        return result

    def get_today_teachers(self, school_id: int, weekday: int) -> list:
        with self.conn() as c:
            return c.execute("""
                SELECT DISTINCT t.id, t.full_name,
                    GROUP_CONCAT(c.name || ' - ' || s.name) AS schedule_info
                FROM teacher_weekly_schedule ws
                JOIN teachers t ON ws.teacher_id=t.id
                JOIN classes  c ON ws.class_id=c.id
                JOIN subjects s ON ws.subject_id=s.id
                WHERE ws.school_id=? AND ws.weekday=?
                GROUP BY t.id
                ORDER BY t.full_name
            """, (school_id, weekday)).fetchall()