"""
core/repositories/user_repo.py — Foydalanuvchilar, o'quvchilar, o'qituvchilar
"""
from core.database import BaseDB


class UserRepo(BaseDB):

    # ── Telegram foydalanuvchilar (statistika) ───────────────────

    def add_user(self, telegram_id: int, username: str, first_name: str):
        with self.conn() as c:
            c.execute("""
                INSERT OR IGNORE INTO users (telegram_id, username, first_name)
                VALUES (?,?,?)
            """, (telegram_id, username, first_name))

    # ── O'quvchilar (whitelist) ──────────────────────────────────

    def get_whitelist_user(self, telegram_id: int):
        with self.conn() as c:
            return c.execute("""
                SELECT w.*, c.name AS class_name, s.name AS school_name
                FROM whitelist w
                JOIN classes c ON w.class_id = c.id
                JOIN schools s ON w.school_id = s.id
                WHERE w.telegram_id = ?
            """, (telegram_id,)).fetchone()

    def get_whitelist_by_class(self, class_id: int) -> list:
        with self.conn() as c:
            return c.execute(
                "SELECT * FROM whitelist WHERE class_id=? AND is_active=1 ORDER BY full_name", (class_id,)
            ).fetchall()

    def get_whitelist_by_school(self, school_id: int) -> list:
        with self.conn() as c:
            return c.execute("""
                SELECT w.*, c.name AS class_name
                FROM whitelist w JOIN classes c ON w.class_id=c.id
                WHERE w.school_id=? AND w.is_active=1 ORDER BY c.name, w.full_name
            """, (school_id,)).fetchall()

    def add_student(self, telegram_id: int, full_name: str,
                    class_id: int, school_id: int) -> bool:
        with self.conn() as c:
            try:
                c.execute("""
                    INSERT OR IGNORE INTO whitelist (telegram_id, full_name, class_id, school_id)
                    VALUES (?,?,?,?)
                """, (telegram_id, full_name, class_id, school_id))
                return True
            except Exception:
                return False


    # ── Arxiv tizimi (O'quvchilar) ───────────────────────────────

    def archive_student(self, telegram_id: int) -> bool:
        """O'quvchini arxivlaydi (ma'lumotlari saqlanadi, login bloklanadi)."""
        with self.conn() as c:
            c.execute("UPDATE whitelist SET is_active=0 WHERE telegram_id=?", (telegram_id,))
            return True

    def restore_student(self, telegram_id: int) -> bool:
        """Arxivlangan o'quvchini qayta faollashtiradi."""
        with self.conn() as c:
            c.execute("UPDATE whitelist SET is_active=1 WHERE telegram_id=?", (telegram_id,))
            return True

    def get_archived_students(self, school_id: int) -> list:
        """Arxivlangan o'quvchilar ro'yxati."""
        with self.conn() as c:
            return c.execute("""
                SELECT w.*, c.name AS class_name
                FROM whitelist w JOIN classes c ON w.class_id=c.id
                WHERE w.school_id=? AND w.is_active=0
                ORDER BY c.name, w.full_name
            """, (school_id,)).fetchall()

    # ── Arxiv tizimi (O'qituvchilar) ─────────────────────────────

    def archive_teacher(self, teacher_id: int) -> bool:
        """O'qituvchini arxivlaydi (ma'lumotlari saqlanadi, login bloklanadi)."""
        with self.conn() as c:
            c.execute("UPDATE teachers SET is_active=0 WHERE id=?", (teacher_id,))
            return True

    def restore_teacher(self, teacher_id: int) -> bool:
        """Arxivlangan o'qituvchini qayta faollashtiradi."""
        with self.conn() as c:
            c.execute("UPDATE teachers SET is_active=1 WHERE id=?", (teacher_id,))
            return True

    def get_archived_teachers(self, school_id: int) -> list:
        """Arxivlangan o'qituvchilar ro'yxati."""
        with self.conn() as c:
            return c.execute(
                "SELECT * FROM teachers WHERE school_id=? AND is_active=0 ORDER BY full_name",
                (school_id,)
            ).fetchall()

    def get_teacher_by_id_any(self, teacher_id: int):
        """Arxivlangan yoki faol — har qanday o'qituvchini ID bo'yicha olish."""
        with self.conn() as c:
            return c.execute("SELECT * FROM teachers WHERE id=?", (teacher_id,)).fetchone()

    def get_whitelist_user_any(self, telegram_id: int):
        """Arxivlangan yoki faol — har qanday o'quvchini olish (tiklash uchun)."""
        with self.conn() as c:
            return c.execute("""
                SELECT w.*, c.name AS class_name, s.name AS school_name
                FROM whitelist w
                JOIN classes c ON w.class_id = c.id
                JOIN schools s ON w.school_id = s.id
                WHERE w.telegram_id = ?
            """, (telegram_id,)).fetchone()

    def delete_student(self, telegram_id: int):
        """
        O'quvchini va uning barcha bog'liq ma'lumotlarini o'chiradi.
        attendance, grades, submissions, submission_files, student_parents
        jadvallarida CASCADE o'rnatilmagani uchun qo'lda o'chiriladi.
        """
        with self.conn() as c:
            c.execute("PRAGMA foreign_keys = OFF")
            # 1. Submission fayllarini o'chirish
            c.execute("""
                DELETE FROM submission_files
                WHERE submission_id IN (
                    SELECT id FROM submissions WHERE student_id=?
                )
            """, (telegram_id,))
            # 2. Topshirmalarni o'chirish
            c.execute("DELETE FROM submissions WHERE student_id=?", (telegram_id,))
            # 3. Davomat yozuvlarini o'chirish
            c.execute("DELETE FROM attendance WHERE student_id=?", (telegram_id,))
            # 4. Baholarni o'chirish
            c.execute("DELETE FROM grades WHERE student_id=?", (telegram_id,))
            # 5. Ota-ona bog'liqliklarini o'chirish
            c.execute("DELETE FROM student_parents WHERE student_telegram_id=?", (telegram_id,))
            # 6. Whitelistdan o'chirish
            c.execute("DELETE FROM whitelist WHERE telegram_id=?", (telegram_id,))
            c.execute("PRAGMA foreign_keys = ON")

    # ── O'qituvchilar ────────────────────────────────────────────

    def get_teacher(self, telegram_id: int):
        with self.conn() as c:
            return c.execute("""
                SELECT t.*, s.name AS school_name
                FROM teachers t JOIN schools s ON t.school_id=s.id
                WHERE t.telegram_id=?
            """, (telegram_id,)).fetchone()

    def get_teachers_by_telegram_id(self, telegram_id: int):
        """O'qituvchining barcha maktablardagi yozuvlarini olish"""
        with self.conn() as c:
            return c.execute("""
                SELECT t.*, s.name AS school_name
                FROM teachers t JOIN schools s ON t.school_id=s.id
                WHERE t.telegram_id=? AND t.is_active=1
                ORDER BY s.name
            """, (telegram_id,)).fetchall()
    
    def get_teacher_with_school(self, telegram_id: int, school_id: int):
        """O'qituvchini telegram_id va school_id bo'yicha olish"""
        with self.conn() as c:
            return c.execute("""
                SELECT t.*, s.name AS school_name
                FROM teachers t JOIN schools s ON t.school_id=s.id
                WHERE t.telegram_id=? AND t.school_id=?
            """, (telegram_id, school_id)).fetchone()

    def get_teacher_by_id(self, teacher_id: int):
        with self.conn() as c:
            return c.execute(
                "SELECT * FROM teachers WHERE id=?", (teacher_id,)
            ).fetchone()

    def get_teachers_by_school(self, school_id: int) -> list:
        with self.conn() as c:
            return c.execute(
                "SELECT * FROM teachers WHERE school_id=? AND is_active=1 ORDER BY full_name", (school_id,)
            ).fetchall()

    def add_teacher(self, telegram_id: int, school_id: int, full_name: str) -> int:
        with self.conn() as c:
            cur = c.execute("""
                INSERT OR IGNORE INTO teachers (telegram_id, school_id, full_name)
                VALUES (?,?,?)
            """, (telegram_id, school_id, full_name))
            return cur.lastrowid

    def delete_teacher(self, teacher_id: int):
        """
        O'qituvchini va uning barcha bog'liq ma'lumotlarini o'chiradi.
        teacher_assignments, teacher_attendance, teacher_weekly_schedule,
        lessons (lesson_files), grades — CASCADE o'rnatilmagani uchun qo'lda.
        """
        with self.conn() as c:
            c.execute("PRAGMA foreign_keys = OFF")
            # 1. Dars fayllarini o'chirish
            c.execute("""
                DELETE FROM lesson_files
                WHERE lesson_id IN (
                    SELECT id FROM lessons WHERE teacher_id=?
                )
            """, (teacher_id,))
            # 2. Dars topshirmalarini o'chirish (lessons ga bog'liq)
            c.execute("""
                DELETE FROM submission_files
                WHERE submission_id IN (
                    SELECT s.id FROM submissions s
                    JOIN lessons l ON s.lesson_id = l.id
                    WHERE l.teacher_id=?
                )
            """, (teacher_id,))
            c.execute("""
                DELETE FROM submissions
                WHERE lesson_id IN (
                    SELECT id FROM lessons WHERE teacher_id=?
                )
            """, (teacher_id,))
            # 3. Darslarni o'chirish
            c.execute("DELETE FROM lessons WHERE teacher_id=?", (teacher_id,))
            # 4. Baholarni o'chirish
            c.execute("DELETE FROM grades WHERE teacher_id=?", (teacher_id,))
            # 5. O'qituvchi davomatini o'chirish
            c.execute("DELETE FROM teacher_attendance WHERE teacher_id=?", (teacher_id,))
            # 6. Haftalik jadval slotlarini o'chirish
            c.execute("DELETE FROM teacher_weekly_schedule WHERE teacher_id=?", (teacher_id,))
            # 7. Sinf-fan biriktirmalarini o'chirish
            c.execute("DELETE FROM teacher_assignments WHERE teacher_id=?", (teacher_id,))
            # 8. O'qituvchini o'chirish
            c.execute("DELETE FROM teachers WHERE id=?", (teacher_id,))
            c.execute("PRAGMA foreign_keys = ON")

    # ── O'qituvchi-sinf-fan biriktirish ─────────────────────────

    def get_teacher_assignments(self, teacher_id: int) -> list:
        with self.conn() as c:
            return c.execute("""
                SELECT ta.*, c.name AS class_name, s.name AS subject_name
                FROM teacher_assignments ta
                JOIN classes  c ON ta.class_id   = c.id
                JOIN subjects s ON ta.subject_id  = s.id
                WHERE ta.teacher_id = ?
            """, (teacher_id,)).fetchall()

    def assign_teacher(self, teacher_id: int, class_id: int, subject_id: int) -> bool:
        with self.conn() as c:
            try:
                c.execute("""
                    INSERT OR IGNORE INTO teacher_assignments (teacher_id, class_id, subject_id)
                    VALUES (?,?,?)
                """, (teacher_id, class_id, subject_id))
                return True
            except Exception:
                return False

    def remove_assignment(self, assignment_id: int):
        with self.conn() as c:
            c.execute("DELETE FROM teacher_assignments WHERE id=?", (assignment_id,))

    def get_teacher_classes(self, teacher_id: int) -> list:
        """O'qituvchi o'tadigan sinflar (takrorsiz)"""
        with self.conn() as c:
            return c.execute("""
                SELECT DISTINCT c.id, c.name
                FROM teacher_assignments ta JOIN classes c ON ta.class_id=c.id
                WHERE ta.teacher_id=?
                ORDER BY c.name
            """, (teacher_id,)).fetchall()

    def get_teacher_subjects_for_class(self, teacher_id: int, class_id: int) -> list:
        """O'qituvchining berilgan sinfda o'qitiladigan fanlari"""
        with self.conn() as c:
            return c.execute("""
                SELECT DISTINCT s.id, s.name
                FROM teacher_assignments ta JOIN subjects s ON ta.subject_id=s.id
                WHERE ta.teacher_id=? AND ta.class_id=?
                ORDER BY s.name
            """, (teacher_id, class_id)).fetchall()

    def get_teachers_by_subject_class(self, subject_id: int, class_id: int) -> list:
        """Berilgan sinf + fan uchun o'qituvchilar"""
        with self.conn() as c:
            return c.execute("""
                SELECT DISTINCT t.id, t.full_name, t.telegram_id
                FROM teacher_assignments ta
                JOIN teachers t ON ta.teacher_id = t.id
                WHERE ta.subject_id=? AND ta.class_id=?
                ORDER BY t.full_name
            """, (subject_id, class_id)).fetchall()

    def remove_teacher_from_subject_class(self, teacher_id: int, class_id: int, subject_id: int):
        """O'qituvchini sinf + fan biriktirmasidan olib tashlash"""
        with self.conn() as c:
            c.execute("""
                DELETE FROM teacher_assignments
                WHERE teacher_id=? AND class_id=? AND subject_id=?
            """, (teacher_id, class_id, subject_id))

    # ── Telegram ID yangilash ────────────────────────────────────

    def update_student_telegram_id(self, old_id: int, new_id: int) -> bool:
        """
        O'quvchining Telegram ID sini yangilaydi.
        Barcha bog'liq jadvallar (attendance, grades, submissions) ham yangilanadi.
        """
        with self.conn() as c:
            # Yangi ID allaqachon boshqa o'quvchida bormi?
            existing = c.execute(
                "SELECT telegram_id FROM whitelist WHERE telegram_id=?", (new_id,)
            ).fetchone()
            if existing:
                return False
            # PRAGMA foreign_keys=ON bo'lganda CASCADE UPDATE ishlamaydi SQLite da,
            # shuning uchun qo'lda yangilaymiz
            c.executescript(f"""
                PRAGMA foreign_keys = OFF;
                UPDATE attendance   SET student_id={new_id} WHERE student_id={old_id};
                UPDATE grades       SET student_id={new_id} WHERE student_id={old_id};
                UPDATE submissions  SET student_id={new_id} WHERE student_id={old_id};
                UPDATE whitelist    SET telegram_id={new_id} WHERE telegram_id={old_id};
                PRAGMA foreign_keys = ON;
            """)
            return True

    def update_teacher_telegram_id(self, old_id: int, new_id: int) -> bool:
        """
        O'qituvchining Telegram ID sini yangilaydi.
        teachers.id o'zgarmaydi — bog'liq jadvallar ta'sirlanmaydi.
        """
        with self.conn() as c:
            existing = c.execute(
                "SELECT id FROM teachers WHERE telegram_id=?", (new_id,)
            ).fetchone()
            if existing:
                return False
            c.execute(
                "UPDATE teachers SET telegram_id=? WHERE telegram_id=?",
                (new_id, old_id)
            )
            return True