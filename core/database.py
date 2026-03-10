"""
core/database.py — PostgreSQL ulanish + jadval yaratish

SQLite dan PostgreSQL ga o'tkazildi:
  - sqlite3 → psycopg2
  - ? placeholder → %s
  - sqlite3.Row → RealDictCursor (dict kabi ishlaydi)
  - INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
  - INTEGER AUTOINCREMENT → SERIAL
  - strftime('%Y-%m', date) → TO_CHAR(date::date, 'YYYY-MM')
  - PRAGMA → yo'q
"""
import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


class BaseDB:
    def __init__(self, db_path: str = None):
        # db_path SQLite uchun edi — PostgreSQL da DATABASE_URL ishlatiladi
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL muhit o'zgaruvchisi o'rnatilmagan!")

    def conn(self):
        """PostgreSQL connection qaytaradi"""
        return psycopg2.connect(self.database_url)

    def init_tables(self):
        """Barcha jadvallarni yaratish"""
        sql = """
            CREATE TABLE IF NOT EXISTS schools (
                id         SERIAL PRIMARY KEY,
                name       TEXT NOT NULL UNIQUE,
                address    TEXT,
                created_at TEXT DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')
            );
            CREATE TABLE IF NOT EXISTS school_admins (
                id          SERIAL PRIMARY KEY,
                telegram_id BIGINT NOT NULL,
                school_id   INTEGER NOT NULL REFERENCES schools(id),
                full_name   TEXT NOT NULL,
                created_at  TEXT DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS'),
                UNIQUE(telegram_id, school_id)
            );
            CREATE TABLE IF NOT EXISTS classes (
                id        SERIAL PRIMARY KEY,
                name      TEXT NOT NULL,
                school_id INTEGER NOT NULL REFERENCES schools(id),
                UNIQUE(name, school_id)
            );
            CREATE TABLE IF NOT EXISTS whitelist (
                telegram_id BIGINT PRIMARY KEY,
                full_name   TEXT NOT NULL,
                class_id    INTEGER NOT NULL REFERENCES classes(id),
                school_id   INTEGER NOT NULL REFERENCES schools(id),
                is_active   INTEGER NOT NULL DEFAULT 1,
                joined_at   TEXT DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')
            );
            CREATE TABLE IF NOT EXISTS users (
                id          SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username    TEXT,
                first_name  TEXT,
                created_at  TEXT DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')
            );
            CREATE TABLE IF NOT EXISTS subjects (
                id        SERIAL PRIMARY KEY,
                name      TEXT NOT NULL,
                school_id INTEGER NOT NULL REFERENCES schools(id),
                UNIQUE(name, school_id)
            );
            CREATE TABLE IF NOT EXISTS subject_assignments (
                id         SERIAL PRIMARY KEY,
                subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
                class_id   INTEGER NOT NULL REFERENCES classes(id)  ON DELETE CASCADE,
                UNIQUE(subject_id, class_id)
            );
            CREATE TABLE IF NOT EXISTS teachers (
                id          SERIAL PRIMARY KEY,
                telegram_id BIGINT NOT NULL UNIQUE,
                school_id   INTEGER NOT NULL REFERENCES schools(id),
                full_name   TEXT NOT NULL,
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')
            );
            CREATE TABLE IF NOT EXISTS teacher_assignments (
                id         SERIAL PRIMARY KEY,
                teacher_id INTEGER NOT NULL REFERENCES teachers(id),
                class_id   INTEGER NOT NULL REFERENCES classes(id),
                subject_id INTEGER NOT NULL REFERENCES subjects(id),
                UNIQUE(teacher_id, class_id, subject_id)
            );
            CREATE TABLE IF NOT EXISTS lessons (
                id           SERIAL PRIMARY KEY,
                teacher_id   INTEGER NOT NULL REFERENCES teachers(id),
                class_id     INTEGER NOT NULL REFERENCES classes(id),
                subject_id   INTEGER NOT NULL REFERENCES subjects(id),
                date         TEXT NOT NULL,
                content_type TEXT NOT NULL DEFAULT 'homework',
                content      TEXT,
                file_id      TEXT,
                file_type    TEXT,
                deadline     TEXT,
                comment      TEXT,
                created_at   TEXT DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')
            );
            CREATE TABLE IF NOT EXISTS lesson_files (
                id        SERIAL PRIMARY KEY,
                lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
                file_id   TEXT NOT NULL,
                file_type TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS schedules (
                id          SERIAL PRIMARY KEY,
                school_id   INTEGER NOT NULL REFERENCES schools(id),
                class_id    INTEGER REFERENCES classes(id),
                file_id     TEXT NOT NULL,
                file_type   TEXT NOT NULL DEFAULT 'photo',
                uploaded_at TEXT DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')
            );
            CREATE TABLE IF NOT EXISTS submissions (
                id           SERIAL PRIMARY KEY,
                student_id   BIGINT NOT NULL REFERENCES whitelist(telegram_id),
                subject_id   INTEGER NOT NULL REFERENCES subjects(id),
                class_id     INTEGER NOT NULL REFERENCES classes(id),
                lesson_id    INTEGER REFERENCES lessons(id) ON DELETE SET NULL,
                date         TEXT NOT NULL,
                content      TEXT,
                file_id      TEXT,
                file_type    TEXT,
                is_late      INTEGER NOT NULL DEFAULT 0,
                submitted_at TEXT DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')
            );
            CREATE TABLE IF NOT EXISTS submission_files (
                id            SERIAL PRIMARY KEY,
                submission_id INTEGER NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
                file_id       TEXT NOT NULL,
                file_type     TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS attendance (
                id         SERIAL PRIMARY KEY,
                student_id BIGINT NOT NULL,
                class_id   INTEGER NOT NULL REFERENCES classes(id),
                subject_id INTEGER NOT NULL,
                date       TEXT NOT NULL,
                status     TEXT NOT NULL DEFAULT 'present',
                comment    TEXT,
                UNIQUE(student_id, class_id, subject_id, date)
            );
            CREATE TABLE IF NOT EXISTS teacher_attendance (
                id         SERIAL PRIMARY KEY,
                teacher_id INTEGER NOT NULL REFERENCES teachers(id),
                date       TEXT NOT NULL,
                status     TEXT NOT NULL DEFAULT 'present',
                school_id  INTEGER NOT NULL REFERENCES schools(id),
                comment    TEXT,
                hours      NUMERIC(4,1),
                UNIQUE(teacher_id, date)
            );
            CREATE TABLE IF NOT EXISTS grades (
                id                SERIAL PRIMARY KEY,
                student_id        BIGINT NOT NULL,
                teacher_id        INTEGER NOT NULL REFERENCES teachers(id),
                subject_id        INTEGER NOT NULL REFERENCES subjects(id),
                class_id          INTEGER NOT NULL REFERENCES classes(id),
                criteria          TEXT NOT NULL,
                score             INTEGER NOT NULL,
                date              TEXT NOT NULL,
                comment           TEXT,
                comment_file_id   TEXT,
                comment_file_type TEXT,
                UNIQUE(student_id, subject_id, criteria, date)
            );
            CREATE TABLE IF NOT EXISTS teacher_weekly_schedule (
                id         SERIAL PRIMARY KEY,
                teacher_id INTEGER NOT NULL REFERENCES teachers(id),
                class_id   INTEGER NOT NULL REFERENCES classes(id),
                subject_id INTEGER NOT NULL REFERENCES subjects(id),
                weekday    INTEGER NOT NULL,
                start_time TEXT,
                end_time   TEXT,
                school_id  INTEGER NOT NULL REFERENCES schools(id),
                UNIQUE(teacher_id, class_id, subject_id, weekday)
            );
            CREATE TABLE IF NOT EXISTS student_parents (
                id                  SERIAL PRIMARY KEY,
                student_telegram_id BIGINT NOT NULL REFERENCES whitelist(telegram_id) ON DELETE CASCADE,
                parent_telegram_id  BIGINT NOT NULL UNIQUE,
                label               TEXT NOT NULL DEFAULT 'Ota/Ona',
                added_at            TEXT DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')
            );
            CREATE TABLE IF NOT EXISTS class_groups (
                id         SERIAL PRIMARY KEY,
                group_name TEXT NOT NULL,
                teacher_id INTEGER NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
                subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
                school_id  INTEGER NOT NULL REFERENCES schools(id),
                created_at TEXT DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')
            );
            CREATE TABLE IF NOT EXISTS class_group_members (
                id       SERIAL PRIMARY KEY,
                group_id INTEGER NOT NULL REFERENCES class_groups(id) ON DELETE CASCADE,
                class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
                UNIQUE(group_id, class_id)
            );
        """
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def run_migrations(self):
        """
        Mavjud bazaga yangi ustunlarni xavfsiz qo'shadi.
        Bot har ishga tushganda avtomatik chaqiriladi.
        """
        migrations = [
            # (jadval, ustun, tip)
            ("teacher_attendance", "hours", "NUMERIC(4,1)"),
        ]
        with self.conn() as conn:
            with conn.cursor() as cur:
                for table, column, col_type in migrations:
                    cur.execute("""
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name=%s AND column_name=%s
                    """, (table, column))
                    if not cur.fetchone():
                        cur.execute(
                            f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
                        )
                        import logging
                        logging.getLogger(__name__).info(
                            f"Migration: {table}.{column} ({col_type}) qo'shildi"
                        )
            conn.commit()