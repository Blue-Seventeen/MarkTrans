"""
@File: ast_html_translator.py
@Version : 1.0.0
@Date: 2026-03-14
@Author: Blue17
@Contact: QQ 群(1016970550)
@Description: 将传入的 AST 树根据 database.db 中的规则解析为 HTML 文档
后续维护流程（修改映射格式流程）:
1. 在 `mapping_rule` 中编写对应的 matching_rule 与对应的 render_name
2. 在本脚本中添加对应的 _render_§render_name§ 渲染规则即可
"""
import re
import ast
import sys
import html
import json
import sqlite3

# -------------------------------------------------------------------------------------------- #
#                                           全局配置                                            #
# -------------------------------------------------------------------------------------------  #
# 设置更高的递归限制，防止在解析深层嵌套的 AST（如多层列表或引用）时报错
sys.setrecursionlimit(2000)
# _safe_eval_rule 执行 Bool 表达式判断时，只允许使用以下节点
ALLOWED_NODES = (
    ast.Expression,      # 根节点（eval 模式）
    ast.BoolOp, ast.And, ast.Or,  # 布尔运算：and / or
    ast.UnaryOp, ast.Not,         # 一元运算：not
    ast.Compare,                  # 比较运算
    ast.Eq, ast.NotEq,            # ==, !=
    ast.In, ast.NotIn,            # in, not in
    ast.Gt, ast.GtE, ast.Lt, ast.LtE,  # >, >=, <, <=
    ast.Name, ast.Load,           # 变量名及其读取操作
    ast.Constant,                 # 常量（数字、字符串等）
    ast.Subscript, ast.Index, ast.Slice,  # 下标访问：token["key"]
    ast.List, ast.Tuple,          # 列表、元组字面量
    ast.Call, ast.Attribute       # 仅允许受控方法调用（如 .lower()）
)

