"""
core/repositories/attendance_repo.py — PostgreSQL versiyasi

Asosiy farq:
  strftime('%Y-%m', date) → TO_CHAR(date::date, 'YYYY-MM')
"""
import psycopg2.extras
from core.database import BaseDB


class AttendanceRepo(BaseDB):

    def _fetchone(self, conn, q, p=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(q, p); return cur.fetchone()

    def _fetchall(self, conn, q, p=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(q, p); return cur.fetchall() or []

    # ── O'quvchi davomati ────────────────────────────────────────

    def save_attendance(self, class_id: int, subject_id: int,
                        date: str, attendance_data: dict,
                        comments: dict = None):
        comments = comments or {}
        with self.conn() as conn:
            with conn.cursor() as cur:
                for student_id, status in attendance_data.items():
                    comment = comments.get(str(student_id))
                    cur.execute("""
                        INSERT INTO attendance
                            (student_id, class_id, subject_id, date, status, comment)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT(student_id, class_id, subject_id, date)
                        DO UPDATE SET status=EXCLUDED.status, comment=EXCLUDED.comment
                    """, (int(student_id), class_id, subject_id, date, status, comment))
            conn.commit()

    def get_attendance(self, class_id: int, subject_id: int, date: str) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT a.*, w.full_name
                FROM attendance a JOIN whitelist w ON a.student_id=w.telegram_id
                WHERE a.class_id=%s AND a.subject_id=%s AND a.date=%s
            """, (class_id, subject_id, date))

    def get_student_attendance(self, student_id: int, month: str = None) -> list:
        with self.conn() as conn:
            if month:
                return self._fetchall(conn, """
                    SELECT a.*, COALESCE(sub.name, 'Umumiy') AS subject_name
                    FROM attendance a LEFT JOIN subjects sub ON a.subject_id=sub.id
                    WHERE a.student_id=%s AND TO_CHAR(a.date::date, 'YYYY-MM')=%s
                    ORDER BY a.date DESC
                """, (student_id, month))
            return self._fetchall(conn, """
                SELECT a.*, COALESCE(sub.name, 'Umumiy') AS subject_name
                FROM attendance a LEFT JOIN subjects sub ON a.subject_id=sub.id
                WHERE a.student_id=%s ORDER BY a.date DESC
            """, (student_id,))

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
        comments = comments or {}
        with self.conn() as conn:
            with conn.cursor() as cur:
                for teacher_id, status in attendance_data.items():
                    comment = comments.get(str(teacher_id))
                    cur.execute("""
                        INSERT INTO teacher_attendance
                            (teacher_id, date, status, school_id, comment)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT(teacher_id, date)
                        DO UPDATE SET status=EXCLUDED.status, comment=EXCLUDED.comment
                    """, (int(teacher_id), date, status, school_id, comment))
            conn.commit()

    def get_teacher_attendance(self, school_id: int, date: str) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT ta.*, t.full_name
                FROM teacher_attendance ta JOIN teachers t ON ta.teacher_id=t.id
                WHERE ta.school_id=%s AND ta.date=%s
            """, (school_id, date))

    def get_teacher_attendance_for_teacher(self, teacher_id: int,
                                           month: str = None) -> list:
        with self.conn() as conn:
            if month:
                return self._fetchall(conn, """
                    SELECT * FROM teacher_attendance
                    WHERE teacher_id=%s AND TO_CHAR(date::date, 'YYYY-MM')=%s
                    ORDER BY date DESC
                """, (teacher_id, month))
            return self._fetchall(conn,
                "SELECT * FROM teacher_attendance WHERE teacher_id=%s ORDER BY date DESC",
                (teacher_id,))

    def get_teacher_attendance_status_for_date(self, school_id: int, date_str: str) -> tuple:
        import datetime
        try:
            weekday = datetime.date.fromisoformat(date_str).weekday()
        except Exception:
            return 0, 0
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(DISTINCT teacher_id) FROM teacher_weekly_schedule
                    WHERE school_id=%s AND weekday=%s
                """, (school_id, weekday))
                total = cur.fetchone()[0]
                cur.execute("""
                    SELECT COUNT(*) FROM teacher_attendance
                    WHERE school_id=%s AND date=%s
                """, (school_id, date_str))
                marked = cur.fetchone()[0]
        return marked, total

    def get_teacher_monthly_attendance(self, school_id: int, month: str) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT t.full_name, ta.date, ta.status, ta.comment
                FROM teacher_attendance ta
                JOIN teachers t ON ta.teacher_id = t.id
                WHERE ta.school_id=%s AND TO_CHAR(ta.date::date, 'YYYY-MM')=%s
                ORDER BY t.full_name, ta.date
            """, (school_id, month))

    def get_teacher_att_stats(self, teacher_id: int, month: str = None) -> dict:
        records = self.get_teacher_attendance_for_teacher(teacher_id, month)
        total   = len(records)
        present = sum(1 for r in records if r["status"] == "present")
        absent  = sum(1 for r in records if r["status"] == "absent")
        late    = sum(1 for r in records if r["status"] == "late")
        return {"total": total, "present": present, "absent": absent, "late": late}
