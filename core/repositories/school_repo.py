"""
core/repositories/school_repo.py — PostgreSQL versiyasi
"""
import psycopg2.extras
from core.database import BaseDB


class SchoolRepo(BaseDB):

    def _fetchone(self, conn, q, p=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(q, p); return cur.fetchone()

    def _fetchall(self, conn, q, p=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(q, p); return cur.fetchall() or []

    def get_schools(self) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, "SELECT * FROM schools ORDER BY name")

    def get_school(self, school_id: int):
        with self.conn() as conn:
            return self._fetchone(conn, "SELECT * FROM schools WHERE id=%s", (school_id,))

    def add_school(self, name: str, address: str = "") -> int:
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO schools (name, address) VALUES (%s, %s)
                    ON CONFLICT (name) DO NOTHING RETURNING id
                """, (name, address))
                row = cur.fetchone()
            conn.commit()
            return row[0] if row else None

    def delete_school(self, school_id: int):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM schools WHERE id=%s", (school_id,))
            conn.commit()

    def get_school_stats(self, school_id: int) -> dict:
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM whitelist WHERE school_id=%s", (school_id,))
                students = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM teachers WHERE school_id=%s", (school_id,))
                teachers = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM classes WHERE school_id=%s", (school_id,))
                classes = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM subjects WHERE school_id=%s", (school_id,))
                subjects = cur.fetchone()[0]
        return {"students": students, "teachers": teachers,
                "classes": classes, "subjects": subjects}

    def get_school_admin(self, telegram_id: int):
        with self.conn() as conn:
            return self._fetchone(conn, """
                SELECT sa.*, s.name AS school_name
                FROM school_admins sa JOIN schools s ON sa.school_id = s.id
                WHERE sa.telegram_id = %s
            """, (telegram_id,))

    def get_school_admins(self, school_id: int = None) -> list:
        with self.conn() as conn:
            if school_id:
                return self._fetchall(conn, """
                    SELECT sa.*, s.name AS school_name
                    FROM school_admins sa JOIN schools s ON sa.school_id=s.id
                    WHERE sa.school_id=%s
                """, (school_id,))
            return self._fetchall(conn, """
                SELECT sa.*, s.name AS school_name
                FROM school_admins sa JOIN schools s ON sa.school_id=s.id
            """)

    def add_school_admin(self, telegram_id: int, school_id: int, full_name: str) -> int:
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO school_admins (telegram_id, school_id, full_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (telegram_id, school_id) DO NOTHING RETURNING id
                """, (telegram_id, school_id, full_name))
                row = cur.fetchone()
            conn.commit()
            return row[0] if row else None

    def is_school_admin(self, telegram_id: int) -> bool:
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM school_admins WHERE telegram_id=%s", (telegram_id,))
                return cur.fetchone() is not None

    def delete_school_admin(self, admin_id: int):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM school_admins WHERE id=%s", (admin_id,))
            conn.commit()

    def rename_school(self, school_id: int, new_name: str):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE schools SET name=%s WHERE id=%s", (new_name, school_id))
            conn.commit()
