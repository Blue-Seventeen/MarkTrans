import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), 'res/database.db')

def get_db_connection():
    if not os.path.exists(os.path.dirname(DB_FILE)):
        os.makedirs(os.path.dirname(DB_FILE))
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table 1: Mapping-Base
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mapping_base (
            id INTEGER PRIMARY KEY,
            element_name TEXT NOT NULL,
            element_name_en TEXT,
            element_description TEXT,
            element_category TEXT,
            weight INTEGER,
            ast_example_input TEXT,
            ast_example_output TEXT,
            element_regex_rule TEXT,
            element_handler_name TEXT
        )
    ''')

    # Table 2: Mapping-Style
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mapping_style (
            id INTEGER PRIMARY KEY,
            style_name TEXT NOT NULL,
            is_active INTEGER DEFAULT 0,
            is_deletable INTEGER DEFAULT 1,
            remark TEXT
        )
    ''')

    # Table 3: Mapping-Rule
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mapping_rule (
            style_id INTEGER,
            base_id INTEGER,
            match_pattern TEXT,
            replace_result TEXT,
            FOREIGN KEY (style_id) REFERENCES mapping_style (id),
            FOREIGN KEY (base_id) REFERENCES mapping_base (id),
            PRIMARY KEY (style_id, base_id)
        )
    ''')

    # Initialize Data if empty
    cursor.execute('SELECT count(*) FROM mapping_base')
    if cursor.fetchone()[0] == 0:
        base_data = [
            (1, '一级标题', '# ', 'Block', 10),
            (2, '二级标题', '## ', 'Block', 11),
            (3, '三级标题', '### ', 'Block', 12),
            (4, '四级标题', '#### ', 'Block', 13),
            (5, '五级标题', '##### ', 'Block', 14),
            (6, '六级标题', '###### ', 'Block', 15),
            (7, '粗体', '** **', 'Inline', 40),
            (8, '斜体', '* *', 'Inline', 41),
            (9, '删除线', '~~ ~~', 'Inline', 42),
            (10, '高亮', '== ==', 'Inline', 36),
            (13, '外部链接', '[text](url)', 'Inline', 50),
            (14, '本地图片', '![[img]]', 'Inline', 45),
            (15, '外部图片', '![text](url)', 'Inline', 45),
            (16, '引用', '> content', 'Block', 20),
            (30, '无序列表', '- item', 'Block', 27),
            (31, '有序列表', '1. item', 'Block', 27),
            (33, '分割线', '---', 'Block', 25),
            (34, '行内代码', '`code`', 'Inline', 30),
            (35, '代码块', '```code```', 'Block', 26),
            (38, '表格', '|---|', 'Block', 8),
            # Add more as needed based on the Read output, keeping it functional for now
        ]
        cursor.executemany('INSERT INTO mapping_base (id, element_name, element_description, element_category, weight) VALUES (?, ?, ?, ?, ?)', base_data)

    cursor.execute('SELECT count(*) FROM mapping_style')
    if cursor.fetchone()[0] == 0:
        style_data = [
            (1, '默认风格', 1, 0, 'Default Style'),
            (2, '用户自定义风格', 0, 1, 'Custom Style')
        ]
        cursor.executemany('INSERT INTO mapping_style (id, style_name, is_active, is_deletable, remark) VALUES (?, ?, ?, ?, ?)', style_data)

    cursor.execute('SELECT count(*) FROM mapping_rule')
    if cursor.fetchone()[0] == 0:
        # Default rules (Style 1)
        # Regex patterns adapted from common markdown parsers and the user's hint
        rule_data = [
            (1, 1, r'^#\s+(.*)$', r'<h1>\1</h1>'),
            (1, 2, r'^##\s+(.*)$', r'<h2>\1</h2>'),
            (1, 3, r'^###\s+(.*)$', r'<h3>\1</h3>'),
            (1, 4, r'^####\s+(.*)$', r'<h4>\1</h4>'),
            (1, 5, r'^#####\s+(.*)$', r'<h5>\1</h5>'),
            (1, 6, r'^######\s+(.*)$', r'<h6>\1</h6>'),
            (1, 7, r'\*\*(.*?)\*\*', r'<strong>\1</strong>'),
            (1, 8, r'\*(.*?)\*', r'<em>\1</em>'),
            (1, 9, r'~~(.*?)~~', r'<del>\1</del>'),
            (1, 10, r'==(.*?)==', r'<mark>\1</mark>'),
            (1, 13, r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>'),
            (1, 15, r'!\[(.*?)\]\((.*?)\)', r'<img src="\2" alt="\1">'),
            (1, 16, r'(^> .*$\n)+', '__BLOCKQUOTE_HANDLER__'),
            (1, 33, r'^---$', r'<hr>'),
            (1, 34, r'`(.*?)`', r'<code>\1</code>'),
            (1, 35, r'```(\w+)?\n([\s\S]*?)```', r'<pre><code class="language-\1">\2</code></pre>'),
            (1, 38, r'(^\|.*\|$\n)+', '__TABLE_HANDLER__'),
             # Simple list handling (might need complex handler for nested lists, but using regex for simple cases)
            (1, 30, r'^\s*-\s+(.*)$', r'<li>\1</li>'), 
            (1, 31, r'^\s*\d+\.\s+(.*)$', r'<li>\1</li>'),
        ]
        cursor.executemany('INSERT INTO mapping_rule (style_id, base_id, match_pattern, replace_result) VALUES (?, ?, ?, ?)', rule_data)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
