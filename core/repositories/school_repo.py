"""
core/repositories/school_repo.py — Maktab va admin operatsiyalari
"""
from core.database import BaseDB


class SchoolRepo(BaseDB):

    # ── Maktablar ────────────────────────────────────────────────

    def get_schools(self) -> list:
        with self.conn() as c:
            return c.execute("SELECT * FROM schools ORDER BY name").fetchall()

    def get_school(self, school_id: int):
        with self.conn() as c:
            return c.execute("SELECT * FROM schools WHERE id=?", (school_id,)).fetchone()

    def add_school(self, name: str, address: str = "") -> int:
        with self.conn() as c:
            cur = c.execute(
                "INSERT OR IGNORE INTO schools (name, address) VALUES (?,?)", (name, address)
            )
            return cur.lastrowid

    def delete_school(self, school_id: int):
        with self.conn() as c:
            c.execute("DELETE FROM schools WHERE id=?", (school_id,))

    def get_school_stats(self, school_id: int) -> dict:
        with self.conn() as c:
            students = c.execute(
                "SELECT COUNT(*) FROM whitelist WHERE school_id=?", (school_id,)
            ).fetchone()[0]
            teachers = c.execute(
                "SELECT COUNT(*) FROM teachers WHERE school_id=?", (school_id,)
            ).fetchone()[0]
            classes = c.execute(
                "SELECT COUNT(*) FROM classes WHERE school_id=?", (school_id,)
            ).fetchone()[0]
            subjects = c.execute(
                "SELECT COUNT(*) FROM subjects WHERE school_id=?", (school_id,)
            ).fetchone()[0]
        return {"students": students, "teachers": teachers,
                "classes": classes, "subjects": subjects}

    # ── Maktab adminlari ─────────────────────────────────────────

    def get_school_admin(self, telegram_id: int):
        with self.conn() as c:
            return c.execute("""
                SELECT sa.*, s.name AS school_name
                FROM school_admins sa
                JOIN schools s ON sa.school_id = s.id
                WHERE sa.telegram_id = ?
            """, (telegram_id,)).fetchone()

    def get_school_admins(self, school_id: int = None) -> list:
        with self.conn() as c:
            if school_id:
                return c.execute("""
                    SELECT sa.*, s.name AS school_name
                    FROM school_admins sa JOIN schools s ON sa.school_id=s.id
                    WHERE sa.school_id=?
                """, (school_id,)).fetchall()
            return c.execute("""
                SELECT sa.*, s.name AS school_name
                FROM school_admins sa JOIN schools s ON sa.school_id=s.id
            """).fetchall()

    def add_school_admin(self, telegram_id: int, school_id: int, full_name: str) -> int:
        with self.conn() as c:
            cur = c.execute(
                "INSERT OR IGNORE INTO school_admins (telegram_id, school_id, full_name) VALUES (?,?,?)",
                (telegram_id, school_id, full_name)
            )
            return cur.lastrowid

    def is_school_admin(self, telegram_id: int) -> bool:
        with self.conn() as c:
            row = c.execute(
                "SELECT id FROM school_admins WHERE telegram_id=?", (telegram_id,)
            ).fetchone()
            return row is not None

    def delete_school_admin(self, admin_id: int):
        with self.conn() as c:
            c.execute("DELETE FROM school_admins WHERE id=?", (admin_id,))

    def get_global_stats(self) -> dict:
        with self.conn() as c:
            schools  = c.execute("SELECT COUNT(*) FROM schools").fetchone()[0]
            students = c.execute("SELECT COUNT(*) FROM whitelist").fetchone()[0]
            teachers = c.execute("SELECT COUNT(*) FROM teachers").fetchone()[0]
            users    = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        return {"schools": schools, "students": students,
                "teachers": teachers, "users": users}
