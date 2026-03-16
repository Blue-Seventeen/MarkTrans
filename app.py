from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
import os
import sys
from pathlib import Path
from database import init_db, get_db_connection, DB_FILE

PROJECT_ROOT = Path(__file__).resolve().parent
MAIN_SRC_PATH = PROJECT_ROOT / "src" / "main"
if str(MAIN_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(MAIN_SRC_PATH))

from markdown_ast_parser.markdown_ast_parser import MarkdownASTParser
from ast_html_translator.ast_html_translator import ASTHtmlTranslator

app = Flask(__name__, static_folder='res/static', template_folder='res/templates')
CURRENT_IMAGE_DIR = ''


def get_table_columns(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def normalize_rule_name(conn, style_rule_name):
    candidate = (style_rule_name or "").strip() or "rule"
    cursor = conn.cursor()
    seq = 1
    while True:
        cursor.execute("SELECT 1 FROM mapping_rule WHERE style_rule_name = ? LIMIT 1", (candidate,))
        if cursor.fetchone() is None:
            return candidate
        seq += 1
        candidate = f"{style_rule_name}_{seq}"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/styles')
def styles_page():
    return render_template('styles.html')


@app.route('/admin')
def admin():
    return render_template('admin.html')


@app.route('/docs')
def docs():
    return render_template('docs.html')


@app.route('/api/style/list', methods=['GET'])
def get_style_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, style_name, is_active, is_deletable, remark FROM mapping_style ORDER BY id ASC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route('/api/style/activate', methods=['POST'])
def activate_style():
    data = request.json or {}
    style_id = data.get('id')
    if style_id is None:
        return jsonify({'error': 'Style id required'}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE mapping_style SET is_active = 0")
        cursor.execute("UPDATE mapping_style SET is_active = 1 WHERE id = ?", (style_id,))
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Style not found'}), 404
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500
    conn.close()
    return jsonify({'success': True})


@app.route('/api/style/clone', methods=['POST'])
def clone_style():
    data = request.json or {}
    base_style_id = data.get('base_style_id')
    style_name = (data.get('style_name') or '').strip()
    if not base_style_id or not style_name:
        return jsonify({'error': 'base_style_id and style_name required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO mapping_style (style_name, is_active, is_deletable, remark) VALUES (?, 1, 1, ?)", (style_name, f'Cloned from {base_style_id}'))
        new_style_id = cursor.lastrowid
        cursor.execute("UPDATE mapping_style SET is_active = 0 WHERE id <> ?", (new_style_id,))

        cursor.execute("""
            SELECT style_rule_name, ast_input, matching_rule, html_output, render_name, weight
            FROM mapping_rule
            WHERE style_id = ?
            ORDER BY id ASC
        """, (base_style_id,))
        base_rules = cursor.fetchall()

        for rule in base_rules:
            original_name = rule["style_rule_name"]
            new_rule_name = normalize_rule_name(conn, f"{original_name}_{new_style_id}")
            cursor.execute("""
                INSERT INTO mapping_rule (style_id, style_rule_name, ast_input, matching_rule, html_output, render_name, weight)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (new_style_id, new_rule_name, rule["ast_input"], rule["matching_rule"], rule["html_output"], rule["render_name"], rule["weight"]))

        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

    conn.close()
    return jsonify({'success': True, 'id': new_style_id})


@app.route('/api/db/tables', methods=['GET'])
def get_tables():
    return jsonify(['mapping_base', 'mapping_style', 'mapping_rule'])


@app.route('/api/db/query', methods=['POST'])
def run_db_query():
    data = request.json or {}
    sql = (data.get('sql') or '').strip()
    if not sql:
        return jsonify({'error': 'SQL is required'}), 400
    sql_lower = sql.lower().strip().rstrip(';')
    if not (sql_lower.startswith('select ') or sql_lower.startswith('pragma ')):
        return jsonify({'error': '仅允许执行 SELECT 或 PRAGMA 查询'}), 400
    if ';' in sql_lower:
        return jsonify({'error': '仅允许单条查询语句'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()]
        columns = [col[0] for col in (cursor.description or [])]
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 400
    conn.close()
    return jsonify({'columns': columns, 'rows': rows})


@app.route('/api/db/<table_name>', methods=['GET'])
def get_table_data(table_name):
    if table_name not in ['mapping_base', 'mapping_style', 'mapping_rule']:
        return jsonify({'error': 'Invalid table'}), 400

    conn = get_db_connection()
    columns = get_table_columns(conn, table_name)
    sort_by = request.args.get('sort_by')
    order = (request.args.get('order') or 'asc').lower()
    if order not in ['asc', 'desc']:
        order = 'asc'

    query = f"SELECT * FROM {table_name}"
    if sort_by and sort_by in columns:
        query += f" ORDER BY {sort_by} {order.upper()}"
    elif table_name == 'mapping_base':
        query += " ORDER BY weight DESC"
    elif table_name == 'mapping_rule':
        query += " ORDER BY style_id ASC, weight DESC"

    cursor = conn.cursor()
    cursor.execute(query)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route('/api/db/<table_name>', methods=['POST'])
def add_table_row(table_name):
    if table_name not in ['mapping_base', 'mapping_style', 'mapping_rule']:
        return jsonify({'error': 'Invalid table'}), 400

    data = request.json or {}
    conn = get_db_connection()
    valid_columns = set(get_table_columns(conn, table_name))
    payload = {k: v for k, v in data.items() if k in valid_columns}
    keys = list(payload.keys())
    values = [payload[k] for k in keys]
    placeholders = ', '.join(['?'] * len(keys))
    columns = ', '.join(keys)
    cursor = conn.cursor()
    try:
        cursor.execute(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", values)
        conn.commit()
        new_id = cursor.lastrowid
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500
    conn.close()
    return jsonify({'success': True, 'id': new_id})


@app.route('/api/db/<table_name>/delete', methods=['POST'])
def delete_table_row(table_name):
    if table_name not in ['mapping_base', 'mapping_style', 'mapping_rule']:
        return jsonify({'error': 'Invalid table'}), 400

    data = request.json or {}
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if table_name == 'mapping_rule':
            id_val = data.get('id')
            if id_val is not None:
                cursor.execute(f"DELETE FROM {table_name} WHERE id=?", (id_val,))
            else:
                style_id = data.get('style_id')
                style_rule_name = data.get('style_rule_name')
                cursor.execute(f"DELETE FROM {table_name} WHERE style_id=? AND style_rule_name=?", (style_id, style_rule_name))
        elif table_name == 'mapping_style':
            id_val = data.get('id')
            if id_val is None:
                conn.close()
                return jsonify({'error': 'Style id required'}), 400
            if int(id_val) == 1:
                conn.close()
                return jsonify({'error': '系统默认风格不可删除'}), 400
            cursor.execute("SELECT id, is_active FROM mapping_style WHERE id = ? LIMIT 1", (id_val,))
            style_row = cursor.fetchone()
            if style_row is None:
                conn.close()
                return jsonify({'error': 'Record not found'}), 404
            was_active = int(style_row["is_active"] or 0) == 1
            cursor.execute("DELETE FROM mapping_rule WHERE style_id = ?", (id_val,))
            cursor.execute("DELETE FROM mapping_style WHERE id = ?", (id_val,))
            if was_active:
                cursor.execute("UPDATE mapping_style SET is_active = 0")
                cursor.execute("UPDATE mapping_style SET is_active = 1 WHERE id = 1")
        else:
            id_val = data.get('id')
            cursor.execute(f"DELETE FROM {table_name} WHERE id=?", (id_val,))

        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Record not found'}), 404
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500
    conn.close()
    return jsonify({'success': True})


@app.route('/api/db/<table_name>/update', methods=['POST'])
def update_table_row(table_name):
    if table_name not in ['mapping_base', 'mapping_style', 'mapping_rule']:
        return jsonify({'error': 'Invalid table'}), 400

    data = request.json or {}
    updates = dict(data.get('updates', {}))
    if not updates:
        return jsonify({'error': 'No updates provided'}), 400
    if table_name == 'mapping_rule':
        updates.pop('id', None)
        if not updates:
            return jsonify({'error': 'No updatable fields provided'}), 400

    conn = get_db_connection()
    valid_columns = set(get_table_columns(conn, table_name))
    updates = {k: v for k, v in updates.items() if k in valid_columns}
    set_clause = ', '.join([f"{k}=?" for k in updates.keys()])
    values = list(updates.values())
    cursor = conn.cursor()
    try:
        if table_name == 'mapping_rule':
            id_val = data.get('id')
            if id_val is not None:
                values.append(id_val)
                cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE id=?", values)
            else:
                style_id = data.get('style_id')
                style_rule_name = data.get('style_rule_name')
                values.append(style_id)
                values.append(style_rule_name)
                cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE style_id=? AND style_rule_name=?", values)
        else:
            id_val = data.get('id')
            values.append(id_val)
            cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE id=?", values)
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Record not found'}), 404
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500
    conn.close()
    return jsonify({'success': True})


@app.route('/api/path/pick', methods=['POST'])
def pick_local_path():
    try:
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        file_path = filedialog.askopenfilename(
            title='选择 Markdown 文件',
            filetypes=[('Markdown Files', '*.md *.markdown *.txt'), ('All Files', '*.*')]
        )
        if file_path:
            root.destroy()
            return jsonify({'kind': 'file', 'path': file_path})
        folder_path = filedialog.askdirectory(title='选择附件目录')
        root.destroy()
        if folder_path:
            return jsonify({'kind': 'folder', 'path': folder_path})
        return jsonify({'kind': 'none', 'path': ''})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/translate', methods=['POST'])
def translate():
    global CURRENT_IMAGE_DIR
    data = request.json or {}
    markdown_text = data.get('content', '')
    file_path = data.get('filePath', '')
    image_dir = data.get('imageDir', '')
    style_id = data.get('styleId')
    loaded_content = None

    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                markdown_text = f.read()
            loaded_content = markdown_text
            if not image_dir:
                image_dir = os.path.dirname(file_path)
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    if image_dir and os.path.isdir(image_dir):
        CURRENT_IMAGE_DIR = image_dir

    conn = get_db_connection()
    if style_id is not None:
        cursor = conn.cursor()
        cursor.execute("UPDATE mapping_style SET is_active = 0")
        cursor.execute("UPDATE mapping_style SET is_active = 1 WHERE id = ?", (style_id,))
        conn.commit()
    conn.close()
    
    if CURRENT_IMAGE_DIR != None:
        parser = MarkdownASTParser(DB_FILE, attachment_directory_path=CURRENT_IMAGE_DIR)
    else:
        parser = MarkdownASTParser(DB_FILE)

    ast_tokens = parser.parse(markdown_text, 'block')
    translator = ASTHtmlTranslator(DB_FILE)
    html_content = translator.translate(ast_tokens)

    response_data = {'html': html_content, 'ast': ast_tokens}
    if loaded_content:
        response_data['loadedContent'] = loaded_content
    return jsonify(response_data)


@app.route('/<path:filename>')
def serve_image(filename):
    if filename.endswith('.css') or filename.endswith('.js'):
        return send_from_directory('res/static', filename)
    global CURRENT_IMAGE_DIR
    if CURRENT_IMAGE_DIR and os.path.exists(os.path.join(CURRENT_IMAGE_DIR, filename)):
        return send_from_directory(CURRENT_IMAGE_DIR, filename)
    if os.path.exists(filename):
        return send_file(filename)
    return "File not found", 404


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=7000)
