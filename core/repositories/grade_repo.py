"""
core/repositories/grade_repo.py — PostgreSQL versiyasi

strftime('%Y-%m', date) → TO_CHAR(date::date, 'YYYY-MM')
NULLS LAST → PostgreSQL da ishlaydi
GROUP_CONCAT → STRING_AGG
"""
import psycopg2.extras
from core.database import BaseDB


class GradeRepo(BaseDB):

    def _fetchone(self, conn, q, p=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(q, p); return cur.fetchone()

    def _fetchall(self, conn, q, p=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(q, p); return cur.fetchall() or []

    def save_grade(self, student_id, teacher_id, subject_id,
                   class_id, criteria, score, date,
                   comment=None, comment_file_id=None, comment_file_type=None):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO grades
                        (student_id, teacher_id, subject_id, class_id,
                         criteria, score, date, comment,
                         comment_file_id, comment_file_type)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(student_id, subject_id, criteria, date)
                    DO UPDATE SET
                        score=EXCLUDED.score,
                        teacher_id=EXCLUDED.teacher_id,
                        comment=EXCLUDED.comment,
                        comment_file_id=EXCLUDED.comment_file_id,
                        comment_file_type=EXCLUDED.comment_file_type
                """, (student_id, teacher_id, subject_id, class_id,
                      criteria, score, date, comment,
                      comment_file_id, comment_file_type))
            conn.commit()

    def get_grades_for_class(self, class_id, subject_id, criteria, date) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT g.*, w.full_name AS student_name
                FROM grades g JOIN whitelist w ON g.student_id=w.telegram_id
                WHERE g.class_id=%s AND g.subject_id=%s AND g.criteria=%s AND g.date=%s
            """, (class_id, subject_id, criteria, date))

    def get_student_grades(self, student_id, subject_id=None, month=None) -> list:
        where, params = ["g.student_id=%s"], [student_id]
        if subject_id:
            where.append("g.subject_id=%s"); params.append(subject_id)
        if month:
            where.append("TO_CHAR(g.date::date, 'YYYY-MM')=%s"); params.append(month)
        with self.conn() as conn:
            return self._fetchall(conn, f"""
                SELECT g.*, sub.name AS subject_name
                FROM grades g JOIN subjects sub ON g.subject_id=sub.id
                WHERE {' AND '.join(where)} ORDER BY g.date DESC
            """, params)

    def get_submission_grade(self, student_id, subject_id, date):
        with self.conn() as conn:
            return self._fetchone(conn, """
                SELECT * FROM grades
                WHERE student_id=%s AND subject_id=%s AND date=%s AND criteria='homework'
                ORDER BY date DESC LIMIT 1
            """, (student_id, subject_id, date))

    def get_class_rating(self, class_id, subject_id) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT w.telegram_id, w.full_name,
                       ROUND(AVG(g.score)::numeric, 2) AS avg_score,
                       COUNT(g.id) AS total_grades
                FROM whitelist w
                LEFT JOIN grades g ON g.student_id=w.telegram_id
                    AND g.subject_id=%s AND g.class_id=%s
                WHERE w.class_id=%s
                GROUP BY w.telegram_id, w.full_name
                ORDER BY avg_score DESC NULLS LAST
            """, (subject_id, class_id, class_id))


class ScheduleRepo(BaseDB):

    def _fetchone(self, conn, q, p=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(q, p); return cur.fetchone()

    def _fetchall(self, conn, q, p=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(q, p); return cur.fetchall() or []

    def get_schedule(self, school_id=None, class_id=None):
        with self.conn() as conn:
            if class_id:
                return self._fetchone(conn, """
                    SELECT * FROM schedules WHERE class_id=%s
                    ORDER BY uploaded_at DESC LIMIT 1
                """, (class_id,))
            elif school_id:
                return self._fetchone(conn, """
                    SELECT * FROM schedules WHERE school_id=%s
                    ORDER BY uploaded_at DESC LIMIT 1
                """, (school_id,))
            return None

    def save_schedule(self, school_id, class_id, file_id, file_type='photo'):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM schedules WHERE class_id=%s", (class_id,))
                cur.execute("""
                    INSERT INTO schedules (school_id, class_id, file_id, file_type)
                    VALUES (%s,%s,%s,%s)
                """, (school_id, class_id, file_id, file_type))
            conn.commit()

    def delete_schedule(self, class_id):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM schedules WHERE class_id=%s", (class_id,))
            conn.commit()

    def add_slot(self, teacher_id, class_id, subject_id,
                 weekday, start_time, end_time, school_id) -> bool:
        try:
            with self.conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO teacher_weekly_schedule
                            (teacher_id, class_id, subject_id, weekday,
                             start_time, end_time, school_id)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (teacher_id, class_id, subject_id, weekday) DO NOTHING
                    """, (teacher_id, class_id, subject_id, weekday,
                          start_time, end_time, school_id))
                conn.commit()
            return True
        except Exception:
            return False

    def get_slots(self, teacher_id=None, school_id=None) -> list:
        with self.conn() as conn:
            if teacher_id:
                return self._fetchall(conn, """
                    SELECT ws.*, c.name AS class_name, s.name AS subject_name,
                           t.full_name AS teacher_name, sc.name AS school_name
                    FROM teacher_weekly_schedule ws
                    JOIN classes  c  ON ws.class_id=c.id
                    JOIN subjects s  ON ws.subject_id=s.id
                    JOIN teachers t  ON ws.teacher_id=t.id
                    JOIN schools  sc ON ws.school_id=sc.id
                    WHERE ws.teacher_id=%s ORDER BY ws.weekday, ws.start_time
                """, (teacher_id,))
            if school_id:
                return self._fetchall(conn, """
                    SELECT ws.*, c.name AS class_name, s.name AS subject_name,
                           t.full_name AS teacher_name
                    FROM teacher_weekly_schedule ws
                    JOIN classes  c ON ws.class_id=c.id
                    JOIN subjects s ON ws.subject_id=s.id
                    JOIN teachers t ON ws.teacher_id=t.id
                    WHERE ws.school_id=%s ORDER BY ws.weekday, ws.start_time
                """, (school_id,))
            return []

    def get_slot(self, slot_id):
        with self.conn() as conn:
            return self._fetchone(conn, """
                SELECT ws.*, c.name AS class_name, s.name AS subject_name,
                       t.full_name AS teacher_name
                FROM teacher_weekly_schedule ws
                JOIN classes  c ON ws.class_id=c.id
                JOIN subjects s ON ws.subject_id=s.id
                JOIN teachers t ON ws.teacher_id=t.id
                WHERE ws.id=%s
            """, (slot_id,))

    def update_slot_time(self, slot_id, start_time, end_time):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE teacher_weekly_schedule SET start_time=%s, end_time=%s WHERE id=%s",
                    (start_time, end_time, slot_id))
            conn.commit()

    def delete_slot(self, slot_id):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM teacher_weekly_schedule WHERE id=%s", (slot_id,))
            conn.commit()

    def get_teacher_class_subject_dates(self, teacher_id, class_id, subject_id,
                                         days_back=21, days_forward=7) -> list:
        import datetime
        with self.conn() as conn:
            slots = self._fetchall(conn, """
                SELECT weekday, start_time, end_time
                FROM teacher_weekly_schedule
                WHERE teacher_id=%s AND class_id=%s AND subject_id=%s
                ORDER BY weekday
            """, (teacher_id, class_id, subject_id))

        if not slots:
            return []

        lesson_weekdays = {s['weekday']: s for s in slots}
        today = datetime.date.today()
        today_wd = today.weekday()
        result = []

        if today_wd in lesson_weekdays:
            slot = lesson_weekdays[today_wd]
            result.append({
                'date': today.isoformat(), 'weekday': today_wd,
                'start_time': slot['start_time'] or '',
                'end_time':   slot['end_time']   or '',
            })

        past = []
        for delta in range(1, 90):
            d  = today - datetime.timedelta(days=delta)
            wd = d.weekday()
            if wd in lesson_weekdays:
                slot = lesson_weekdays[wd]
                past.append({
                    'date': d.isoformat(), 'weekday': wd,
                    'start_time': slot['start_time'] or '',
                    'end_time':   slot['end_time']   or '',
                })
            if len(past) == 2:
                break

        result.extend(past)
        return result

    def get_today_teachers(self, school_id, weekday) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT DISTINCT t.id, t.full_name,
                    STRING_AGG(c.name || ' - ' || s.name, ', ') AS schedule_info
                FROM teacher_weekly_schedule ws
                JOIN teachers t ON ws.teacher_id=t.id
                JOIN classes  c ON ws.class_id=c.id
                JOIN subjects s ON ws.subject_id=s.id
                WHERE ws.school_id=%s AND ws.weekday=%s
                GROUP BY t.id, t.full_name ORDER BY t.full_name
            """, (school_id, weekday))
