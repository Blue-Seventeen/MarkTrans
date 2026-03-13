import sys
import os
import json
from markdown_ast_parser import MarkdownASTParser
import re

parser = MarkdownASTParser(db_path = r'../../../res/database.db')
base_dir = os.path.dirname(__file__)
with open(os.path.join(base_dir, "test_inline.md"), "r", encoding="utf-8") as f:
    content = f.read()

# print("========== Origion Text ==========")
# print(content)

result = parser.parse(content)
print(json.dumps(result, ensure_ascii=False, indent=2))

with open(os.path.join(base_dir, "test.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)


# #  12\|3\|
# print(parse_row(content))