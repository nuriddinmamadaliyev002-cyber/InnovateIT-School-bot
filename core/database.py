"""
core/database.py — SQLite ulanish + jadval yaratish

Yangiliklar (v2):
  lessons.deadline       — ixtiyoriy deadline (YYYY-MM-DD HH:MM)
  submissions.is_late    — 1 = kech topshirildi
  grades.comment         — o'qituvchi izohi
"""
import sqlite3


class BaseDB:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        return c

    def _migrate(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("PRAGMA foreign_keys = OFF")

            # Mavjud jadvallar ro'yxati
            existing_tables = {
                r[0] for r in c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }

            # 1. subjects migratsiyasi (faqat jadval mavjud bo'lsa)
            if 'subjects' in existing_tables:
                info = c.execute("PRAGMA table_info(subjects)").fetchall()
                col_names = [row[1] for row in info]
                if 'class_id' in col_names:
                    c.executescript("""
                        CREATE TABLE IF NOT EXISTS subject_assignments (
                            id         INTEGER PRIMARY KEY AUTOINCREMENT,
                            subject_id INTEGER NOT NULL,
                            class_id   INTEGER NOT NULL,
                            UNIQUE(subject_id, class_id)
                        );
                        INSERT OR IGNORE INTO subject_assignments (subject_id, class_id)
                        SELECT id, class_id FROM subjects
                        WHERE class_id IS NOT NULL AND class_id != 0;
                        CREATE TABLE IF NOT EXISTS subjects_new (
                            id        INTEGER PRIMARY KEY AUTOINCREMENT,
                            name      TEXT NOT NULL,
                            school_id INTEGER NOT NULL,
                            UNIQUE(name, school_id)
                        );
                        INSERT OR IGNORE INTO subjects_new (id, name, school_id)
                        SELECT id, name, school_id FROM subjects;
                        DROP TABLE subjects;
                        ALTER TABLE subjects_new RENAME TO subjects;
                    """)

            # 2. lessons.deadline
            if 'lessons' in existing_tables:
                lessons_cols = [r[1] for r in c.execute("PRAGMA table_info(lessons)").fetchall()]
                if 'deadline' not in lessons_cols:
                    c.execute("ALTER TABLE lessons ADD COLUMN deadline TEXT")
                if 'comment' not in lessons_cols:
                    c.execute("ALTER TABLE lessons ADD COLUMN comment TEXT")

            # 3. submissions.is_late + lesson_id
            if 'submissions' in existing_tables:
                sub_cols = [r[1] for r in c.execute("PRAGMA table_info(submissions)").fetchall()]
                if 'is_late' not in sub_cols:
                    c.execute("ALTER TABLE submissions ADD COLUMN is_late INTEGER NOT NULL DEFAULT 0")
                if 'lesson_id' not in sub_cols:
                    c.execute("ALTER TABLE submissions ADD COLUMN lesson_id INTEGER")

            # 4. grades.comment + comment_file_id + comment_file_type
            if 'grades' in existing_tables:
                grade_cols = [r[1] for r in c.execute("PRAGMA table_info(grades)").fetchall()]
                if 'comment' not in grade_cols:
                    c.execute("ALTER TABLE grades ADD COLUMN comment TEXT")
                if 'comment_file_id' not in grade_cols:
                    c.execute("ALTER TABLE grades ADD COLUMN comment_file_id TEXT")
                if 'comment_file_type' not in grade_cols:
                    c.execute("ALTER TABLE grades ADD COLUMN comment_file_type TEXT")
            
            # 5. teacher_attendance.comment ustuni
            if 'teacher_attendance' in existing_tables:
                ta_cols = [r[1] for r in c.execute("PRAGMA table_info(teacher_attendance)").fetchall()]
                if 'comment' not in ta_cols:
                    c.execute("ALTER TABLE teacher_attendance ADD COLUMN comment TEXT")

            # 5b. attendance.comment ustuni (o'quvchi davomati)
            if 'attendance' in existing_tables:
                att_cols = [r[1] for r in c.execute("PRAGMA table_info(attendance)").fetchall()]
                if 'comment' not in att_cols:
                    c.execute("ALTER TABLE attendance ADD COLUMN comment TEXT")

            # 6. teachers - ko'p maktabga biriktirish (UNIQUE constraint o'zgartirish)
            if 'teachers' in existing_tables:
                create_sql = c.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name='teachers'"
                ).fetchone()
                
                # Agar hali (telegram_id, school_id) UNIQUE bo'lmasa
                if create_sql and 'UNIQUE(telegram_id, school_id)' not in create_sql[0]:
                    c.executescript("""
                        CREATE TABLE IF NOT EXISTS teachers_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            telegram_id INTEGER NOT NULL,
                            school_id   INTEGER NOT NULL,
                            full_name   TEXT NOT NULL,
                            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(telegram_id, school_id),
                            FOREIGN KEY (school_id) REFERENCES schools(id)
                        );
                        INSERT OR IGNORE INTO teachers_new (id, telegram_id, school_id, full_name, created_at)
                        SELECT id, telegram_id, school_id, full_name, created_at FROM teachers;
                        DROP TABLE teachers;
                        ALTER TABLE teachers_new RENAME TO teachers;
                    """)

            c.execute("PRAGMA foreign_keys = ON")

    def init_tables(self):
        self._migrate()
        with self.conn() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS schools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    address TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS school_admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    school_id   INTEGER NOT NULL,
                    full_name   TEXT NOT NULL,
                    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(telegram_id, school_id),
                    FOREIGN KEY (school_id) REFERENCES schools(id)
                );
                CREATE TABLE IF NOT EXISTS classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    school_id INTEGER NOT NULL,
                    UNIQUE(name, school_id),
                    FOREIGN KEY (school_id) REFERENCES schools(id)
                );
                CREATE TABLE IF NOT EXISTS whitelist (
                    telegram_id INTEGER PRIMARY KEY,
                    full_name   TEXT NOT NULL,
                    class_id    INTEGER NOT NULL,
                    school_id   INTEGER NOT NULL,
                    joined_at   TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (class_id) REFERENCES classes(id),
                    FOREIGN KEY (school_id) REFERENCES schools(id)
                );
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username    TEXT,
                    first_name  TEXT,
                    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS subjects (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    name      TEXT NOT NULL,
                    school_id INTEGER NOT NULL,
                    UNIQUE(name, school_id),
                    FOREIGN KEY (school_id) REFERENCES schools(id)
                );
                CREATE TABLE IF NOT EXISTS subject_assignments (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id INTEGER NOT NULL,
                    class_id   INTEGER NOT NULL,
                    UNIQUE(subject_id, class_id),
                    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                    FOREIGN KEY (class_id)   REFERENCES classes(id)  ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS teachers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL UNIQUE,
                    school_id   INTEGER NOT NULL,
                    full_name   TEXT NOT NULL,
                    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (school_id) REFERENCES schools(id)
                );
                CREATE TABLE IF NOT EXISTS teacher_assignments (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id INTEGER NOT NULL,
                    class_id   INTEGER NOT NULL,
                    subject_id INTEGER NOT NULL,
                    UNIQUE(teacher_id, class_id, subject_id),
                    FOREIGN KEY (teacher_id) REFERENCES teachers(id),
                    FOREIGN KEY (class_id)   REFERENCES classes(id),
                    FOREIGN KEY (subject_id) REFERENCES subjects(id)
                );
                CREATE TABLE IF NOT EXISTS lessons (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id   INTEGER NOT NULL,
                    class_id     INTEGER NOT NULL,
                    subject_id   INTEGER NOT NULL,
                    date         TEXT NOT NULL,
                    content_type TEXT NOT NULL DEFAULT 'homework',
                    content      TEXT,
                    file_id      TEXT,
                    file_type    TEXT,
                    deadline     TEXT,
                    comment      TEXT,
                    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (teacher_id) REFERENCES teachers(id),
                    FOREIGN KEY (class_id)   REFERENCES classes(id),
                    FOREIGN KEY (subject_id) REFERENCES subjects(id)
                );
                CREATE TABLE IF NOT EXISTS lesson_files (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    lesson_id INTEGER NOT NULL,
                    file_id   TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS schedules (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    school_id   INTEGER NOT NULL,
                    class_id    INTEGER,
                    file_id     TEXT NOT NULL,
                    file_type   TEXT NOT NULL DEFAULT 'photo',
                    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (school_id) REFERENCES schools(id),
                    FOREIGN KEY (class_id)  REFERENCES classes(id)
                );
                CREATE TABLE IF NOT EXISTS submissions (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id   INTEGER NOT NULL,
                    subject_id   INTEGER NOT NULL,
                    class_id     INTEGER NOT NULL,
                    lesson_id    INTEGER,
                    date         TEXT NOT NULL,
                    content      TEXT,
                    file_id      TEXT,
                    file_type    TEXT,
                    is_late      INTEGER NOT NULL DEFAULT 0,
                    submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES whitelist(telegram_id),
                    FOREIGN KEY (subject_id) REFERENCES subjects(id),
                    FOREIGN KEY (class_id)   REFERENCES classes(id),
                    FOREIGN KEY (lesson_id)  REFERENCES lessons(id) ON DELETE SET NULL
                );
                CREATE TABLE IF NOT EXISTS submission_files (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    submission_id INTEGER NOT NULL,
                    file_id       TEXT NOT NULL,
                    file_type     TEXT NOT NULL,
                    FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS attendance (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    class_id   INTEGER NOT NULL,
                    subject_id INTEGER NOT NULL,
                    date       TEXT NOT NULL,
                    status     TEXT NOT NULL DEFAULT 'present',
                    UNIQUE(student_id, class_id, subject_id, date),
                    FOREIGN KEY (student_id) REFERENCES whitelist(telegram_id),
                    FOREIGN KEY (class_id)   REFERENCES classes(id),
                    FOREIGN KEY (subject_id) REFERENCES subjects(id)
                );
                CREATE TABLE IF NOT EXISTS teacher_attendance (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id INTEGER NOT NULL,
                    date       TEXT NOT NULL,
                    status     TEXT NOT NULL DEFAULT 'present',
                    school_id  INTEGER NOT NULL,
                    comment    TEXT,
                    UNIQUE(teacher_id, date),
                    FOREIGN KEY (teacher_id) REFERENCES teachers(id),
                    FOREIGN KEY (school_id)  REFERENCES schools(id)
                );
                CREATE TABLE IF NOT EXISTS grades (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    teacher_id INTEGER NOT NULL,
                    subject_id INTEGER NOT NULL,
                    class_id   INTEGER NOT NULL,
                    criteria   TEXT NOT NULL,
                    score      INTEGER NOT NULL,
                    date       TEXT NOT NULL,
                    comment    TEXT,
                    comment_file_id   TEXT,
                    comment_file_type TEXT,
                    UNIQUE(student_id, subject_id, criteria, date),
                    FOREIGN KEY (student_id) REFERENCES whitelist(telegram_id),
                    FOREIGN KEY (teacher_id) REFERENCES teachers(id),
                    FOREIGN KEY (subject_id) REFERENCES subjects(id),
                    FOREIGN KEY (class_id)   REFERENCES classes(id)
                );
                CREATE TABLE IF NOT EXISTS teacher_weekly_schedule (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id INTEGER NOT NULL,
                    class_id   INTEGER NOT NULL,
                    subject_id INTEGER NOT NULL,
                    weekday    INTEGER NOT NULL,
                    start_time TEXT,
                    end_time   TEXT,
                    school_id  INTEGER NOT NULL,
                    UNIQUE(teacher_id, class_id, subject_id, weekday),
                    FOREIGN KEY (teacher_id) REFERENCES teachers(id),
                    FOREIGN KEY (class_id)   REFERENCES classes(id),
                    FOREIGN KEY (subject_id) REFERENCES subjects(id),
                    FOREIGN KEY (school_id)  REFERENCES schools(id)
                );
                CREATE TABLE IF NOT EXISTS student_parents (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_telegram_id INTEGER NOT NULL,
                    parent_telegram_id  INTEGER NOT NULL UNIQUE,
                    label               TEXT NOT NULL DEFAULT 'Ota/Ona',
                    added_at            TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_telegram_id) REFERENCES whitelist(telegram_id) ON DELETE CASCADE
                );
            """)