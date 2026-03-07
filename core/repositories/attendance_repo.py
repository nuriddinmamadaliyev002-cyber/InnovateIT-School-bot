"""
core/repositories/attendance_repo.py — Davomat (o'quvchi + o'qituvchi)
"""
from core.database import BaseDB


class AttendanceRepo(BaseDB):

    # ── O'quvchi davomati ────────────────────────────────────────

    def save_attendance(self, class_id: int, subject_id: int,
                        date: str, attendance_data: dict,
                        comments: dict = None):
        """
        attendance_data = { student_telegram_id: status }
        comments        = { student_telegram_id: comment_text }
        status: 'present' | 'absent' | 'late' | 'excused'
        subject_id=0 => admin rejimi. FK o'chirilgan holda 0 saqlanadi.
        """
        comments = comments or {}
        use_fk_off = (subject_id == 0)
        with self.conn() as c:
            if use_fk_off:
                c.execute("PRAGMA foreign_keys = OFF")
            for student_id, status in attendance_data.items():
                comment = comments.get(str(student_id))
                c.execute("""
                    INSERT INTO attendance (student_id, class_id, subject_id, date, status, comment)
                    VALUES (?,?,?,?,?,?)
                    ON CONFLICT(student_id, class_id, subject_id, date)
                    DO UPDATE SET status=excluded.status, comment=excluded.comment
                """, (int(student_id), class_id, subject_id, date, status, comment))
            if use_fk_off:
                c.execute("PRAGMA foreign_keys = ON")

    def get_attendance(self, class_id: int, subject_id: int, date: str) -> list:
        with self.conn() as c:
            return c.execute("""
                SELECT a.*, w.full_name
                FROM attendance a JOIN whitelist w ON a.student_id=w.telegram_id
                WHERE a.class_id=? AND a.subject_id=? AND a.date=?
            """, (class_id, subject_id, date)).fetchall()

    def get_student_attendance(self, student_id: int,
                               month: str = None) -> list:
        """
        subject_id=0 (admin rejimi) bo'lishi mumkin — LEFT JOIN ishlatiladi,
        sub.name NULL bo'lganda COALESCE orqali 'Umumiy' ko'rsatiladi.
        """
        with self.conn() as c:
            if month:
                return c.execute("""
                    SELECT a.*, COALESCE(sub.name, 'Umumiy') AS subject_name
                    FROM attendance a LEFT JOIN subjects sub ON a.subject_id=sub.id
                    WHERE a.student_id=? AND strftime('%Y-%m', a.date)=?
                    ORDER BY a.date DESC
                """, (student_id, month)).fetchall()
            return c.execute("""
                SELECT a.*, COALESCE(sub.name, 'Umumiy') AS subject_name
                FROM attendance a LEFT JOIN subjects sub ON a.subject_id=sub.id
                WHERE a.student_id=?
                ORDER BY a.date DESC
            """, (student_id,)).fetchall()

    def get_attendance_stats(self, student_id: int, month: str = None) -> dict:
        records = self.get_student_attendance(student_id, month)
        total   = len(records)
        present = sum(1 for r in records if r["status"] == "present")
        absent  = sum(1 for r in records if r["status"] == "absent")
        late    = sum(1 for r in records if r["status"] == "late")
        pct = round(present / total * 100) if total else 0
        return {"total": total, "present": present,
                "absent": absent, "late": late, "percent": pct}

    # ── O'qituvchi davomati ──────────────────────────────────────

    def save_teacher_attendance(self, school_id: int, date: str,
                                attendance_data: dict, comments: dict = None):
        """attendance_data = { teacher_id: status }, comments = { teacher_id: comment }"""
        comments = comments or {}
        with self.conn() as c:
            for teacher_id, status in attendance_data.items():
                comment = comments.get(str(teacher_id))
                c.execute("""
                    INSERT INTO teacher_attendance (teacher_id, date, status, school_id, comment)
                    VALUES (?,?,?,?,?)
                    ON CONFLICT(teacher_id, date)
                    DO UPDATE SET status=excluded.status, comment=excluded.comment
                """, (int(teacher_id), date, status, school_id, comment))

    def get_teacher_attendance(self, school_id: int, date: str) -> list:
        with self.conn() as c:
            return c.execute("""
                SELECT ta.*, t.full_name
                FROM teacher_attendance ta JOIN teachers t ON ta.teacher_id=t.id
                WHERE ta.school_id=? AND ta.date=?
            """, (school_id, date)).fetchall()

    def get_teacher_attendance_for_teacher(self, teacher_id: int,
                                           month: str = None) -> list:
        with self.conn() as c:
            if month:
                return c.execute("""
                    SELECT * FROM teacher_attendance
                    WHERE teacher_id=? AND strftime('%Y-%m', date)=?
                    ORDER BY date DESC
                """, (teacher_id, month)).fetchall()
            return c.execute(
                "SELECT * FROM teacher_attendance WHERE teacher_id=? ORDER BY date DESC",
                (teacher_id,)
            ).fetchall()

    def get_teacher_attendance_status_for_date(self, school_id: int, date_str: str) -> tuple:
        """
        Berilgan sanada belgilangan va jadval bo'yicha kutilgan o'qituvchilar sonini qaytaradi.
        Returns: (marked_count, total_count)
        """
        import datetime
        try:
            weekday = datetime.date.fromisoformat(date_str).weekday()
        except Exception:
            return 0, 0
        with self.conn() as c:
            total = c.execute("""
                SELECT COUNT(DISTINCT teacher_id) FROM teacher_weekly_schedule
                WHERE school_id=? AND weekday=?
            """, (school_id, weekday)).fetchone()[0]
            marked = c.execute("""
                SELECT COUNT(*) FROM teacher_attendance
                WHERE school_id=? AND date=?
            """, (school_id, date_str)).fetchone()[0]
        return marked, total

    def get_teacher_monthly_attendance(self, school_id: int, month: str) -> list:
        """
        Oylik o'qituvchilar davomati — Excel/PDF uchun.
        month: 'YYYY-MM'
        Returns: [{'full_name', 'date', 'status', 'comment'}, ...]
        """
        with self.conn() as c:
            return c.execute("""
                SELECT t.full_name, ta.date, ta.status, ta.comment
                FROM teacher_attendance ta
                JOIN teachers t ON ta.teacher_id = t.id
                WHERE ta.school_id=? AND strftime('%Y-%m', ta.date)=?
                ORDER BY t.full_name, ta.date
            """, (school_id, month)).fetchall()

    def get_teacher_att_stats(self, teacher_id: int, month: str = None) -> dict:
        records = self.get_teacher_attendance_for_teacher(teacher_id, month)
        total   = len(records)
        present = sum(1 for r in records if r["status"] == "present")
        absent  = sum(1 for r in records if r["status"] == "absent")
        late    = sum(1 for r in records if r["status"] == "late")
        return {"total": total, "present": present, "absent": absent, "late": late}