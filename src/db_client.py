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
            ORDER BY date ASC, id ASC
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

    def delete_seed(self, seed_id: int) -> None:
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM seed_inventory WHERE id = %s", (seed_id,))
                conn.commit()
        except Exception as e:
            raise DbError(f"Ошибка удаления seed {seed_id}: {e}")

    def list_seeds(self, year: int, limit: int = 500) -> list[dict]:
        sql = """
            SELECT s.id, s.year, s.culture, s.sort,
                   s.quantity, s.quantity_unit,
                   c.expiry_text, c.need, c.need_unit, c.coefficient,
                   s.created_at::text
            FROM seed_inventory s
            LEFT JOIN cultures c ON c.name = s.culture
            WHERE s.year = %s
            ORDER BY s.culture, s.sort
            LIMIT %s
        """
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (year, limit))
                    rows = cur.fetchall()
        except Exception as e:
            raise DbError(f"Ошибка чтения seed_inventory: {e}")

        return [
            {
                "id": r[0],
                "year": r[1],
                "culture": r[2],
                "sort": r[3],
                "quantity": float(r[4]) if r[4] is not None else None,
                "quantity_unit": r[5],
                "expiry_text": r[6],
                "need": float(r[7]) if r[7] is not None else None,
                "need_unit": r[8],
                "coefficient": float(r[9]) if r[9] is not None else None,
                "created_at": r[10],
            }
            for r in rows
        ]

    def create_seed(self, year, culture, sort, quantity, quantity_unit) -> int:
        sql = """
            INSERT INTO seed_inventory
              (year, culture, sort, quantity, quantity_unit)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (year, culture, sort, quantity, quantity_unit))
                    row = cur.fetchone()
                conn.commit()
        except Exception as e:
            raise DbError(f"Ошибка создания seed: {e}")
        return row[0]

    def update_seed(self, seed_id, culture, sort, quantity, quantity_unit) -> None:
        sql = """
            UPDATE seed_inventory
            SET culture=%s, sort=%s, quantity=%s, quantity_unit=%s
            WHERE id=%s
        """
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (culture, sort, quantity, quantity_unit, seed_id))
                conn.commit()
        except Exception as e:
            raise DbError(f"Ошибка обновления seed {seed_id}: {e}")

    def list_cultures(self) -> list[dict]:
        sql = "SELECT id, name FROM cultures ORDER BY name"
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    rows = cur.fetchall()
        except Exception as e:
            raise DbError(f"Ошибка чтения cultures: {e}")
        return [{"id": r[0], "name": r[1]} for r in rows]

    def list_seed_years(self) -> list[int]:
        sql = "SELECT DISTINCT year FROM seed_inventory ORDER BY year DESC"
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    rows = cur.fetchall()
        except Exception as e:
            raise DbError(f"Ошибка чтения годов seed_inventory: {e}")
        return [r[0] for r in rows]

    def list_plans(self, limit: int = 500) -> list[dict]:
        sql = """
            SELECT id, month_start, day_start, month_end, day_end,
                   culture, description, done, created_at::text
            FROM plans
            ORDER BY culture, month_start, day_start
            LIMIT %s
        """
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (limit,))
                    rows = cur.fetchall()
        except Exception as e:
            raise DbError(f"Ошибка чтения plans: {e}")

        return [
            {
                "id": r[0],
                "month_start": r[1],
                "day_start": r[2],
                "month_end": r[3],
                "day_end": r[4],
                "culture": r[5],
                "description": r[6],
                "done": bool(r[7]),
                "created_at": r[8],
            }
            for r in rows
        ]

    def create_plan(self, month_start, day_start, month_end, day_end, culture, description, done=False) -> int:
        sql = """
            INSERT INTO plans (month_start, day_start, month_end, day_end, culture, description, done)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (month_start, day_start, month_end, day_end, culture, description, done))
                    row = cur.fetchone()
                conn.commit()
        except Exception as e:
            raise DbError(f"Ошибка создания plan: {e}")
        return row[0]

    def set_plan_done(self, plan_id: int, done: bool) -> None:
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE plans SET done = %s WHERE id = %s", (done, plan_id))
                conn.commit()
        except Exception as e:
            raise DbError(f"Ошибка обновления plan {plan_id}: {e}")

    def delete_plan(self, plan_id: int) -> None:
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM plans WHERE id = %s", (plan_id,))
                conn.commit()
        except Exception as e:
            raise DbError(f"Ошибка удаления plan {plan_id}: {e}")
