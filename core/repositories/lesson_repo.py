"""
core/repositories/lesson_repo.py — PostgreSQL versiyasi
"""
import psycopg2.extras
from core.database import BaseDB


class LessonRepo(BaseDB):

    def _fetchone(self, conn, q, p=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(q, p); return cur.fetchone()

    def _fetchall(self, conn, q, p=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(q, p); return cur.fetchall() or []

    def save_lesson(self, teacher_id, class_id, subject_id, date,
                    content_type, content=None, file_id=None, file_type=None) -> int:
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO lessons
                        (teacher_id, class_id, subject_id, date,
                         content_type, content, file_id, file_type)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """, (teacher_id, class_id, subject_id, date,
                      content_type, content, file_id, file_type))
                row = cur.fetchone()
            conn.commit()
            return row[0]

    def add_lesson_file(self, lesson_id, file_id, file_type):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO lesson_files (lesson_id, file_id, file_type) VALUES (%s,%s,%s)",
                    (lesson_id, file_id, file_type))
            conn.commit()

    def get_lessons(self, class_id, subject_id, date, content_type) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT l.*, t.full_name AS teacher_name
                FROM lessons l JOIN teachers t ON l.teacher_id=t.id
                WHERE l.class_id=%s AND l.subject_id=%s AND l.date=%s AND l.content_type=%s
                ORDER BY l.created_at DESC
            """, (class_id, subject_id, date, content_type))

    def get_lesson_files(self, lesson_id) -> list:
        with self.conn() as conn:
            return self._fetchall(conn,
                "SELECT * FROM lesson_files WHERE lesson_id=%s", (lesson_id,))

    def get_all_lessons_for_class(self, class_id, subject_id) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT * FROM lessons WHERE class_id=%s AND subject_id=%s
                ORDER BY date DESC, created_at DESC
            """, (class_id, subject_id))

    def get_lesson(self, lesson_id: int):
        with self.conn() as conn:
            row = self._fetchone(conn, """
                SELECT l.*, t.full_name AS teacher_name,
                       c.name AS class_name, s.name AS subject_name
                FROM lessons l
                JOIN teachers t ON l.teacher_id = t.id
                JOIN classes  c ON l.class_id   = c.id
                JOIN subjects s ON l.subject_id  = s.id
                WHERE l.id = %s
            """, (lesson_id,))
            if row is None:
                return None
            d = dict(row)
            d.setdefault('deadline', None)
            d.setdefault('comment',  None)
            return d

    def get_lessons_by_teacher_class_subject(self, teacher_id, class_id,
                                              subject_id, content_type=None) -> list:
        with self.conn() as conn:
            q = """
                SELECT l.*, c.name AS class_name, s.name AS subject_name
                FROM lessons l
                JOIN classes  c ON l.class_id  = c.id
                JOIN subjects s ON l.subject_id = s.id
                WHERE l.teacher_id=%s AND l.class_id=%s AND l.subject_id=%s
            """
            params = [teacher_id, class_id, subject_id]
            if content_type:
                q += " AND l.content_type=%s"
                params.append(content_type)
            q += " ORDER BY l.date DESC, l.created_at DESC"
            return self._fetchall(conn, q, params)

    def get_lessons_by_teacher_date(self, teacher_id, date, content_type=None) -> list:
        with self.conn() as conn:
            if content_type:
                return self._fetchall(conn, """
                    SELECT l.*, c.name AS class_name, s.name AS subject_name
                    FROM lessons l
                    JOIN classes  c ON l.class_id  = c.id
                    JOIN subjects s ON l.subject_id = s.id
                    WHERE l.teacher_id=%s AND l.date=%s AND l.content_type=%s
                    ORDER BY l.class_id, l.subject_id
                """, (teacher_id, date, content_type))
            return self._fetchall(conn, """
                SELECT l.*, c.name AS class_name, s.name AS subject_name
                FROM lessons l
                JOIN classes  c ON l.class_id  = c.id
                JOIN subjects s ON l.subject_id = s.id
                WHERE l.teacher_id=%s AND l.date=%s
                ORDER BY l.content_type, l.class_id, l.subject_id
            """, (teacher_id, date))

    def update_lesson_content(self, lesson_id, content):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE lessons SET content=%s WHERE id=%s", (content, lesson_id))
            conn.commit()

    def update_lesson_deadline(self, lesson_id, deadline):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE lessons SET deadline=%s WHERE id=%s", (deadline, lesson_id))
            conn.commit()

    def update_lesson_comment(self, lesson_id, comment):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE lessons SET comment=%s WHERE id=%s", (comment, lesson_id))
            conn.commit()

    def replace_lesson_main_file(self, lesson_id, file_id, file_type):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE lessons SET file_id=%s, file_type=%s WHERE id=%s",
                    (file_id, file_type, lesson_id))
                cur.execute("DELETE FROM lesson_files WHERE lesson_id=%s", (lesson_id,))
            conn.commit()

    def delete_lesson(self, lesson_id):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM lessons WHERE id=%s", (lesson_id,))
            conn.commit()

    def save_schedule(self, school_id, file_id, file_type="photo", class_id=None) -> int:
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO schedules (school_id, class_id, file_id, file_type)
                    VALUES (%s,%s,%s,%s) RETURNING id
                """, (school_id, class_id, file_id, file_type))
                row = cur.fetchone()
            conn.commit()
            return row[0]

    def get_schedule(self, school_id, class_id=None):
        with self.conn() as conn:
            if class_id:
                row = self._fetchone(conn, """
                    SELECT * FROM schedules WHERE school_id=%s AND class_id=%s
                    ORDER BY uploaded_at DESC LIMIT 1
                """, (school_id, class_id))
                if row:
                    return row
            return self._fetchone(conn, """
                SELECT * FROM schedules WHERE school_id=%s AND class_id IS NULL
                ORDER BY uploaded_at DESC LIMIT 1
            """, (school_id,))

    # ── Topshirmalar ─────────────────────────────────────────────

    def save_submission(self, student_id, subject_id, class_id,
                        date, content=None, file_id=None,
                        file_type="text", lesson_id=None) -> int:
        with self.conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if lesson_id:
                    cur.execute("SELECT id FROM submissions WHERE student_id=%s AND lesson_id=%s",
                                (student_id, lesson_id))
                else:
                    cur.execute("SELECT id FROM submissions WHERE student_id=%s AND subject_id=%s AND date=%s",
                                (student_id, subject_id, date))
                old_rows = cur.fetchall()
                for row in old_rows:
                    cur.execute("DELETE FROM submission_files WHERE submission_id=%s", (row['id'],))
                if lesson_id:
                    cur.execute("DELETE FROM submissions WHERE student_id=%s AND lesson_id=%s",
                                (student_id, lesson_id))
                else:
                    cur.execute("DELETE FROM submissions WHERE student_id=%s AND subject_id=%s AND date=%s",
                                (student_id, subject_id, date))
                cur.execute("""
                    INSERT INTO submissions
                        (student_id, subject_id, class_id, lesson_id, date, content, file_id, file_type)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """, (student_id, subject_id, class_id, lesson_id, date, content, file_id, file_type))
                row = cur.fetchone()
            conn.commit()
            return row['id']

    def add_submission_file(self, submission_id, file_id, file_type):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO submission_files (submission_id, file_id, file_type) VALUES (%s,%s,%s)",
                    (submission_id, file_id, file_type))
            conn.commit()

    def get_submissions(self, class_id=None, subject_id=None,
                        date=None, student_id=None) -> list:
        where, params = [], []
        if class_id:   where.append("s.class_id=%s");   params.append(class_id)
        if subject_id: where.append("s.subject_id=%s"); params.append(subject_id)
        if date:       where.append("s.date=%s");       params.append(date)
        if student_id: where.append("s.student_id=%s"); params.append(student_id)
        q = """
            SELECT s.*, w.full_name AS student_name, sub.name AS subject_name
            FROM submissions s
            JOIN whitelist w  ON s.student_id = w.telegram_id
            JOIN subjects sub ON s.subject_id  = sub.id
        """
        if where:
            q += " WHERE " + " AND ".join(where)
        q += " ORDER BY s.submitted_at DESC"
        with self.conn() as conn:
            return self._fetchall(conn, q, params)

    def get_homework_dates(self, class_id) -> list:
        with self.conn() as conn:
            rows = self._fetchall(conn, """
                SELECT date, MAX(deadline) AS deadline
                FROM lessons WHERE class_id=%s AND content_type='homework'
                GROUP BY date ORDER BY date DESC
            """, (class_id,))
            return [{'date': r['date'], 'deadline': r['deadline']} for r in rows]

    def get_topic_dates(self, class_id) -> list:
        with self.conn() as conn:
            rows = self._fetchall(conn, """
                SELECT DISTINCT date FROM lessons
                WHERE class_id=%s AND content_type='topic' ORDER BY date DESC
            """, (class_id,))
            return [r['date'] for r in rows]

    def get_topics_for_class(self, class_id) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT l.id, l.content, l.date, l.file_id, l.file_type,
                       s.name AS subject_name
                FROM lessons l JOIN subjects s ON l.subject_id = s.id
                WHERE l.class_id=%s AND l.content_type='topic'
                ORDER BY l.date DESC, l.created_at DESC
            """, (class_id,))

    def count_submissions(self, class_id=None, subject_id=None, date=None) -> int:
        where, params = [], []
        if class_id:   where.append("class_id=%s");   params.append(class_id)
        if subject_id: where.append("subject_id=%s"); params.append(subject_id)
        if date:       where.append("date=%s");       params.append(date)
        q = "SELECT COUNT(*) FROM submissions"
        if where:
            q += " WHERE " + " AND ".join(where)
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute(q, params)
                return cur.fetchone()[0]

    def get_submission_files(self, submission_id) -> list:
        with self.conn() as conn:
            return self._fetchall(conn,
                "SELECT * FROM submission_files WHERE submission_id=%s", (submission_id,))

    def get_student_submission(self, student_id, subject_id, date, lesson_id=None):
        with self.conn() as conn:
            if lesson_id:
                return self._fetchone(conn, """
                    SELECT * FROM submissions WHERE student_id=%s AND lesson_id=%s
                    ORDER BY submitted_at DESC LIMIT 1
                """, (student_id, lesson_id))
            return self._fetchone(conn, """
                SELECT * FROM submissions WHERE student_id=%s AND subject_id=%s AND date=%s
                ORDER BY submitted_at DESC LIMIT 1
            """, (student_id, subject_id, date))

    def get_homework_subjects_for_date(self, class_id, date) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT s.id AS subject_id, s.name AS subject_name,
                       MAX(l.deadline) AS deadline
                FROM lessons l JOIN subjects s ON l.subject_id = s.id
                WHERE l.class_id=%s AND l.date=%s AND l.content_type='homework'
                GROUP BY s.id, s.name ORDER BY s.name
            """, (class_id, date))

    def get_all_teacher_homeworks(self, teacher_id) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT l.id, l.date, l.content, l.file_id, l.file_type,
                       l.subject_id, l.class_id,
                       s.name AS subject_name, cl.name AS class_name
                FROM lessons l
                JOIN subjects s  ON l.subject_id = s.id
                JOIN classes  cl ON l.class_id   = cl.id
                WHERE l.teacher_id=%s AND l.content_type='homework'
                ORDER BY l.date DESC, l.created_at DESC
            """, (teacher_id,))

    def get_all_homeworks_for_class(self, class_id) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT l.id, l.content, l.date, l.deadline,
                       l.file_id, l.file_type, l.subject_id,
                       s.name AS subject_name
                FROM lessons l JOIN subjects s ON l.subject_id = s.id
                WHERE l.class_id=%s AND l.content_type='homework'
                ORDER BY l.date DESC, l.created_at DESC
            """, (class_id,))
