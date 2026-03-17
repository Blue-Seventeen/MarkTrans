import os
import sqlite3

PROJECT_ROOT = os.path.dirname(__file__)
TEMPLATE_DB_FILE = os.path.join(PROJECT_ROOT, 'res', 'database_template.db')
DB_FILE = os.path.join(PROJECT_ROOT, 'res', 'database.db')


def _ensure_parent_dir(file_path: str) -> None:
    parent = os.path.dirname(file_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent)


def _copy_database(src_path: str, dst_path: str) -> None:
    src_conn = sqlite3.connect(src_path)
    dst_conn = sqlite3.connect(dst_path)
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()


def _mapping_rule_style_rule_name_is_unique(conn: sqlite3.Connection) -> bool:
    cursor = conn.cursor()
    indexes = cursor.execute("PRAGMA index_list(mapping_rule)").fetchall()
    for index in indexes:
        is_unique = int(index[2]) == 1
        if not is_unique:
            continue
        index_name = index[1]
        columns = [row[2] for row in cursor.execute(f"PRAGMA index_info({index_name})").fetchall()]
        if columns == ["style_rule_name"]:
            return True
    return False


def _remove_mapping_rule_unique_constraint(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        if not _mapping_rule_style_rule_name_is_unique(conn):
            return
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute("BEGIN")
        cursor.execute(
            """
            CREATE TABLE mapping_rule_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                style_id INTEGER,
                style_rule_name TEXT,
                ast_input TEXT,
                matching_rule TEXT,
                html_output TEXT,
                render_name TEXT,
                weight INTEGER DEFAULT 0,
                FOREIGN KEY (style_id) REFERENCES mapping_style (id)
            )
            """
        )
        cursor.execute(
            """
            INSERT INTO mapping_rule_new (
                id, style_id, style_rule_name, ast_input, matching_rule, html_output, render_name, weight
            )
            SELECT
                id, style_id, style_rule_name, ast_input, matching_rule, html_output, render_name, weight
            FROM mapping_rule
            ORDER BY id ASC
            """
        )
        cursor.execute("DROP TABLE mapping_rule")
        cursor.execute("ALTER TABLE mapping_rule_new RENAME TO mapping_rule")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mapping_rule_style_rule_name ON mapping_rule(style_rule_name)")
        max_id = cursor.execute("SELECT COALESCE(MAX(id), 0) FROM mapping_rule").fetchone()[0]
        has_sqlite_sequence = cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sqlite_sequence' LIMIT 1"
        ).fetchone() is not None
        if has_sqlite_sequence:
            updated = cursor.execute(
                "UPDATE sqlite_sequence SET seq = ? WHERE name = 'mapping_rule'",
                (max_id,)
            ).rowcount
            if updated == 0:
                cursor.execute(
                    "INSERT INTO sqlite_sequence(name, seq) VALUES('mapping_rule', ?)",
                    (max_id,)
                )
        cursor.execute("COMMIT")
        cursor.execute("PRAGMA foreign_keys = ON")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _resequence_mapping_rule_id(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT id FROM mapping_rule ORDER BY id ASC").fetchall()
        for new_id, (old_id,) in enumerate(rows, start=1):
            if old_id != new_id:
                cursor.execute("UPDATE mapping_rule SET id = ? WHERE id = ?", (-new_id, old_id))
        cursor.execute("UPDATE mapping_rule SET id = -id WHERE id < 0")
        next_id = len(rows)
        has_sqlite_sequence = cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sqlite_sequence' LIMIT 1"
        ).fetchone() is not None
        if has_sqlite_sequence:
            updated = cursor.execute(
                "UPDATE sqlite_sequence SET seq = ? WHERE name = 'mapping_rule'",
                (next_id,)
            ).rowcount
            if updated == 0:
                cursor.execute(
                    "INSERT INTO sqlite_sequence(name, seq) VALUES('mapping_rule', ?)",
                    (next_id,)
                )
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    if os.path.exists(TEMPLATE_DB_FILE):
        _remove_mapping_rule_unique_constraint(TEMPLATE_DB_FILE)
    if os.path.exists(DB_FILE):
        _remove_mapping_rule_unique_constraint(DB_FILE)
        return
    if not os.path.exists(TEMPLATE_DB_FILE):
        raise FileNotFoundError(f"模板数据库不存在: {TEMPLATE_DB_FILE}")
    _ensure_parent_dir(DB_FILE)
    _copy_database(TEMPLATE_DB_FILE, DB_FILE)
    _remove_mapping_rule_unique_constraint(DB_FILE)
    _resequence_mapping_rule_id(DB_FILE)


def get_db_connection():
    if not os.path.exists(DB_FILE):
        init_db()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == '__main__':
    init_db()
