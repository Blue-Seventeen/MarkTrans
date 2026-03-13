from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
import os
import sqlite3
# from md_parser import MarkdownParser
from database import init_db, get_db_connection

app = Flask(__name__, static_folder='res/static', template_folder='res/templates')

# Global variable to store image path (simple version for single user local tool)
CURRENT_IMAGE_DIR = ''

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

# --- DB API Endpoints ---

@app.route('/api/db/tables', methods=['GET'])
def get_tables():
    # Return list of tables we want to expose
    return jsonify(['mapping_base', 'mapping_style', 'mapping_rule'])

@app.route('/api/db/<table_name>', methods=['GET'])
def get_table_data(table_name):
    if table_name not in ['mapping_base', 'mapping_style', 'mapping_rule']:
        return jsonify({'error': 'Invalid table'}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = f"SELECT * FROM {table_name}"
    if table_name == 'mapping_base':
        query += " ORDER BY weight DESC"
        
    cursor.execute(query)
    rows = cursor.fetchall()
    
    # Convert rows to dicts
    result = [dict(row) for row in rows]
    conn.close()
    return jsonify(result)

@app.route('/api/db/<table_name>', methods=['POST'])
def add_table_row(table_name):
    if table_name not in ['mapping_base', 'mapping_style', 'mapping_rule']:
        return jsonify({'error': 'Invalid table'}), 400
        
    data = request.json
    keys = data.keys()
    values = [data[k] for k in keys]
    placeholders = ', '.join(['?'] * len(keys))
    columns = ', '.join(keys)
    
    conn = get_db_connection()
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
        
    data = request.json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if table_name == 'mapping_rule':
            # Composite key
            style_id = data.get('style_id')
            base_id = data.get('base_id')
            cursor.execute(f"DELETE FROM {table_name} WHERE style_id=? AND base_id=?", (style_id, base_id))
        else:
            # Single ID
            id_val = data.get('id')
            cursor.execute(f"DELETE FROM {table_name} WHERE id=?", (id_val,))
            
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500
        
    conn.close()
    return jsonify({'success': True})

@app.route('/api/db/<table_name>/update', methods=['POST'])
def update_table_row(table_name):
    if table_name not in ['mapping_base', 'mapping_style', 'mapping_rule']:
        return jsonify({'error': 'Invalid table'}), 400
        
    data = request.json
    updates = data.get('updates', {})
    
    if not updates:
        return jsonify({'error': 'No updates provided'}), 400

    set_clause = ', '.join([f"{k}=?" for k in updates.keys()])
    values = list(updates.values())
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if table_name == 'mapping_rule':
            # Composite key identifier
            style_id = data.get('style_id')
            base_id = data.get('base_id')
            values.append(style_id)
            values.append(base_id)
            cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE style_id=? AND base_id=?", values)
        else:
            # Single ID identifier
            id_val = data.get('id')
            values.append(id_val)
            cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE id=?", values)
            
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500
        
    conn.close()
    return jsonify({'success': True})

# --- End DB API ---

@app.route('/api/translate', methods=['POST'])
def translate():
    global CURRENT_IMAGE_DIR
    data = request.json
    markdown_text = data.get('content', '')
    file_path = data.get('filePath', '')
    image_dir = data.get('imageDir', '')
    
    loaded_content = None
    
    # If file path provided, read from file
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                markdown_text = f.read()
            loaded_content = markdown_text
            
            # If image_dir not provided, default to file's directory
            if not image_dir:
                image_dir = os.path.dirname(file_path)
        except Exception as e:
            return jsonify({'error': str(e)}), 400
            
    if image_dir and os.path.isdir(image_dir):
        CURRENT_IMAGE_DIR = image_dir
    
    parser = MarkdownParser()
    html_content = parser.parse(markdown_text)
    
    response_data = {'html': html_content}
    if loaded_content:
        response_data['loadedContent'] = loaded_content
        
    return jsonify(response_data)

@app.route('/<path:filename>')
def serve_image(filename):
    # Try to serve static files first (like css)
    if filename.endswith('.css') or filename.endswith('.js'):
         return send_from_directory('res/static', filename)
         
    # If not static, try to serve from CURRENT_IMAGE_DIR
    global CURRENT_IMAGE_DIR
    if CURRENT_IMAGE_DIR and os.path.exists(os.path.join(CURRENT_IMAGE_DIR, filename)):
        return send_from_directory(CURRENT_IMAGE_DIR, filename)
    
    # Also check if the filename itself is an absolute path (unlikely from browser but possible logic)
    if os.path.exists(filename):
        return send_file(filename)
        
    return "File not found", 404

if __name__ == '__main__':
    # Initialize DB on start
    init_db()
    app.run(debug=True, port=7000)
