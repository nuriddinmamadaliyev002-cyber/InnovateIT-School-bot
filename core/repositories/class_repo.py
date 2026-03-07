"""
core/repositories/class_repo.py — Sinflar va fanlar operatsiyalari

Fanlar endi school-level — sinfga biriktirish subject_assignments orqali.
"""
from core.database import BaseDB


class ClassRepo(BaseDB):

    # ── Sinflar ──────────────────────────────────────────────────

    def get_classes(self, school_id: int) -> list:
        with self.conn() as c:
            return c.execute(
                "SELECT * FROM classes WHERE school_id=? ORDER BY name", (school_id,)
            ).fetchall()

    def get_class(self, class_id: int):
        with self.conn() as c:
            return c.execute("SELECT * FROM classes WHERE id=?", (class_id,)).fetchone()

    def add_class(self, name: str, school_id: int) -> int:
        with self.conn() as c:
            cur = c.execute(
                "INSERT OR IGNORE INTO classes (name, school_id) VALUES (?,?)", (name, school_id)
            )
            return cur.lastrowid

    def delete_class(self, class_id: int):
        with self.conn() as c:
            c.execute("DELETE FROM classes WHERE id=?", (class_id,))

    # ── Fanlar (school-level) ────────────────────────────────────

    def get_subjects(self, school_id: int = None, class_id: int = None) -> list:
        """
        class_id berilsa  → o'sha sinfga biriktirilgan fanlar
        school_id berilsa → maktabdagi barcha fanlar
        ikkalasi ham yo'q  → hamma fanlar
        """
        with self.conn() as c:
            if class_id:
                return c.execute("""
                    SELECT s.*
                    FROM subjects s
                    JOIN subject_assignments sa ON sa.subject_id = s.id
                    WHERE sa.class_id = ?
                    ORDER BY s.name
                """, (class_id,)).fetchall()
            if school_id:
                return c.execute(
                    "SELECT * FROM subjects WHERE school_id=? ORDER BY name", (school_id,)
                ).fetchall()
            return c.execute("SELECT * FROM subjects ORDER BY name").fetchall()

    def get_subject(self, subject_id: int):
        with self.conn() as c:
            return c.execute("SELECT * FROM subjects WHERE id=?", (subject_id,)).fetchone()

    def add_subject(self, name: str, school_id: int, class_id: int = None) -> int:
        """
        Fanni maktab darajasida yaratadi.
        class_id berilsa — shu sinfga ham biriktiradi.
        """
        with self.conn() as c:
            cur = c.execute(
                "INSERT OR IGNORE INTO subjects (name, school_id) VALUES (?,?)",
                (name, school_id)
            )
            subject_id = cur.lastrowid
            if not subject_id:
                # Allaqachon bor — ID ni ol
                row = c.execute(
                    "SELECT id FROM subjects WHERE name=? AND school_id=?",
                    (name, school_id)
                ).fetchone()
                subject_id = row['id'] if row else None
            if subject_id and class_id:
                c.execute(
                    "INSERT OR IGNORE INTO subject_assignments (subject_id, class_id) VALUES (?,?)",
                    (subject_id, class_id)
                )
            return subject_id

    def delete_subject(self, subject_id: int):
        with self.conn() as c:
            c.execute("DELETE FROM subjects WHERE id=?", (subject_id,))

    # ── Fan ↔ Sinf biriktirish ───────────────────────────────────

    def is_subject_assigned(self, subject_id: int, class_id: int) -> bool:
        with self.conn() as c:
            row = c.execute(
                "SELECT id FROM subject_assignments WHERE subject_id=? AND class_id=?",
                (subject_id, class_id)
            ).fetchone()
            return row is not None

    def assign_subject_to_class(self, subject_id: int, class_id: int,
                                 school_id: int = None) -> bool:
        with self.conn() as c:
            try:
                c.execute(
                    "INSERT OR IGNORE INTO subject_assignments (subject_id, class_id) VALUES (?,?)",
                    (subject_id, class_id)
                )
                return True
            except Exception:
                return False

    def unassign_subject_from_class(self, subject_id: int, class_id: int):
        with self.conn() as c:
            c.execute(
                "DELETE FROM subject_assignments WHERE subject_id=? AND class_id=?",
                (subject_id, class_id)
            )

    def get_subject_classes(self, subject_id: int) -> list:
        """Fan biriktirilgan sinflar ro'yxati"""
        with self.conn() as c:
            return c.execute("""
                SELECT c.*
                FROM classes c
                JOIN subject_assignments sa ON sa.class_id = c.id
                WHERE sa.subject_id = ?
                ORDER BY c.name
            """, (subject_id,)).fetchall()

    # ── (Eski kod uchun qoldirilgan) Fan → Sinf biriktirish ──────

    def assign_subject(self, name: str, class_id: int, school_id: int) -> int:
        """Fanni sinfga biriktirish (eski API uchun)"""
        subj_id = self.add_subject(name, school_id)
        if subj_id:
            self.assign_subject_to_class(subj_id, class_id, school_id)
        return subj_id