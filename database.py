
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
    # Updated to match the new schema requirements
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mapping_rule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            style_id INTEGER,
            style_rule_name TEXT UNIQUE,
            ast_input TEXT,
            matching_rule TEXT,
            html_output TEXT,
            render_name TEXT,
            weight INTEGER DEFAULT 0,
            FOREIGN KEY (style_id) REFERENCES mapping_style (id),
            UNIQUE(style_rule_name)
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
        # Regex patterns adapted from common markdown parsers
        # Updated columns: style_id, base_id, matching_rule, html_output
        rule_data = [
            (1, 'heading_h1', '', r'^#\s+(.*)$', r'<h1>\1</h1>', 'render_heading', 100),
            (1, 'heading_h2', '', r'^##\s+(.*)$', r'<h2>\1</h2>', 'render_heading', 99),
            (1, 'heading_h3', '', r'^###\s+(.*)$', r'<h3>\1</h3>', 'render_heading', 98),
            (1, 'heading_h4', '', r'^####\s+(.*)$', r'<h4>\1</h4>', 'render_heading', 97),
            (1, 'heading_h5', '', r'^#####\s+(.*)$', r'<h5>\1</h5>', 'render_heading', 96),
            (1, 'heading_h6', '', r'^######\s+(.*)$', r'<h6>\1</h6>', 'render_heading', 95),
            (1, 'inline_strong', '', r'\*\*(.*?)\*\*', r'<strong>\1</strong>', 'render_strong', 90),
            (1, 'inline_em', '', r'\*(.*?)\*', r'<em>\1</em>', 'render_italic', 89),
            (1, 'inline_del', '', r'~~(.*?)~~', r'<del>\1</del>', 'render_del', 88),
            (1, 'inline_mark', '', r'==(.*?)==', r'<mark>\1</mark>', 'render_mark', 87),
            (1, 'inline_link', '', r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', 'render_link', 86),
            (1, 'inline_image', '', r'!\[(.*?)\]\((.*?)\)', r'<img src="\2" alt="\1">', 'render_image', 85),
            (1, 'block_quote', '', r'(^> .*$\n)+', '__BLOCKQUOTE_HANDLER__', 'render_blockquote', 80),
            (1, 'block_hr', '', r'^---$', r'<hr>', 'render_hr', 79),
            (1, 'inline_code', '', r'`(.*?)`', r'<code>\1</code>', 'render_codespan', 78),
            (1, 'block_code', '', r'```(\w+)?\n([\s\S]*?)```', r'<pre><code class="language-\1">\2</code></pre>', 'render_codeblock', 77),
            (1, 'block_table', '', r'(^\|.*\|$\n)+', '__TABLE_HANDLER__', 'render_table', 76),
            (1, 'list_unordered', '', r'^\s*-\s+(.*)$', r'<li>\1</li>', 'render_list_item', 75),
            (1, 'list_ordered', '', r'^\s*\d+\.\s+(.*)$', r'<li>\1</li>', 'render_list_item', 74),
        ]
        cursor.executemany(
            'INSERT INTO mapping_rule (style_id, style_rule_name, ast_input, matching_rule, html_output, render_name, weight) VALUES (?, ?, ?, ?, ?, ?, ?)',
            rule_data
        )

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