# -------------------------------------------------------------------------------------------- #
#                                    核心类 - ASTHtmlTranslator                                 #
# -------------------------------------------------------------------------------------------  #
class ASTHtmlTranslator:
    """
    AST HTML 转换器
    将 MarkdownASTParser 解析生成的 AST JSON 转换为 HTML 代码
    """
    def __init__(self, db_path):
        """
        初始化转换器
        :param db_path: 存储解析规则的 SQlite 数据库路径
        :param attachment_directory_path: 附件目录路径，针对那些需要定位附件的场景
        """
        self.db_path = db_path     # 规则数据库路径
        self.mapping_rules = []    # 存放所有映射规则 [{}]
        self.load_rules_from_db(db_path = self.db_path)  # 从数据库加载解析规则
    
    def load_rules_from_db(self, db_path = None):
        """
        从数据库加载转换规则，存放到 self.mapping_rules 中
        :param db_path: 数据库路径
        :return 
        格式: 
        [
            {
                'style_rule_name' : style_rule_name,     // 对应格式的样式规则名称，此字段唯一
                'weight' : weight,                       // 对应格式的权重，数值越大越优先处理
                'matching_rule' : matching_rule,         // 对应格式的匹配表达式
                'html_output' : html_output,             // 对应格式的 HTML 输出
                'render_name' : render_name              // 对应格式的渲染函数名，用于处理匹配到的文本
            },
            ...
        ]
        """
        self.mapping_rules = []
        rows = []
        style_id = 1

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # 1. 从 mapping_style 表中查询 is_active = 1 的样式，并获取其 style_id
            cursor.execute('SELECT id FROM mapping_style WHERE is_active = 1 ORDER BY id LIMIT 1')
            active_style = cursor.fetchone()
            if active_style is not None:
                style_id = active_style[0]
            # 2. 根据 style_id 从 mapping_rule 表中查询所有规则配置
            cursor.execute('SELECT style_rule_name, weight, matching_rule, html_output, render_name FROM mapping_rule WHERE style_id = ? ORDER BY weight DESC', (style_id,))
            rows = cursor.fetchall()
        except Exception as e:
            print(f"Error loading rules from DB: {e}", file=sys.stderr)
        finally:
            try:
                conn.close()
            except Exception:
                pass
        
        # 3. 遍历查询结果，构建规则字典
        for row in rows:
            style_rule_name, weight, matching_rule, html_output, render_name = row
            self.mapping_rules.append({
                'style_rule_name' : style_rule_name,
                'weight' : weight,
                'matching_rule' : matching_rule,
                'html_output' : html_output,
                'render_name' : render_name
            })
        
        # 4. 再次按权重排序降序排序，确保顺序正确
        self.mapping_rules.sort(key=lambda x: x['weight'], reverse=True)

    def translate(self, ast_tokens):
        """
        转换入口函数
        :param ast_tokens: AST 节点列表 (List[Dict])
        :return: 生成的 HTML 字符串
        """
        html_output = "" # 存储最终生成的 HTML 字符串
        # 1. 预处理，将 AST JSON 格式转换为符合 Python 要求的字典与列表
        if isinstance(ast_tokens, str):
            ast_tokens = json.loads(ast_tokens)

        # 2. 遍历 AST 节点列表，根据规则进行转换
        for token in ast_tokens:
            ## 2.1 获取 token 类型
            token_type = token.get('type')
            if not token_type:
                continue

            ## 2.2 从 self.mapping_rules 中定位对应的 rule 组成 rule_list 一同传递过去
            rule_list = [rule for rule in self.mapping_rules if rule['render_name'] == token_type]

            ## 2.2 将 token, matching_rule 和 html_output 传递给对应的渲染函数
            render_func = getattr(self, f'_render_{token_type}')
            html_output += render_func(token, rule_list)
        
        return html_output

    # -------------------------------------------------------------------------------------------- #
    #                                         字符串代码执行逻辑                                      #
    # -------------------------------------------------------------------------------------------- #

    def _save_eval_rule(self, expr: str, token: dict) -> bool:
        """
        评估表达式是否匹配当前 token，应付 token['type'] == 'escape' 时的特殊情况
        :param expr: 匹配表达式
        :param token: 当前 AST 节点
        :return: 是否匹配
        """
        # 1. 基础校验：空表达式或过长表达式直接拒绝
        if not expr or len(expr) > 1024:
            return False
        
        # 2. 解析为 AST, mode='eval' 表示单表达式模式
        tree = ast.parse(expr, mode="eval")

        # 3. 遍历所有节点，检查是否在白名单中
        global ALLOWED_NODES
        for node in ast.walk(tree):
            # 3.1 发现危险节点，直接拒绝执行
            if not isinstance(node, ALLOWED_NODES):
                return False 
        
            # 3.2 额外限制：变量名只能是 "token"
            if isinstance(node, ast.Name) and node.id != 'token':
                return False # 发现非 "token" 变量名，拒绝执行

            # 3.3 仅允许访问属性 lower
            if isinstance(node, ast.Attribute):
                if node.attr != 'lower':
                    return False

            # 3.4 仅允许无参数调用 .lower()
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Attribute):
                    return False
                if node.func.attr != 'lower':
                    return False
                if node.args or node.keywords:
                    return False
        
        # 4. 编译并通过 eval 执行，但完全隔离执行环境
        try:
            code = compile(tree, "<rule>", "eval")
            return bool(eval(code, {"__builtins__": {}}, {"token": token}))
        except Exception:
            return False

    def _save_get_token(self, expr: str, token: dict) -> str:
        """
        安全的获取 token 中的 text 字段，应付 	§token['text']§
        :param expr: 表达式
        :param token: 当前 AST 节点
        :return: 表达式求值结果
        """
        return eval(expr, {"__builtins__": {}}, {"token": token})

    # -------------------------------------------------------------------------------------------- #
    #                                           html 渲染逻辑                                       #
    # -------------------------------------------------------------------------------------------- #

    def _render_easy(self, token, rule_list):
        """
        简单渲染函数，用于处理那些不需要特殊处理的 token，只对 html_output 中的 §token['text']§ 进行替换操作
        :param token : AST 中对应节点
        :param rule_list : 匹配的规则列表
        """
        # 1. 遍历 rule_list 拿到找到 token 满足的 matching_rule
        for rule in rule_list:
            # 1.1 执行 matching_rule 并判断是否满足，如果满足则按照 html_output 进行解析
            if self._save_eval_rule(rule['matching_rule'], token):
                # 1.1.1 拿到 html_output 模板
                html_output_template = rule['html_output']
                # 1.1.2 从 html_output_template 中提取出所有被 § 包裹的内容
                pattern = r'(§(.*?)§)'    # 非贪婪匹配 §...§ 之间的内容（最小匹配）
                matches = re.findall(pattern, rule['html_output'])
                # 1.1.3 替换 §...§ 为对应的值
                for match in matches:
                    # 如果 match 为 §token['tokens']§ 证明需要递归翻译
                    if match[1] == "token['tokens']" :
                        html_output_template = html_output_template.replace(match[0], self.translate(token['tokens']))
                    else:
                        html_output_template = html_output_template.replace(match[0], self._save_get_token(match[1], token))
                # 1.1.4 返回渲染结果
                return html_output_template 
        # 2. 如果没有一条满足，返回默认渲染
        return self._render_default(token)

    def _render_default(self, token):
        """
        默认渲染函数，当没有匹配的渲染函数时调用
        :param token : AST 中对应节点
        """
        # 直接将 token 转换为字符串并 HTML 转义
        return html.escape(str(token))

    # -------------------------------------------------------------------------------------------- #
    #                                   块级元素渲染 (Block Elements)                                #
    # -------------------------------------------------------------------------------------------- #
    def _render_cardLink(self, token, rule_list):
        """
        渲染卡片链接
        :param token : AST 中对应节点
        :param rule_list : 匹配的规则列表
        """
        return self._render_easy(token, rule_list)

    def _render_codeBlock(self, token, rule_list):
        """
        渲染代码块
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)

    def _render_callout(self, token, rule_list):
        """
        渲染标注块
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)

    def _render_blockQuote(self, token, rule_list):
        """
        渲染引用块
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)
    
    def _render_list_item(self, token, rule_list):
        """
        渲染列表项
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)
    
    def _render_table(self, token, rule_list):
        """
        渲染表格
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        html_output_template = "" # 存放最终的渲染结果的
        # 1. 遍历 rule_list 列表，拿到表格各部分的渲染模板
        render_template_dict = {}
        for rule in rule_list:
            render_template_dict[rule['style_rule_name']] = rule['html_output']
        
        # 2. 从内到外依次渲染出表格各个部分
        tr_html = ""
        for row in token["rows"] :   # 定位到每一行
            ## 2.1 渲染 td  => 一个单元格
            td_html = ""
            for cell in row:         # 定位到每一个单元格, cell 中存放的是一个列表，代表构成该单元格的样式集合
                text_html = self.translate(cell) # 递归翻译该单元格的内容
                td_html += render_template_dict['表格 — <td>'].replace('§text§', text_html) # 替换 §text§ 为翻译后的内容
            ## 2.2 渲染 tr => 一行
            tr_html += render_template_dict['表格 — <tr>'].replace('§td§', td_html) # 替换 §td§ 为翻译后的内容
        
        ## 2.3 渲染 th
        th_html = ""
        for cell in token["header"]:         # 定位到每一个单元格, cell 中存放的是一个列表，代表构成该单元格的样式集合
            text_html = self.translate(cell) # 递归翻译该单元格的内容
            th_html += render_template_dict['表格 — <th>'].replace('§text§', text_html) # 替换 §text§ 为翻译后的内容
        
        ## 2.4 渲染最终的表格
        html_output_template = render_template_dict['表格 — <table>'].replace('§表格 — <th>§', th_html).replace('§表格 — <tr>§', tr_html) # 替换 §th§ 和 §tr§ 为翻译后的内容

        return html_output_template
   
    def _render_heading(self, token, rule_list):
        """
        渲染标题
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)
    
    def _render_hr(self, token, rule_list):
        """
        渲染水平分割线
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)

    def _render_footNoteContent(self, token, rule_list):
        """
        渲染脚注内容
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)
    
    def _render_paragraph(self, token, rule_list):
        """
        渲染文本段落
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)
    
    def _render_br(self, token, rule_list):
        """
        渲染换行符
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)
    # -------------------------------------------------------------------------------------------- #
    #                                   行内元素渲染 (Inline Elements)                               #
    # -------------------------------------------------------------------------------------------- #
    def _render_escape(self, token, rule_list):
        """
        渲染转义字符
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)

    def _render_codeSpan(self, token, rule_list):
        """
        渲染行内代码
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)

    def _render_comment(self, token, rule_list):
        """
        渲染注释
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)
    
    def _render_footNoteSign(self, token, rule_list):
        """
        渲染脚注引用符号
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)
    
    def _render_embed(self, token, rule_list):
        """
        渲染嵌入内容
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)
    
    def _render_image(self, token, rule_list):
        """
        渲染外部图片引用
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)
    
    def _render_wikiLink(self, token, rule_list):
        """
        渲染内部链接（Wiki 风格）
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)
    
    def _render_link(self, token, rule_list):
        """
        渲染内部链接（Markdown 风格）
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)
    
    def _render_strong(self, token, rule_list):
        """
        渲染加粗文本
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)
    
    def _render_italic(self, token, rule_list):
        """
        渲染斜体文本
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)
    
    def _render_del(self, token, rule_list):
        """
        渲染删除线文本
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)
    
    def _render_mark(self, token, rule_list):
        """
        渲染高亮文本
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)
    
    def _render_text(self, token, rule_list):
        """
        渲染普通文本
        :param token : AST 中对应节点
        :param rule_list : 对应的规则（可能有很多条） [{}] 
        """
        return self._render_easy(token = token, rule_list = rule_list)

if __name__ == "__main__":
    translator = ASTHtmlTranslator(db_path = r'../../../res/database.db')
    print(translator.mapping_rules)