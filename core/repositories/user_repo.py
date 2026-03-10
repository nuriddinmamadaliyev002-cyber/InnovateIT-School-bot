"""
core/repositories/user_repo.py — PostgreSQL versiyasi
"""
import psycopg2.extras
from core.database import BaseDB


class UserRepo(BaseDB):

    def _fetchone(self, conn, query, params=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def _fetchall(self, conn, query, params=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall() or []

    # ── Telegram foydalanuvchilar ────────────────────────────────

    def add_user(self, telegram_id: int, username: str, first_name: str):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (telegram_id, username, first_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (telegram_id) DO NOTHING
                """, (telegram_id, username, first_name))
            conn.commit()

    # ── O'quvchilar (whitelist) ──────────────────────────────────

    def get_whitelist_user(self, telegram_id: int):
        with self.conn() as conn:
            return self._fetchone(conn, """
                SELECT w.*, c.name AS class_name, s.name AS school_name
                FROM whitelist w
                JOIN classes c ON w.class_id = c.id
                JOIN schools s ON w.school_id = s.id
                WHERE w.telegram_id = %s
            """, (telegram_id,))

    def get_whitelist_by_class(self, class_id: int) -> list:
        with self.conn() as conn:
            return self._fetchall(conn,
                "SELECT * FROM whitelist WHERE class_id=%s AND is_active=1 ORDER BY full_name",
                (class_id,))

    def get_whitelist_by_school(self, school_id: int) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT w.*, c.name AS class_name
                FROM whitelist w JOIN classes c ON w.class_id=c.id
                WHERE w.school_id=%s AND w.is_active=1 ORDER BY c.name, w.full_name
            """, (school_id,))

    def add_student(self, telegram_id: int, full_name: str,
                    class_id: int, school_id: int) -> bool:
        try:
            with self.conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO whitelist (telegram_id, full_name, class_id, school_id)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (telegram_id) DO NOTHING
                    """, (telegram_id, full_name, class_id, school_id))
                conn.commit()
            return True
        except Exception:
            return False

    # ── Arxiv tizimi ─────────────────────────────────────────────

    def rename_student(self, telegram_id: int, new_name: str) -> bool:
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE whitelist SET full_name=%s WHERE telegram_id=%s",
                    (new_name, telegram_id)
                )
            conn.commit()
        return True

    def archive_student(self, telegram_id: int) -> bool:
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE whitelist SET is_active=0 WHERE telegram_id=%s", (telegram_id,))
            conn.commit()
        return True

    def restore_student(self, telegram_id: int) -> bool:
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE whitelist SET is_active=1 WHERE telegram_id=%s", (telegram_id,))
            conn.commit()
        return True

    def get_archived_students(self, school_id: int) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT w.*, c.name AS class_name
                FROM whitelist w JOIN classes c ON w.class_id=c.id
                WHERE w.school_id=%s AND w.is_active=0
                ORDER BY c.name, w.full_name
            """, (school_id,))

    def rename_teacher(self, teacher_id: int, new_name: str) -> bool:
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE teachers SET full_name=%s WHERE id=%s",
                    (new_name, teacher_id)
                )
            conn.commit()
        return True

    def archive_teacher(self, teacher_id: int) -> bool:
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE teachers SET is_active=0 WHERE id=%s", (teacher_id,))
            conn.commit()
        return True

    def restore_teacher(self, teacher_id: int) -> bool:
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE teachers SET is_active=1 WHERE id=%s", (teacher_id,))
            conn.commit()
        return True

    def get_archived_teachers(self, school_id: int) -> list:
        with self.conn() as conn:
            return self._fetchall(conn,
                "SELECT * FROM teachers WHERE school_id=%s AND is_active=0 ORDER BY full_name",
                (school_id,))

    def get_teacher_by_id_any(self, teacher_id: int):
        with self.conn() as conn:
            return self._fetchone(conn, "SELECT * FROM teachers WHERE id=%s", (teacher_id,))

    def get_teacher_any(self, telegram_id: int):
        """Arxivlangan bo'lsa ham o'qituvchini oladi"""
        with self.conn() as conn:
            return self._fetchone(conn, """
                SELECT t.*, s.name AS school_name
                FROM teachers t JOIN schools s ON t.school_id=s.id
                WHERE t.telegram_id=%s
            """, (telegram_id,))

    def get_whitelist_user_any(self, telegram_id: int):
        with self.conn() as conn:
            return self._fetchone(conn, """
                SELECT w.*, c.name AS class_name, s.name AS school_name
                FROM whitelist w
                JOIN classes c ON w.class_id = c.id
                JOIN schools s ON w.school_id = s.id
                WHERE w.telegram_id = %s
            """, (telegram_id,))

    def delete_student(self, telegram_id: int):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM submission_files
                    WHERE submission_id IN (
                        SELECT id FROM submissions WHERE student_id=%s
                    )
                """, (telegram_id,))
                cur.execute("DELETE FROM submissions WHERE student_id=%s", (telegram_id,))
                cur.execute("DELETE FROM attendance WHERE student_id=%s", (telegram_id,))
                cur.execute("DELETE FROM grades WHERE student_id=%s", (telegram_id,))
                cur.execute("DELETE FROM student_parents WHERE student_telegram_id=%s", (telegram_id,))
                cur.execute("DELETE FROM whitelist WHERE telegram_id=%s", (telegram_id,))
            conn.commit()

    # ── O'qituvchilar ────────────────────────────────────────────

    def get_teacher(self, telegram_id: int):
        with self.conn() as conn:
            return self._fetchone(conn, """
                SELECT t.*, s.name AS school_name
                FROM teachers t JOIN schools s ON t.school_id=s.id
                WHERE t.telegram_id=%s
            """, (telegram_id,))

    def get_teachers_by_telegram_id(self, telegram_id: int):
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT t.*, s.name AS school_name
                FROM teachers t JOIN schools s ON t.school_id=s.id
                WHERE t.telegram_id=%s AND t.is_active=1
                ORDER BY s.name
            """, (telegram_id,))

    def get_teacher_with_school(self, telegram_id: int, school_id: int):
        with self.conn() as conn:
            return self._fetchone(conn, """
                SELECT t.*, s.name AS school_name
                FROM teachers t JOIN schools s ON t.school_id=s.id
                WHERE t.telegram_id=%s AND t.school_id=%s
            """, (telegram_id, school_id))

    def get_teacher_by_id(self, teacher_id: int):
        with self.conn() as conn:
            return self._fetchone(conn,
                "SELECT * FROM teachers WHERE id=%s", (teacher_id,))

    def get_teachers_by_school(self, school_id: int) -> list:
        with self.conn() as conn:
            return self._fetchall(conn,
                "SELECT * FROM teachers WHERE school_id=%s AND is_active=1 ORDER BY full_name",
                (school_id,))

    def add_teacher(self, telegram_id: int, school_id: int, full_name: str) -> int:
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO teachers (telegram_id, school_id, full_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (telegram_id) DO NOTHING
                    RETURNING id
                """, (telegram_id, school_id, full_name))
                row = cur.fetchone()
            conn.commit()
            return row[0] if row else None

    def delete_teacher(self, teacher_id: int):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM lesson_files
                    WHERE lesson_id IN (SELECT id FROM lessons WHERE teacher_id=%s)
                """, (teacher_id,))
                cur.execute("""
                    DELETE FROM submission_files
                    WHERE submission_id IN (
                        SELECT s.id FROM submissions s
                        JOIN lessons l ON s.lesson_id = l.id
                        WHERE l.teacher_id=%s
                    )
                """, (teacher_id,))
                cur.execute("""
                    DELETE FROM submissions
                    WHERE lesson_id IN (SELECT id FROM lessons WHERE teacher_id=%s)
                """, (teacher_id,))
                cur.execute("DELETE FROM lessons WHERE teacher_id=%s", (teacher_id,))
                cur.execute("DELETE FROM grades WHERE teacher_id=%s", (teacher_id,))
                cur.execute("DELETE FROM teacher_attendance WHERE teacher_id=%s", (teacher_id,))
                cur.execute("DELETE FROM teacher_weekly_schedule WHERE teacher_id=%s", (teacher_id,))
                cur.execute("DELETE FROM teacher_assignments WHERE teacher_id=%s", (teacher_id,))
                cur.execute("DELETE FROM teachers WHERE id=%s", (teacher_id,))
            conn.commit()

    # ── O'qituvchi-sinf-fan biriktirish ─────────────────────────

    def get_teacher_assignments(self, teacher_id: int) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT ta.*, c.name AS class_name, s.name AS subject_name
                FROM teacher_assignments ta
                JOIN classes  c ON ta.class_id   = c.id
                JOIN subjects s ON ta.subject_id  = s.id
                WHERE ta.teacher_id = %s
            """, (teacher_id,))

    def assign_teacher(self, teacher_id: int, class_id: int, subject_id: int) -> bool:
        try:
            with self.conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO teacher_assignments (teacher_id, class_id, subject_id)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (teacher_id, class_id, subject_id) DO NOTHING
                    """, (teacher_id, class_id, subject_id))
                conn.commit()
            return True
        except Exception:
            return False

    def remove_assignment(self, assignment_id: int):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM teacher_assignments WHERE id=%s", (assignment_id,))
            conn.commit()

    def get_teacher_classes(self, teacher_id: int) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT DISTINCT c.id, c.name
                FROM teacher_assignments ta JOIN classes c ON ta.class_id=c.id
                WHERE ta.teacher_id=%s ORDER BY c.name
            """, (teacher_id,))

    def get_teacher_subjects_for_class(self, teacher_id: int, class_id: int) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT DISTINCT s.id, s.name
                FROM teacher_assignments ta JOIN subjects s ON ta.subject_id=s.id
                WHERE ta.teacher_id=%s AND ta.class_id=%s ORDER BY s.name
            """, (teacher_id, class_id))

    def get_teachers_by_subject_class(self, subject_id: int, class_id: int) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT DISTINCT t.id, t.full_name, t.telegram_id
                FROM teacher_assignments ta
                JOIN teachers t ON ta.teacher_id = t.id
                WHERE ta.subject_id=%s AND ta.class_id=%s ORDER BY t.full_name
            """, (subject_id, class_id))

    def remove_teacher_from_subject_class(self, teacher_id: int, class_id: int, subject_id: int):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM teacher_assignments
                    WHERE teacher_id=%s AND class_id=%s AND subject_id=%s
                """, (teacher_id, class_id, subject_id))
            conn.commit()

    def update_student_telegram_id(self, old_id: int, new_id: int) -> bool:
        with self.conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT telegram_id FROM whitelist WHERE telegram_id=%s", (new_id,))
                if cur.fetchone():
                    return False
                cur.execute("UPDATE attendance  SET student_id=%s WHERE student_id=%s", (new_id, old_id))
                cur.execute("UPDATE grades      SET student_id=%s WHERE student_id=%s", (new_id, old_id))
                cur.execute("UPDATE submissions SET student_id=%s WHERE student_id=%s", (new_id, old_id))
                cur.execute("UPDATE whitelist   SET telegram_id=%s WHERE telegram_id=%s", (new_id, old_id))
            conn.commit()
        return True

    def update_teacher_telegram_id(self, old_id: int, new_id: int) -> bool:
        with self.conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT id FROM teachers WHERE telegram_id=%s", (new_id,))
                if cur.fetchone():
                    return False
                cur.execute("UPDATE teachers SET telegram_id=%s WHERE telegram_id=%s", (new_id, old_id))
            conn.commit()
        return True