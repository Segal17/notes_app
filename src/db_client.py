import psycopg


class DbError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotesDb:
    def __init__(self, host: str, port: int, dbname: str, user: str, password: str):
        self.dsn = (
            f"host={host} port={port} dbname={dbname} "
            f"user={user} password={password} connect_timeout=5"
        )

    def health(self) -> bool:
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return True
        except Exception as e:
            raise DbError(f"Нет связи с БД: {e}")

    def create_note(self, culture: str | None, description: str | None, date: str) -> dict:
        sql = """
            INSERT INTO notes (culture, description, date)
            VALUES (%s, %s, COALESCE(%s, CURRENT_DATE))
            RETURNING id, created_at::text, date::text, culture, description
        """
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (culture, description, date))
                    row = cur.fetchone()
                conn.commit()
        except Exception as e:
            raise DbError(f"Ошибка записи в БД: {e}")

        return {
            "id": row[0],
            "created_at": row[1],
            "date": row[2],
            "culture": row[3],
            "description": row[4],
        }

    def list_notes(self, limit: int = 500) -> list[dict]:
        sql = """
            SELECT id, created_at::text, date::text, culture, description
            FROM notes
            ORDER BY date DESC, id DESC
            LIMIT %s
        """
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (limit,))
                    rows = cur.fetchall()
        except Exception as e:
            raise DbError(f"Ошибка чтения из БД: {e}")

        return [
            {
                "id": r[0],
                "created_at": r[1],
                "date": r[2],
                "culture": r[3],
                "description": r[4],
            }
            for r in rows
        ]

    def update_note(self, note_id: int, culture: str | None, description: str | None) -> None:
        sql = """
            UPDATE notes
            SET culture = %s, description = %s
            WHERE id = %s
        """
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (culture, description, note_id))
                conn.commit()
        except Exception as e:
            raise DbError(f"Ошибка обновления записи {note_id}: {e}")

    def delete_note(self, note_id: int) -> None:
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM notes WHERE id = %s", (note_id,))
                conn.commit()
        except Exception as e:
            raise DbError(f"Ошибка удаления записи {note_id}: {e}")
