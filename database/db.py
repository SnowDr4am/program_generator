import sqlite3
import json
from typing import List, Dict, Any

class Database:
    def __init__(self, db_path: str = "database/programs.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with open('database/schema.sql', 'r') as f:
            schema = f.read()
        
        with self.get_connection() as conn:
            conn.executescript(schema)

    def save_program(self, title: str, description: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO programs (title, description) VALUES (?, ?)",
                (title, description)
            )
            return cursor.lastrowid

    def get_all_programs(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT id, title, description FROM programs")
            return [{"id": row[0], "title": row[1], "description": row[2]} for row in cursor.fetchall()]

    def save_course_plan(self, program_id: int, plan_data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO course_plans (program_id, plan_data) VALUES (?, ?)",
                (program_id, json.dumps(plan_data))
            )
            return cursor.lastrowid

    def get_course_plan(self, program_id: int) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT plan_data FROM course_plans WHERE program_id = ? ORDER BY created_at DESC LIMIT 1",
                (program_id,)
            )
            row = cursor.fetchone()
            return json.loads(row[0]) if row else None

    def save_lecture(self, course_plan_id: int, theme: str, content: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO lectures (course_plan_id, theme, content) VALUES (?, ?, ?)",
                (course_plan_id, theme, json.dumps(content))
            )
            return cursor.lastrowid

    def get_lecture(self, course_plan_id: int, theme: str) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT content FROM lectures WHERE course_plan_id = ? AND theme = ?",
                (course_plan_id, theme)
            )
            row = cursor.fetchone()
            return json.loads(row[0]) if row else None

    def get_program_by_id(self, program_id: int) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, title, description FROM programs WHERE id = ?",
                (program_id,)
            )
            row = cursor.fetchone()
            return {"id": row[0], "title": row[1], "description": row[2]} if row else None

    def update_course_plan(self, program_id: int, plan_data: Dict[str, Any]):
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE course_plans SET plan_data = ? WHERE program_id = ?",
                (json.dumps(plan_data), program_id)
            ) 