
import sys
import os
import json

# Add src/main to sys.path to import modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_src_path = os.path.dirname(os.path.dirname(current_dir)) # src/test/.. -> src
markdown_ast_parser_path = os.path.join(project_src_path, "main/markdown_ast_parser")
ast_html_translator_path = os.path.join(project_src_path, "main/ast_html_translator")
if markdown_ast_parser_path not in sys.path:
    sys.path.insert(0, markdown_ast_parser_path)
if ast_html_translator_path not in sys.path:
    sys.path.insert(0, ast_html_translator_path)

from markdown_ast_parser import MarkdownASTParser
from ast_html_translator import ASTHtmlTranslator

class ASTHtmlTranslatorTest(ASTHtmlTranslator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    


if __name__ == "__main__":
    db_path = r'../../../res/database.db'
    parser = MarkdownASTParser(db_path = db_path)
    translator = ASTHtmlTranslatorTest(db_path = db_path)

    # 1. 读取 test.md 中的内容
    content = ""
    with open("test.md", 'r', encoding='utf-8') as f:
         content = f.read()
    print("================= Markdown Content =================\n")
    print(content)
    # 2. 解析 Markdown 内容为 AST
    ast_tokens = parser.parse(content)
    print("\n==================== AST Tokens ===================\n")
    print(ast_tokens)
    # 3. 将 AST 转换为 HTML
    print("\n==================== HTML Output ===================\n")
    html_output = translator.translate(ast_tokens)
    print(html_output)
    
    # 4. 将生成的完整 HTML 代码输出到一个文件中
    full_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Markdown AST to HTML Test</title>
    <link rel="stylesheet" href="../../../res/static/style.css">
    <style>
        /* Override global styles that might affect layout */
        body {{ 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px; 
            font-family: system-ui;
            /* Fix: Override flex display from style.css */
            display: block !important; 
            height: auto !important;
            overflow: auto !important;
        }}
        .callout {{ border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 4px; }}
        .callout-title {{ font-weight: bold; margin-bottom: 5px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; }}
        pre {{ background: #f4f4f4; padding: 10px; overflow-x: auto; }}
        blockquote {{ border-left: 4px solid #ddd; margin: 0; padding-left: 10px; color: #666; }}
    </style>
</head>
<body>
    <h1>Markdown Translation Result</h1>
    <hr>
    {html_output}
</body>
</html>
    """

    with open("test.html", "w", encoding="utf-8") as f:
        f.write(full_html)