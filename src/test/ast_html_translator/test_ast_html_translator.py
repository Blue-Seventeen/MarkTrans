
import sys
import os
import json

# Add src/main to sys.path to import modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_src_path = os.path.dirname(os.path.dirname(current_dir)) # src/test/.. -> src
main_path = os.path.join(project_src_path, "main/ast_html_translator")
if main_path not in sys.path:
    sys.path.insert(0, main_path)

from ast_html_translator import ASTHtmlTranslator

def test_translate():
    # 1. Load the test JSON AST
    json_path = os.path.join(project_src_path, "test/markdown_ast_parser/test.json")
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found at {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        ast_tokens = json.load(f)

    # 2. Translate to HTML
    translator = ASTHtmlTranslator()
    html_output = translator.translate(ast_tokens)

    # 3. Save output
    output_path = os.path.join(current_dir, "test_output.html")
    
    # Add a simple HTML wrapper for viewing in browser
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
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_html)
        
    print(f"HTML output saved to: {output_path}")
    
    # Print a snippet to console
    print("\n--- HTML Snippet (First 500 chars) ---")
    print(html_output[:500])
    print("...")

if __name__ == "__main__":
    test_translate()
