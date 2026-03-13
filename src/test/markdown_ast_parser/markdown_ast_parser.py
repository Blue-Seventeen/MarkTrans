"""
用于测试数据库中的正则与优先级是否配置正确
"""

"""
Step 2 => 将传入的 Markdown 文档解析为 AST 树
后续维护流程：
1. 在 `mapping_base` 表中新增解析规则，并标注 handler 字段
2. 在 MarkdownASTParser 类中新增对应的处理方法，方法名与 handler 字段相同（需要设置特殊的 AST 节点类型）
"""
import json
import sys
import os

# 1. 导入 main 目录下的 MarkdownASTParser 类
## 1.1 获取当前脚本的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
## 1.2 定位到 src 目录，然后再定位 markdown_ast_parser 目录
project_src_path = os.path.dirname(os.path.dirname(current_dir))
ast_parser_path = os.path.join(project_src_path, "main/markdown_ast_parser")
## 1.3 将 src/main/markdown_ast_parser 添加到系统目录中
if ast_parser_path not in sys.path:
    sys.path.insert(0, ast_parser_path)
## 1.4 导入 main 目录下的 MarkdownASTParser 类
from markdown_ast_parser import MarkdownASTParser


class MarkdownASTParserTest(MarkdownASTParser):
    def __init__(self, db_path):
        super().__init__(db_path)
    
    def parse_test01(parser, text, parse_type='block'):
        """
        测试函数：用来校验数据库的正则 & 权重是否正确
        简单规则匹配测试：根据解析类型选择不同的规则集合，
        打印首次匹配到的规则信息以验证正则与权重配置
        :param parser: MarkdownASTParser 实例（已加载规则）
        :param text: 要解析的 Markdown 文本
        :param parse_type: 解析类型，'block' 或 'inline'
        """
        rules = parser.block_rules if parse_type == 'block' else parser.inline_rules
        while text:
            matched = False
            for rule in rules:
                match = rule['compiled_regex'].match(text)
                if match:
                    print(f"========== Match {parse_type} Rules ==========")
                    print("element_name_en: ", rule['name'])
                    print("element_category: ", rule['scope'])
                    print("element_weight: ", rule['weight'])
                    print("element_handler_name: ", rule['handler'])
                    matched = True
                    break
            if not matched:
                print("========== No Match Rules ==========")
            break

    def parse_test02(self, text, parse_type='block'):
        """ 
        确定可以从文档中你解析出不同的块来
        解析入口（会根据 parse_type 选择不同的解析规则）
        :param text: 要解析的 Markdown 文本
        :param parse_type: 解析类型，'block' 或 'inline'
        :return: AST Token 列表
        """
        tokens = []
        # 根据解析类型选择不同的规则集 - 默认是 block 级解析
        rules = self.block_rules if parse_type == 'block' else self.inline_rules

        print("========== LEFT Text ==========") # 打印剩余的 text
        # 打印剩余的字符，不可见字符也会被打印
        # 例如：换行符 \n 会被打印为 \n
        print(repr(text), '\n')
        while text:
            matched = False
            # 遍历所有规则进行匹配
            for rule in rules:
                match = rule['compiled_regex'].match(text)
                if match:
                    print("Block Name: ", rule['name'])
                    # 动态调用处理函数，例如 handle_heading, 返回 token 和消耗的字符长度
                    handler_method = getattr(self, f"_handle_{rule['handler']}")
                    token, consumed_length = handler_method(match, rule, text)
                    
                    if token:
                        tokens.append(token)

                    # 移动指针，截断已被处理的字符串
                    text = text[consumed_length:]
                    print("========== LEFT Text ==========") # 打印剩余的 text
                    # 打印剩余的字符，不可见字符也会被打印
                    # 例如：换行符 \n 会被打印为 \n
                    print(repr(text), '\n')
                    matched = True
                    break  # 匹配成功后跳出循环，避免重复处理
            
            if not matched:
                # 如果没有匹配到任何元素（理论上不可能，因为有 Paragraph 和 Text 兜底）
                # 将此未匹配到的视为 Text 节点
                if text:
                    tokens.append({'type' : 'text', 'raw' : text[0], 'text' : text[0]})
                    text = text[1:]

        # 返回后处理后的 AST 结构
        return self.normalize_output(tokens) 

if __name__ == "__main__":
    content = """# 123"""
    # 从 sqlite 数据库中读取规则
    parser = MarkdownASTParserTest(db_path = r'../../../res/database.db')
    ast = parser.parse_test02(content)
    # 打印 JSON 结果
      # ast: 要序列化的 AST 树
      # indent: 缩进空格数，每层嵌套缩进 2 个空格，形成层级结构
      # ensure_ascii=False: 确保非 ASCII 字符正常显示，避免编码问题，当为 True 时，中文会以 \uXXXX 编码显示
    print(json.dumps(ast, indent=2, ensure_ascii=False))
