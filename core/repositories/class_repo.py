"""
core/repositories/class_repo.py — PostgreSQL versiyasi
"""
import psycopg2.extras
from core.database import BaseDB


class ClassRepo(BaseDB):

    def _fetchone(self, conn, q, p=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(q, p); return cur.fetchone()

    def _fetchall(self, conn, q, p=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(q, p); return cur.fetchall() or []

    # ── Sinflar ──────────────────────────────────────────────────

    def get_classes(self, school_id: int) -> list:
        with self.conn() as conn:
            return self._fetchall(conn,
                "SELECT * FROM classes WHERE school_id=%s ORDER BY name", (school_id,))

    def get_class(self, class_id: int):
        with self.conn() as conn:
            return self._fetchone(conn, "SELECT * FROM classes WHERE id=%s", (class_id,))

    def add_class(self, name: str, school_id: int) -> int:
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO classes (name, school_id) VALUES (%s, %s)
                    ON CONFLICT (name, school_id) DO NOTHING RETURNING id
                """, (name, school_id))
                row = cur.fetchone()
            conn.commit()
            return row[0] if row else None

    def delete_class(self, class_id: int):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM classes WHERE id=%s", (class_id,))
            conn.commit()

    # ── Fanlar ───────────────────────────────────────────────────

    def get_subjects(self, school_id: int = None, class_id: int = None) -> list:
        with self.conn() as conn:
            if class_id:
                return self._fetchall(conn, """
                    SELECT s.*
                    FROM subjects s
                    JOIN subject_assignments sa ON sa.subject_id = s.id
                    WHERE sa.class_id = %s ORDER BY s.name
                """, (class_id,))
            if school_id:
                return self._fetchall(conn,
                    "SELECT * FROM subjects WHERE school_id=%s ORDER BY name", (school_id,))
            return self._fetchall(conn, "SELECT * FROM subjects ORDER BY name")

    def get_subject(self, subject_id: int):
        with self.conn() as conn:
            return self._fetchone(conn, "SELECT * FROM subjects WHERE id=%s", (subject_id,))

    def add_subject(self, name: str, school_id: int, class_id: int = None) -> int:
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO subjects (name, school_id) VALUES (%s, %s)
                    ON CONFLICT (name, school_id) DO NOTHING RETURNING id
                """, (name, school_id))
                row = cur.fetchone()
                if row:
                    subject_id = row[0]
                else:
                    cur.execute("SELECT id FROM subjects WHERE name=%s AND school_id=%s",
                                (name, school_id))
                    r = cur.fetchone()
                    subject_id = r[0] if r else None
                if subject_id and class_id:
                    cur.execute("""
                        INSERT INTO subject_assignments (subject_id, class_id)
                        VALUES (%s, %s)
                        ON CONFLICT (subject_id, class_id) DO NOTHING
                    """, (subject_id, class_id))
            conn.commit()
            return subject_id

    def delete_subject(self, subject_id: int):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM subjects WHERE id=%s", (subject_id,))
            conn.commit()

    # ── Fan ↔ Sinf biriktirish ───────────────────────────────────

    def is_subject_assigned(self, subject_id: int, class_id: int) -> bool:
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM subject_assignments WHERE subject_id=%s AND class_id=%s",
                    (subject_id, class_id))
                return cur.fetchone() is not None

    def assign_subject_to_class(self, subject_id: int, class_id: int,
                                 school_id: int = None) -> bool:
        try:
            with self.conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO subject_assignments (subject_id, class_id)
                        VALUES (%s, %s)
                        ON CONFLICT (subject_id, class_id) DO NOTHING
                    """, (subject_id, class_id))
                conn.commit()
            return True
        except Exception:
            return False

    def unassign_subject_from_class(self, subject_id: int, class_id: int):
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM subject_assignments WHERE subject_id=%s AND class_id=%s",
                    (subject_id, class_id))
            conn.commit()

    def get_subject_classes(self, subject_id: int) -> list:
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT c.*
                FROM classes c
                JOIN subject_assignments sa ON sa.class_id = c.id
                WHERE sa.subject_id = %s ORDER BY c.name
            """, (subject_id,))

    def assign_subject(self, name: str, class_id: int, school_id: int) -> int:
        subj_id = self.add_subject(name, school_id)
        if subj_id:
            self.assign_subject_to_class(subj_id, class_id, school_id)
        return subj_id
