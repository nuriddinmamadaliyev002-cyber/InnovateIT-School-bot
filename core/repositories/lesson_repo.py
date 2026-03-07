"""
core/repositories/lesson_repo.py — Darslar, fayllar, topshirmalar
"""
from core.database import BaseDB


class LessonRepo(BaseDB):

    # ── Darslar ──────────────────────────────────────────────────

    def save_lesson(self, teacher_id: int, class_id: int, subject_id: int,
                    date: str, content_type: str, content: str = None,
                    file_id: str = None, file_type: str = None) -> int:
        with self.conn() as c:
            cur = c.execute("""
                INSERT INTO lessons
                    (teacher_id, class_id, subject_id, date, content_type, content, file_id, file_type)
                VALUES (?,?,?,?,?,?,?,?)
            """, (teacher_id, class_id, subject_id, date,
                  content_type, content, file_id, file_type))
            return cur.lastrowid

    def add_lesson_file(self, lesson_id: int, file_id: str, file_type: str):
        with self.conn() as c:
            c.execute(
                "INSERT INTO lesson_files (lesson_id, file_id, file_type) VALUES (?,?,?)",
                (lesson_id, file_id, file_type)
            )

    def get_lessons(self, class_id: int, subject_id: int,
                    date: str, content_type: str) -> list:
        with self.conn() as c:
            return c.execute("""
                SELECT l.*, t.full_name AS teacher_name
                FROM lessons l JOIN teachers t ON l.teacher_id=t.id
                WHERE l.class_id=? AND l.subject_id=? AND l.date=? AND l.content_type=?
                ORDER BY l.created_at DESC
            """, (class_id, subject_id, date, content_type)).fetchall()

    def get_lesson_files(self, lesson_id: int) -> list:
        with self.conn() as c:
            return c.execute(
                "SELECT * FROM lesson_files WHERE lesson_id=?", (lesson_id,)
            ).fetchall()

    def get_all_lessons_for_class(self, class_id: int, subject_id: int) -> list:
        with self.conn() as c:
            return c.execute("""
                SELECT * FROM lessons
                WHERE class_id=? AND subject_id=?
                ORDER BY date DESC, created_at DESC
            """, (class_id, subject_id)).fetchall()

    def get_lesson(self, lesson_id: int):
        """Bitta darsni ID bo'yicha olish — dict qaytaradi (.get() ishlaydi)"""
        with self.conn() as c:
            row = c.execute("""
                SELECT l.*, t.full_name AS teacher_name,
                       c.name AS class_name, s.name AS subject_name
                FROM lessons l
                JOIN teachers t ON l.teacher_id = t.id
                JOIN classes  c ON l.class_id   = c.id
                JOIN subjects s ON l.subject_id  = s.id
                WHERE l.id = ?
            """, (lesson_id,)).fetchone()
            if row is None:
                return None
            d = dict(row)
            # deadline va comment ustunlari eski DBda bo'lmasligi mumkin
            d.setdefault('deadline', None)
            d.setdefault('comment',  None)
            return d

    def get_lessons_by_teacher_class_subject(self, teacher_id: int, class_id: int,
                                               subject_id: int,
                                               content_type: str = None) -> list:
        """O'qituvchi, sinf va fanga ko'ra darslarni olish (sana bo'yicha tartib)"""
        with self.conn() as c:
            q = """
                SELECT l.*, c.name AS class_name, s.name AS subject_name
                FROM lessons l
                JOIN classes  c ON l.class_id  = c.id
                JOIN subjects s ON l.subject_id = s.id
                WHERE l.teacher_id=? AND l.class_id=? AND l.subject_id=?
            """
            params = [teacher_id, class_id, subject_id]
            if content_type:
                q += " AND l.content_type=?"
                params.append(content_type)
            q += " ORDER BY l.date DESC, l.created_at DESC"
            return c.execute(q, params).fetchall()

    def get_lessons_by_teacher_date(self, teacher_id: int, date: str,
                                     content_type: str = None) -> list:
        """O'qituvchi va sanaga ko'ra darslarni olish"""
        with self.conn() as c:
            if content_type:
                return c.execute("""
                    SELECT l.*, c.name AS class_name, s.name AS subject_name
                    FROM lessons l
                    JOIN classes  c ON l.class_id  = c.id
                    JOIN subjects s ON l.subject_id = s.id
                    WHERE l.teacher_id=? AND l.date=? AND l.content_type=?
                    ORDER BY l.class_id, l.subject_id
                """, (teacher_id, date, content_type)).fetchall()
            return c.execute("""
                SELECT l.*, c.name AS class_name, s.name AS subject_name
                FROM lessons l
                JOIN classes  c ON l.class_id  = c.id
                JOIN subjects s ON l.subject_id = s.id
                WHERE l.teacher_id=? AND l.date=?
                ORDER BY l.content_type, l.class_id, l.subject_id
            """, (teacher_id, date)).fetchall()

    def update_lesson_content(self, lesson_id: int, content: str):
        """Dars matnini yangilash"""
        with self.conn() as c:
            c.execute("UPDATE lessons SET content=? WHERE id=?", (content, lesson_id))

    def update_lesson_deadline(self, lesson_id: int, deadline: str):
        """Dars deadlinini yangilash (None berilsa — o'chiradi)"""
        with self.conn() as c:
            c.execute("UPDATE lessons SET deadline=? WHERE id=?", (deadline, lesson_id))

    def update_lesson_comment(self, lesson_id: int, comment: str):
        """Dars izohini yangilash"""
        with self.conn() as c:
            c.execute("UPDATE lessons SET comment=? WHERE id=?", (comment, lesson_id))

    def replace_lesson_main_file(self, lesson_id: int,
                                  file_id: str, file_type: str):
        """Darsning asosiy faylini almashtirish (lesson_files ham tozalanadi)"""
        with self.conn() as c:
            c.execute(
                "UPDATE lessons SET file_id=?, file_type=? WHERE id=?",
                (file_id, file_type, lesson_id)
            )
            # Eski qo'shimcha fayllarni o'chirish
            c.execute("DELETE FROM lesson_files WHERE lesson_id=?", (lesson_id,))

    def delete_lesson(self, lesson_id: int):
        with self.conn() as c:
            c.execute("DELETE FROM lessons WHERE id=?", (lesson_id,))

    # ── Dars jadvali (schedules) ──────────────────────────────────

    def save_schedule(self, school_id: int, file_id: str,
                      file_type: str = "photo", class_id: int = None) -> int:
        with self.conn() as c:
            cur = c.execute("""
                INSERT INTO schedules (school_id, class_id, file_id, file_type)
                VALUES (?,?,?,?)
            """, (school_id, class_id, file_id, file_type))
            return cur.lastrowid

    def get_schedule(self, school_id: int, class_id: int = None):
        with self.conn() as c:
            if class_id:
                row = c.execute("""
                    SELECT * FROM schedules
                    WHERE school_id=? AND class_id=?
                    ORDER BY uploaded_at DESC LIMIT 1
                """, (school_id, class_id)).fetchone()
                if row:
                    return row
            return c.execute("""
                SELECT * FROM schedules
                WHERE school_id=? AND class_id IS NULL
                ORDER BY uploaded_at DESC LIMIT 1
            """, (school_id,)).fetchone()

    # ── Topshirmalar ─────────────────────────────────────────────

    def save_submission(self, student_id: int, subject_id: int, class_id: int,
                        date: str, content: str = None,
                        file_id: str = None, file_type: str = "text",
                        lesson_id: int = None) -> int:
        with self.conn() as c:
            # Eski topshirmani o'chirish — lesson_id bo'yicha (aniq dars) yoki subject+date
            if lesson_id:
                old_rows = c.execute("""
                    SELECT id FROM submissions
                    WHERE student_id=? AND lesson_id=?
                """, (student_id, lesson_id)).fetchall()
            else:
                old_rows = c.execute("""
                    SELECT id FROM submissions
                    WHERE student_id=? AND subject_id=? AND date=?
                """, (student_id, subject_id, date)).fetchall()
            for row in old_rows:
                c.execute("DELETE FROM submission_files WHERE submission_id=?", (row['id'],))
            if lesson_id:
                c.execute("""
                    DELETE FROM submissions WHERE student_id=? AND lesson_id=?
                """, (student_id, lesson_id))
            else:
                c.execute("""
                    DELETE FROM submissions WHERE student_id=? AND subject_id=? AND date=?
                """, (student_id, subject_id, date))
            # Yangi topshirma saqlash
            cur = c.execute("""
                INSERT INTO submissions
                    (student_id, subject_id, class_id, lesson_id, date, content, file_id, file_type)
                VALUES (?,?,?,?,?,?,?,?)
            """, (student_id, subject_id, class_id, lesson_id, date, content, file_id, file_type))
            return cur.lastrowid

    def add_submission_file(self, submission_id: int, file_id: str, file_type: str):
        with self.conn() as c:
            c.execute(
                "INSERT INTO submission_files (submission_id, file_id, file_type) VALUES (?,?,?)",
                (submission_id, file_id, file_type)
            )

    def get_submissions(self, class_id: int = None, subject_id: int = None,
                        date: str = None, student_id: int = None) -> list:
        """Flexible filter bilan topshirmalarni olish"""
        where, params = [], []
        if class_id:   where.append("s.class_id=?");   params.append(class_id)
        if subject_id: where.append("s.subject_id=?"); params.append(subject_id)
        if date:       where.append("s.date=?");       params.append(date)
        if student_id: where.append("s.student_id=?"); params.append(student_id)
        q = """
            SELECT s.*, w.full_name AS student_name, sub.name AS subject_name
            FROM submissions s
            JOIN whitelist w  ON s.student_id = w.telegram_id
            JOIN subjects sub ON s.subject_id  = sub.id
        """
        if where:
            q += " WHERE " + " AND ".join(where)
        q += " ORDER BY s.submitted_at DESC"
        with self.conn() as c:
            return c.execute(q, params).fetchall()

    def get_homework_dates(self, class_id: int) -> list:
        """Sinf uchun uyga vazifa mavjud sanalar ro'yxati (eng yangi avval).
        Qaytaradi: [{'date': '2026-02-27', 'deadline': '2026-02-28 23:59' | None}, ...]
        """
        with self.conn() as c:
            rows = c.execute("""
                SELECT date, MAX(deadline) AS deadline
                FROM lessons
                WHERE class_id=? AND content_type='homework'
                GROUP BY date
                ORDER BY date DESC
            """, (class_id,)).fetchall()
            return [{'date': r['date'], 'deadline': r['deadline']} for r in rows]

    def get_topic_dates(self, class_id: int) -> list:
        """Sinf uchun mavzu mavjud sanalar ro'yxati (eng yangi avval)"""
        with self.conn() as c:
            rows = c.execute("""
                SELECT DISTINCT date FROM lessons
                WHERE class_id=? AND content_type='topic'
                ORDER BY date DESC
            """, (class_id,)).fetchall()
            return [r['date'] for r in rows]

    def get_topics_for_class(self, class_id: int) -> list:
        """Sinfdagi barcha mavzular — mavzu nomi (content) + fan nomi + sana.
        Qaytaradi: [{'id', 'content', 'subject_name', 'date', 'file_id', 'file_type'}, ...]
        """
        with self.conn() as c:
            return c.execute("""
                SELECT l.id, l.content, l.date, l.file_id, l.file_type,
                       s.name AS subject_name
                FROM lessons l
                JOIN subjects s ON l.subject_id = s.id
                WHERE l.class_id=? AND l.content_type='topic'
                ORDER BY l.date DESC, l.created_at DESC
            """, (class_id,)).fetchall()

    def count_submissions(self, class_id: int = None,
                          subject_id: int = None, date: str = None) -> int:
        """Topshirmalar sonini sanash"""
        where, params = [], []
        if class_id:   where.append("class_id=?");   params.append(class_id)
        if subject_id: where.append("subject_id=?"); params.append(subject_id)
        if date:       where.append("date=?");       params.append(date)
        q = "SELECT COUNT(*) FROM submissions"
        if where:
            q += " WHERE " + " AND ".join(where)
        with self.conn() as c:
            return c.execute(q, params).fetchone()[0]

    def get_submission_files(self, submission_id: int) -> list:
        with self.conn() as c:
            return c.execute(
                "SELECT * FROM submission_files WHERE submission_id=?", (submission_id,)
            ).fetchall()
    def get_student_submission(self, student_id: int, subject_id: int, date: str,
                               lesson_id: int = None):
        """O'quvchining topshirmasi — lesson_id bo'yicha (aniq dars) yoki subject+date"""
        with self.conn() as c:
            if lesson_id:
                return c.execute("""
                    SELECT * FROM submissions
                    WHERE student_id=? AND lesson_id=?
                    ORDER BY submitted_at DESC LIMIT 1
                """, (student_id, lesson_id)).fetchone()
            return c.execute("""
                SELECT * FROM submissions
                WHERE student_id=? AND subject_id=? AND date=?
                ORDER BY submitted_at DESC LIMIT 1
            """, (student_id, subject_id, date)).fetchone()

    def get_homework_subjects_for_date(self, class_id: int, date: str) -> list:
        """Berilgan sinf va sanada homework mavjud fanlar ro'yxati.
        Qaytaradi: [{'subject_id', 'subject_name', 'deadline'}, ...]
        """
        with self.conn() as c:
            return c.execute("""
                SELECT s.id AS subject_id, s.name AS subject_name,
                       MAX(l.deadline) AS deadline
                FROM lessons l
                JOIN subjects s ON l.subject_id = s.id
                WHERE l.class_id=? AND l.date=? AND l.content_type='homework'
                GROUP BY s.id, s.name
                ORDER BY s.name
            """, (class_id, date)).fetchall()

    def get_all_teacher_homeworks(self, teacher_id: int) -> list:
        """
        O'qituvchi o'zi qo'shgan barcha uyga vazifalar — yangi avval.
        Qaytaradi: [{'id', 'date', 'content', 'file_id', 'file_type',
                     'subject_id', 'subject_name', 'class_id', 'class_name'}, ...]
        """
        with self.conn() as c:
            return c.execute("""
                SELECT l.id, l.date, l.content, l.file_id, l.file_type,
                       l.subject_id, l.class_id,
                       s.name AS subject_name,
                       cl.name AS class_name
                FROM lessons l
                JOIN subjects s  ON l.subject_id = s.id
                JOIN classes  cl ON l.class_id   = cl.id
                WHERE l.teacher_id=? AND l.content_type='homework'
                ORDER BY l.date DESC, l.created_at DESC
            """, (teacher_id,)).fetchall()

    def get_all_homeworks_for_class(self, class_id: int) -> list:
        """Sinfdagi barcha uyga vazifalar — fan nomi + matn + sana (yangi avval).
        Qaytaradi: [{'id', 'content', 'date', 'deadline', 'file_id', 'file_type',
                     'subject_id', 'subject_name'}, ...]
        """
        with self.conn() as c:
            return c.execute("""
                SELECT l.id, l.content, l.date, l.deadline,
                       l.file_id, l.file_type, l.subject_id,
                       s.name AS subject_name
                FROM lessons l
                JOIN subjects s ON l.subject_id = s.id
                WHERE l.class_id=? AND l.content_type='homework'
                ORDER BY l.date DESC, l.created_at DESC
            """, (class_id,)).fetchall()