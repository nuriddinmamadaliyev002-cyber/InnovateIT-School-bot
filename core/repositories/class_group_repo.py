"""
core/repositories/class_group_repo.py — Sinf guruhlari repository
"""
import psycopg2.extras
from core.database import BaseDB


class ClassGroupRepo(BaseDB):

    def _fetchone(self, conn, query, params=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def _fetchall(self, conn, query, params=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall() or []

    # ── Guruh yaratish ───────────────────────────────────────────

    def create_group(self, teacher_id: int, subject_id: int, school_id: int, 
                     class_ids: list, group_name: str = None) -> int:
        """
        Sinf guruhi yaratish.
        
        Args:
            teacher_id: O'qituvchi ID
            subject_id: Fan ID
            school_id: Maktab ID
            class_ids: Sinflar ID ro'yxati [1, 2, 3]
            group_name: Guruh nomi (opsional)
        
        Returns:
            group_id: Yaratilgan guruh ID
        """
        if not group_name:
            # Avtomatik nom: "1-sinf, 2-sinf, 3-sinf"
            from config import db
            classes = [db.get_class(cid) for cid in class_ids if cid]
            group_name = ", ".join(c['name'] for c in classes if c)
        
        with self.conn() as conn:
            with conn.cursor() as cur:
                # Guruh yaratish
                cur.execute("""
                    INSERT INTO class_groups (group_name, teacher_id, subject_id, school_id)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (group_name, teacher_id, subject_id, school_id))
                group_id = cur.fetchone()[0]
                
                # Sinflarni qo'shish
                for class_id in class_ids:
                    cur.execute("""
                        INSERT INTO class_group_members (group_id, class_id)
                        VALUES (%s, %s)
                        ON CONFLICT (group_id, class_id) DO NOTHING
                    """, (group_id, class_id))
            conn.commit()
        return group_id

    # ── Guruhlarni olish ─────────────────────────────────────────

    def get_school_groups(self, school_id: int) -> list:
        """Maktabdagi barcha guruhlar"""
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT cg.*, t.full_name AS teacher_name, s.name AS subject_name,
                       (SELECT COUNT(*) FROM class_group_members WHERE group_id=cg.id) AS class_count
                FROM class_groups cg
                JOIN teachers t ON cg.teacher_id = t.id
                JOIN subjects s ON cg.subject_id = s.id
                WHERE cg.school_id = %s
                ORDER BY cg.created_at DESC
            """, (school_id,))

    def get_teacher_groups(self, teacher_id: int) -> list:
        """O'qituvchining barcha guruhlari"""
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT cg.*, s.name AS subject_name,
                       (SELECT COUNT(*) FROM class_group_members WHERE group_id=cg.id) AS class_count
                FROM class_groups cg
                JOIN subjects s ON cg.subject_id = s.id
                WHERE cg.teacher_id = %s
                ORDER BY cg.created_at DESC
            """, (teacher_id,))

    def get_group(self, group_id: int):
        """Bitta guruhni olish"""
        with self.conn() as conn:
            return self._fetchone(conn, """
                SELECT cg.*, s.name AS subject_name, t.full_name AS teacher_name,
                       (SELECT COUNT(*) FROM class_group_members WHERE group_id=cg.id) AS class_count
                FROM class_groups cg
                JOIN subjects s ON cg.subject_id = s.id
                JOIN teachers t ON cg.teacher_id = t.id
                WHERE cg.id = %s
            """, (group_id,))

    def get_group_classes(self, group_id: int) -> list:
        """Guruhdagi sinflar"""
        with self.conn() as conn:
            return self._fetchall(conn, """
                SELECT c.* FROM classes c
                JOIN class_group_members cgm ON c.id = cgm.class_id
                WHERE cgm.group_id = %s
                ORDER BY c.name
            """, (group_id,))

    def get_group_class_ids(self, group_id: int) -> list:
        """Guruhdagi sinf ID lari"""
        classes = self.get_group_classes(group_id)
        return [c['id'] for c in classes]

    # ── Guruhni tahrirlash ───────────────────────────────────────

    def update_group_name(self, group_id: int, new_name: str):
        """Guruh nomini o'zgartirish"""
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE class_groups SET group_name=%s WHERE id=%s
                """, (new_name, group_id))
            conn.commit()

    def update_group_classes(self, group_id: int, class_ids: list):
        """Guruhdagi sinflarni yangilash"""
        with self.conn() as conn:
            with conn.cursor() as cur:
                # Avvalgi sinflarni o'chirish
                cur.execute("DELETE FROM class_group_members WHERE group_id=%s", (group_id,))
                
                # Yangi sinflarni qo'shish
                for class_id in class_ids:
                    cur.execute("""
                        INSERT INTO class_group_members (group_id, class_id)
                        VALUES (%s, %s)
                    """, (group_id, class_id))
            conn.commit()

    # ── Guruhni o'chirish ────────────────────────────────────────

    def delete_group(self, group_id: int):
        """Guruhni o'chirish (cascade: members ham o'chadi)"""
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM class_groups WHERE id=%s", (group_id,))
            conn.commit()

    # ── Tekshirish funksiyalari ──────────────────────────────────

    def group_exists(self, teacher_id: int, subject_id: int, class_ids: list) -> bool:
        """
        Aynan shu sinf kombinatsiyasiga guruh bormi?
        (Duplicate oldini olish uchun)
        """
        with self.conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Shu fan va o'qituvchidagi barcha guruhlarni olish
                cur.execute("""
                    SELECT id FROM class_groups 
                    WHERE teacher_id=%s AND subject_id=%s
                """, (teacher_id, subject_id))
                groups = cur.fetchall()
                
                for g in groups:
                    # Har bir guruhning sinflarini tekshirish
                    cur.execute("""
                        SELECT class_id FROM class_group_members 
                        WHERE group_id=%s ORDER BY class_id
                    """, (g['id'],))
                    existing_classes = sorted([r['class_id'] for r in cur.fetchall()])
                    
                    if existing_classes == sorted(class_ids):
                        return True
        return False