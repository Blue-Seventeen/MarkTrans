"""
@File: markdown_ast_parser.py
@Version : 1.0.0
@Date: 2026-03-13
@Author: Blue17
@Contact: QQ 群(1016970550)
@Description: 将传入的 Markdown 文档根据 database.db 中的规则解析为 AST 树
后续维护流程（扩充语法格式流程）：
1. 在 `mapping_base` 表中新增解析规则，并标注 handler 字段
2. 在 MarkdownASTParser 类中新增对应的处理方法，方法名与 handler 字段相同（需要设置特殊的 AST 节点类型）
"""
import sqlite3
import re
import json
import sys
from pathlib import Path

# 设置更高的递归限制，防止在解析深层嵌套的 AST（如多层列表或引用）时报错
sys.setrecursionlimit(2000)

# 全局开关
ENABLE_PRINT_RETURN = False # 控制是否启用打印返回值的装饰器，True 时开启打印，False 时关闭打印

# 装饰器
def print_return(enabled=None):
    """
    带参数装饰器：可控制是否启用打印
    使用: @print_return 或 @print_return(enabled=False)
    如果 enabled 未指定（None），则使用全局 ENABLE_LOG 的值
    """
    # 内部包装逻辑提取
    def _create_wrapper(func, enabled_flag):
        def wrapper(*args, **kwargs):
            should_print = enabled_flag if enabled_flag is not None else ENABLE_PRINT_RETURN
            result = func(*args, **kwargs)
            if should_print:
                print(f"[{func.__name__}] -> {result!r}")
            return result
        return wrapper

    # Case 1: @print_return (无括号调用)
    # enabled 传入的是被装饰的函数
    if callable(enabled):
        return _create_wrapper(enabled, None)
    
    # Case 2: @print_return(enabled=False) (有括号调用)
    # enabled 传入的是 bool 参数 (或者 None)
    def decorator(func):
        return _create_wrapper(func, enabled)
    return decorator

# ---------------------------------------------------  辅助函数 ---------------------------------------------------
# 用于剔除行首缩进，返回缩进空格数和剔除缩进后的文本
def parse_indent(line, tab_width=4):
    """
    解析行首缩进，计算缩进对应的空格数，并返回剔除缩进后的文本。
    :param line: 输入的文本行
    :param tab_width: 一个 Tab 对应的空格数，默认为 4
    :return: (indent_count, cleaned_text) -> (总空格数, 剔除后的文本)
    """
    indent_count = 0
    i = 0
    
    for char in line:
        if char == ' ':
            indent_count += 1
            i += 1
        elif char == '\t':
            indent_count += tab_width
            i += 1
        else:
            # 遇到非空格/Tab字符（包括换行符），停止扫描
            break
            
    return indent_count, line[i:]

class MarkdownASTParser:
    """
    Markdown AST 解析类
    主要功能：连接数据库加载解析规则，并根据规则将 Markdown 文本转换为 AST（抽象语法树） JSON 结构
    """
    def __init__(self, db_path):
        """
        初始化解析器
        :param db_path: 存储解析规则的 SQlite 数据库路径
        """
        self.db_path = db_path    # 规则数据库路径
        self.block_rules = []     # 存储所有块级元素的解析规则（如段落、列表、代码块）
        self.inline_rules = []    # 存储所有行内元素的解析规则（如粗体、链接、行内代码）
        self.load_rules_from_db() # 从数据库加载解析规则，并根据权重（weight 进行排序）
    
    def load_rules_from_db(self):
        """
        从数据库加载解析规则，并根据权重（weight 进行排序），权重越高越优先处理
        格式: [
                    {
                        'name' : element_name_en,            // 对应格式的英文名称，此字段唯一
                        'weight' : weight,                   // 对应格式的权重，数值越大越优先处理
                        'regex' : element_regex_rule,        // 对应格式的正则匹配表达式（仅匹配开始字段，符合要求的就被视为该格式）
                        'compiled_regex' : None,             // 编译后的正则表达式对象，用于后续匹配
                        'handler' : element_handler_name,    // 对应格式的处理函数名，用于处理匹配到的文本
                        'scope' : '作用域(block/inline)'      // 对应格式的作用域，block 表示块级元素，inline 表示行内元素
                    },
            ...
        ]
        """
        self.block_rules = []  # 存储所有块级元素的解析规则（如段落、列表、代码块）
        self.inline_rules = [] # 存储所有行内元素的解析规则（如粗体、链接、行内代码）

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        rows = []
        try:
            # 查询 mapping_base 表，获取所有规则配置
            cursor.execute('SELECT element_name_en, element_regex_rule, element_handler_name, element_category, weight FROM mapping_base ORDER BY weight DESC')
            rows = cursor.fetchall()
        except Exception as e:
            print(f"Error loading patterns from DB: {e}", file=sys.stderr)
        finally:
            conn.close()
        
        # 遍历查询结果，构建规则字典
        for row in rows:
            element_name_en, element_regex_rule, element_handler_name, element_category, weight = row
            
            rule = {
                'name' : element_name_en,
                'weight' : weight,
                'regex' : element_regex_rule,
                'handler' : element_handler_name,
                'scope' : 'block' if 'Block' in element_category else 'inline'
            }

            try:
                # 编译正则表达式，开启多行模式
                rule['compiled_regex'] = re.compile(rule['regex'], re.MULTILINE)
                # 根据作用域分类存储
                if rule['scope'] == 'block':
                    self.block_rules.append(rule)
                else:
                    self.inline_rules.append(rule)
            except Exception as e:
                print(f"Error compiling regex for {element_name_en}: {e}", file=sys.stderr)
                continue

        # 再次按权重排序，确保顺序正确
        self.block_rules.sort(key=lambda x: x['weight'], reverse=True)
        self.inline_rules.sort(key=lambda x: x['weight'], reverse=True)

    def parse(self, text, parse_type='block'):
        """
        解析入口（会根据 parse_type 选择不同的解析规则）
        :param text: 要解析的 Markdown 文本
        :param parse_type: 解析类型，'block' 或 'inline'
        :return: AST Token 列表
        """
        tokens = []
        # 根据解析类型选择不同的规则集 - 默认是 block 级解析
        rules = self.block_rules if parse_type == 'block' else self.inline_rules

        while text:
            matched = False
            # 遍历所有规则进行匹配
            for rule in rules:
                match = rule['compiled_regex'].match(text)
                if match:
                    # 动态调用处理函数，例如 handle_heading, 返回 token 和消耗的字符长度
                    handler_method = getattr(self, f"_handle_{rule['handler']}")
                    token, consumed_length = handler_method(match, rule, text)
                    
                    if token:
                        tokens.append(token)

                    # 移动指针，截断已被处理的字符串
                    text = text[consumed_length:]
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

    def normalize_output(self, tokens):
        """
        对解析结果进行后处理，确保 AST 结构正确
        :param tokens: 原始解析出的 Token 列表
        :return: 标准化后的 AST Token 列表，合并连续 Text 块
        """
        normalized_tokens = []    # 存放规整化后的数据
        token_index = 0
        # 1. 合并连续的 Text 节点
        for index, token in enumerate(tokens):
            ## 1.0 跳过逻辑，如果 index < token_index，说明当前 token 已经被处理过了
            if index < token_index:
                continue
            else:
                token_index = index # 同步一下进度

            ## 1.1 如果当前 token 不是 text，则检查当前 token 中是否有 token 元素，进行递归
            if token['type'] != 'text':
                if 'token' in token:
                    ### 1.1.1 证明当前 token 内有 "token" 节点，我们需要规整化一下再添加
                    token["token"] = self.normalize_output(token["token"])
                    normalized_tokens.append(token)
                else:
                    normalized_tokens.append(token)
                
                continue

            ## 1.2 当前 token 是 text，则检查下一个 token 是否也是 text，如果是则进行合并，并更新 token_index
            total_raw = token['raw']
            total_text = token['text']
            while True:
                token_index += 1
                if token_index < len(tokens) and tokens[token_index]['type'] == 'text':
                    total_raw += tokens[token_index]['raw']
                    total_text += tokens[token_index]['text']
                else:
                    normalized_tokens.append(
                        {
                            'type' : 'text',
                            'raw' : total_raw,
                            'text' : total_text
                        }
                    )
                    break

        return normalized_tokens

    # ------------------------------------  Handlers（处理函数） · 块级格式------------------------------------ 
    @print_return
    def _handle_cardLink(self, match, rule, text):
        """
        处理卡片链接 (Auto Card Link) 格式，将其转换为 AST 脚本
        
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本内容
        :return: 卡片链接节点, 消耗的字符长度
        """

        # 1. 解析卡片链接内容
        """
        url(required): https://www.bing.com/search?q=baidu+%E7%99%BE%E5%BA%A6%E4%B8%80%E4%B8%8B+%E4%BD%A0%E5%B0%B1%E7%9F%A5%E9%81%93&PC=U316&FORM=CHROMN
        title(required): "baidu 百度一下 你就知道 - 必应"
        description: "通过必应的智能搜索，可以更轻松地快速查找所需内容并获得奖励。"
        host: www.bing.com
        favicon: https://www.bing.com/sa/simg/favicon-trans-bg-blue-mg.ico
        image: http://www.bing.com/sa/simg/facebook_sharing_5.png | "[[支持内部图片]]"
        """
        content = match.group(1)
        data = {}
        for line in content.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                data[key.strip()] = val.strip()
        
        # 2. 构建 AST 节点
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),
            **data
        }
        return token, len(match.group(0))
    
    @print_return
    def _handle_codeBlock(self, match, rule, text):
        """
        处理普通代码块，将其转换成 AST 代码块节点
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本内容
        :return: 代码块节点 & 消耗的字符长度
        """
        # 1. 提取出代码块的语言标识，并进行优化，如果没有则是 None
        """
        ```js
            console.log(123);
        ```
        """
        lang = match.group(1).strip() if match.group(1) else None
        if lang is not None:
            # 部分用户可能采用语言缩写，如 js 代替 javascript，我们需要一个字典将其缩写映射过去，如果没有缩写，保持原样
            # 如果未能找到对应的语言名称，保持原样
            full_language_name_dic = {
                    "js": "JavaScript", "ts": "TypeScript", "py": "Python",
                    "sh": "Bash", "bash": "Bash", "zsh": "Bash",
                    "cpp": "C++", "c++": "C++", "cxx": "C++",
                    "md": "Markdown", "markdown": "Markdown",
                    "javascript": "JavaScript", "python": "Python"
            }
            lang = full_language_name_dic.get(lang, lang) # 如果没有缩写，保持原样
        
        # 2. 提取出代码块的内容，并构造 AST 节点
        code_content = match.group(2)
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),
            "lang" : lang,
            "text": code_content
        }
        return token, len(match.group(0))
    
    @print_return
    def _handle_comment(self, match, rule, text):
        """
        处理注释 %% ... %%
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本内容
        :return: 注释节点 & 消耗的字符长度
        """
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),
            "block" : True if 'Block' in rule['name'] else False,
            "text" : match.group(1)
        }
        return token, len(match.group(0))
    
    @print_return
    def _handle_callout(self, match, rule, text):
        """
        处理调用块 callout
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :return: 调用块节点 , 消耗的字符长度
        """
        # 1. 解析调用快内容
        c_type = match.group(1)  # 调用块类型
        c_state = "collapse" if match.group(2) == "-" else "expand"   # 调用块的状态 — 折叠(collapse)，展开（expand）
        c_title = match.group(3).strip() if match.group(3) else None  # 调用块标题
        c_content = match.group(4) if match.group(4) else None        # 调用块内容

        # 构造 token 节点
        token = {
            'type' : rule['handler'],
            'raw' : match.group(0),
            'calloutType' : c_type,
            'fold' : c_state,
            'title' : self.parse(c_title, 'inline') if c_title != None else None, # 标题中可能隐藏行内样式
            'text' : c_content,
            # Callout 内容可能包含块级元素（如列表），递归调用 parse (块级解析)
            "tokens": self.parse(c_content) 
        }
        return token, len(match.group(0))

    @print_return
    def _handle_blockQuote(self, match, rule, text):
        """
        处理引用块
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :return: 引用块节点 & 消耗的字符长度
        """
        # 1. 拿到引用块的所有内容
        raw = match.group(0)
        # 2. 移除引用块的所有行首 '>' 符号，获得 text
        text = ""
        indent_level = parse_indent(raw.split("\n")[0])[0] # 引用块的缩进级别
        for line in raw.split("\n"):
            text += line[indent_level+1:] + "\n"
        if raw.split("\n")[-1] == "": # 防止最后一行空行
            text = text[:-1]

        # 3. 构造 AST 节点
        token = {
            'type' : rule['handler'],
            'raw' : raw,
            'text' : text,
            "tokens" : self.parse(text)
        }
        return token, len(raw)

    @print_return
    def _handle_list(self, match, rule, text):
        """
        处理列表，包括：无序列表（Unordered List）、有序列表（Ordered List）、任务列表（Task List），及其子列表
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :return: 列表节点 , 消耗的字符长度
        """
        # 1. 获取一整个列表块（直到遇到可能的换行或文档结束）
        total_list_raw = ""  # 存储了连续的所有列表的原始字符串
        ## 1.1 从块级格式中检索所有列表规则
        rule_lists = [{'element_name_en' : item['name'], 'compiled_regex' : item['compiled_regex']} for item in self.block_rules if item['handler'] == rule['handler']]
        ## 1.2 遍历列表规则，从 text 文档中以行为单位一行一行向下匹配，直到文章终止，或者遇到不符合列表规则的行
        break_flag = True
        for line in text.split("\n"):
            break_flag = True
            for r in rule_lists:
                match_result = r['compiled_regex'].match(line)
                if match_result:
                    total_list_raw += line + "\n"
                    break_flag = False
                    break
            if break_flag:
                break
        
        # 2. 按行开始解析列表块 
        tokens = []                                   # 用来存储解析出来的 list_item 节点
        for line in total_list_raw.split("\n")[:-1]:
            list_type = ""          # 存储列表类型
            fragment_match = None   # 存储正则表达式匹配的结果
            ## 2.1 遍历规则列表，找到当前行符合的列表规则，获取 list_type & fragment_match
            for item in rule_lists:
                fragment_match = item['compiled_regex'].match(line)
                if fragment_match:
                    list_type = item['element_name_en'] # 获取列表类型
                    break

            ## 2.2 根据 list_type 与 fragment_match 构造 AST 节点
            if list_type == "Task List":
                ### 2.2.1 获取当前行 task_list 的原始文本
                raw = fragment_match.group(0)
                ### 2.2.2 获取 taskFinish 状态
                taskFinish = True if fragment_match.group(3) == "x" or fragment_match.group(3) == "X" else False
                ### 2.2.3 获取 task_list 项的文本内容
                text = fragment_match.group(4)
                ### 2.2.4 构造 task_list AST 节点
                token = {
                        "type" : "list_item",
                        "listType" : "task_list",
                        "taskFinish" : taskFinish,
                        "indentationLevel" : int(parse_indent(raw)[0]),
                        "raw" : raw,
                        "text" : text,
                        "tokens" : self.parse(text)
                    }
                ### 2.2.5 加入 tokens 列表
                tokens.append(token)
            elif list_type == "Unordered List":
                ### 2.2.1 获取当前行 unordered_list 的原始文本
                raw = fragment_match.group(0)
                ### 2.2.2 获取 unordered_list 项的文本内容
                text = fragment_match.group(3)
                ### 2.2.3 构造 unordered_list AST 节点
                token = {
                        "type" : "list_item",
                        "listType" : "unordered_list",
                        "indentationLevel" : int(parse_indent(raw)[0]),
                        "raw" : raw,
                        "text" : text,
                        "tokens" : self.parse(text)
                    }
                ### 2.2.4 加入 tokens 列表
                tokens.append(token)
            elif list_type == "Ordered List":
                ### 2.2.1 获取当前行 ordered_list 的原始文本
                raw = fragment_match.group(0)
                ### 2.2.2 获取当前行 ordered_list 的序号
                order = int(raw.split(".", 1)[0].strip())
                ### 2.2.3 获取 ordered_list 项的文本内容
                text = fragment_match.group(3)
                ### 2.2.4 构造 ordered_list AST 节点
                token = {
                        "type" : "list_item",
                        "listType" : "ordered_list",
                        "indentationLevel" : int(parse_indent(raw)[0]),
                        "order" : int(order),
                        "raw" : raw,
                        "text" : text,
                        "tokens" : self.parse(text)
                    }
                ### 2.2.5 加入 tokens 列表
                tokens.append(token)
                
        # 3. 构造 AST 节点
        token = {
            'type' : rule['handler'],
            'raw' : total_list_raw,
            "tokens" : tokens
        }
        # 3.1 如果 break_flag 为 True，证明列表后面还有其他内容，也证明列表是以 \n 结尾的，
            # 则返回列表片段的长度，否则返回列表片段的长度减一，因为最后一个列表项后面没有 \n
        return token, len(total_list_raw) if break_flag else len(total_list_raw) - 1
    
    @print_return
    def _handle_table(self, match, rule, text):
        """
        处理表格节点
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本
        :return: 表格节点 , 消耗的字符长度
        | H1  | H2  |  H3 |
        | :-- | :-: | --: |
        | C1  | C2  |  C3 |
        """
        # 1. 从表格中提取出标题行，对齐信息，表格内容(可能没有)
        raw = match.group(0) if match.group(0).split("\n")[-1] != '' else match.group(0)[:-1]
        title_row = raw.split("\n")[0]
        align_row = raw.split("\n")[1]
        content_rows = raw.split("\n")[2:] if len(raw.split("\n")) > 2 else []

        # 2. 解析对齐信息，将其转换为对齐方式列表
        align_list = []
        for align in align_row.split("|")[1:-1]:
            if align.strip().count(":") == 2:
                align_list.append("center")
            elif ":-" in align.strip():
                align_list.append("left")
            elif "-:" in align.strip():
                align_list.append("right")
            else:
                align_list.append("none")

        # 3. 解析 title_row 单元格中的标题内容格式
        def parse_row(row_content):
            """
            解析表格行内容，将其转换为单元格列表
            :param row_content: 表格行内容
            :return: 单元格列表 ['1', '2', '3']
            """
            # 将 | 12\|3 | 123 | 123 | 转换为 [' 12\|3 ', ' 123 ', ' 123 ']
            row_list = row_content.split("|")[1:-1]
            # 后处理，还原被注释后的 |
            row_data = []
            i = 0
            while i < len(row_list):
                if row_list[i].strip()[-1:] != "\\":
                    row_data.append(row_list[i].strip())
                else:
                    cell_data = row_list[i].strip() + '|' + row_list[i + 1].strip()
                    i += 1
                    while row_list[i].strip()[-1:] == '\\':
                        cell_data +=  '|' + row_list[i + 1].strip()
                        i += 1
                    row_data.append(cell_data)
                i += 1
            return row_data

        header = []
        title_row_list = parse_row(title_row)
        for cell in title_row_list:
            header.append(self.parse(cell, 'inline'))
        
        # 4. 解析 content_rows 中的内容行
        rows = []
        ## 4.1 解析 content_rows 中每行的内容
        for row in content_rows: 
            row_list = []
            row_cell_list = parse_row(row) ## 4.2 将 content_rows 中每行拆分为多个单元格
            print(row_cell_list)
            for cell in row_cell_list:     ## 4.3 调用行内解析器解析每个单元格的内容
                row_list.append(self.parse(cell, 'inline'))
            ## 4.3 将当前行解析后的单元格列表添加到 rows 中
            rows.append(row_list)

        # 构造 AST 节点信息
        token = {
            "type" : rule['handler'],
            "raw" : raw,
            "rowCount" : len(raw.split("\n")) - 1 if raw.split("\n")[-1] != "" else len(raw.split("\n")) - 2,
            "columnCount" : len(align_list),
            "align" : align_list,
            "header" : header,
            "rows" : rows
        }
        return token, len(match.group(0))

    @print_return
    def _handle_heading(self, match, rule, text):
        """
        处理标题，包括：一级标题（H1）、二级标题（H2）、三级标题（H3）、四级标题（H4）、五级标题（H5）、六级标题（H6）
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本
        :return: 标题节点 , 消耗的字符长度
        """
        # 构造 AST 节点信息
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),
            "depth": len(match.group(0).split(' ')[0]),
            "text": match.group(1),
            "tokens": self.parse(match.group(1), 'inline')  # 标题内容可能包含行内样式（如粗体），递归调用 parse
        }
        return token, len(match.group(0))

    @print_return
    def _handle_hr(self, match, rule, text):
        """
        处理水平分隔线
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本
        :return: 水平分隔线节点 , 消耗的字符长度
        """
        # 构造 AST 节点信息
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0)
        }
        return token, len(match.group(0))

    @print_return
    def _handle_footNoteContent(self, match, rule, text):
        """
        处理段落中的脚注内容 [^1]: 123
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本
        :return: 脚注内容节点 , 消耗的字符长度
        """
        # 1. 拿到脚注中的所有内容，以 \n\n，其余块级匹配成功，或者到文本结束，作为结束标志
        raw = match.group(0)
        block_compiled_regex_list = [item['compiled_regex'] for item in self.block_rules if item['name'] != 'Paragraph']
        skip_flag = True
        for line in text.split("\n"):
            ## 1.0 跳过第一行
            if skip_flag:
                skip_flag = False
                continue
            ## 1.1 碰到 \n\n 中的第二个 \n 时，结束解析 或 到文本结束
            if line == "" or len(text.split("\n")) == 1:
                break
            ## 1.2 拿到其余块的匹配内容，也结束
            for compiled_regex in block_compiled_regex_list:
                if compiled_regex.match(line):
                    break
            ## 1.3 否则，添加到 raw 中
            raw += line + "\n"
        
        # 2. 提取所需的信息
        footNoteId = match.group(2)
        text = raw.split(":", 1)[1]

        # 3. 构造 AST 节点信息
        token = {
            "type" : rule['handler'],
            "raw" : raw,
            "text" : text,
            "order" : footNoteId,
            "token" : self.parse(text, parse_type='inline')
        }
        return token, len(raw)

    @print_return
    def _handle_br(self, match, rule, text):
        """
        处理换行符
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本
        :return: 换行符节点 & 消耗的字符长度
        """
        token = {
            "type" : rule['handler'],
            'raw' : match.group(0)
        }
        return token, len(match.group(0))

    @print_return
    def _handle_paragraph(self, match, rule, text):
        """
        处理段落文本，将其转换为 AST 结构
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本
        :return: 段落文本节点 , 消耗的字符长度
        """
        # 构造 AST 节点
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),
            "text" : match.group(0).strip('\n'),
            "tokens" : self.parse(match.group(0).strip('\n'), parse_type='inline')
        }
        return token, len(match.group(0))

    # ------------------------------------  Handlers（处理函数） · 行内格式 ------------------------------------ 
    @print_return
    def _handle_escape(self, match, rule, text):
        """
        处理转义字符（如 \*、\\ 等）
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :return: 转义后的文本节点 & 消耗的字符长度
        """
        # 构造 AST 节点
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),    # 完整匹配的字符串，如 \*
            "text": match.group(1),    # 转义后的字符，如 *
        }
        return token, len(match.group(0))

    @print_return
    def _handle_codeSpan(self, match, rule, text):
        """
        处理行内代码，将其转换为 AST 节点
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本
        :return: 行内代码节点 , 消耗的字符长度
        """
        # 构造 AST 节点
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),
            "text": match.group(2)
        }
        return token, len(match.group(0))
    
    @print_return
    def _handle_footNoteSign(self,match,rule, text):
        """
        处理段落中的脚注符号 [^1]
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本
        :return: 脚注符号节点 , 消耗的字符长度
        """
        # 1. 拿到脚注编号
        footNoteId = match.group(2)
        # 2. 构造 AST 节点
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),
            "text" : match.group(0),
            "order" : int(footNoteId),
            
        }
        return token, len(match.group(0))

    @print_return
    def _handle_embed(self, match, rule, text):
        """
        处理嵌入内容 ![[图片名称#pic_right|300x200]]
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本
        :return: 嵌入内容节点 & 消耗的字符长度
        """
        # 构造 AST 节点
        target = match.group(1).split('#')[0] # 文件名称（包含后缀）
        filename = Path(target)
        # 从 target 中提取文件后缀（Markdown 文件可能没有后缀）
        embedType = filename.suffix if '.' in target else 'md'
        # 从 target 中提取对齐方式（默认居中）
        align = match.group(1).split("#")[1].split("|")[0][4:] if "#" in match.group(1) else "center"
        # 从 target 中提取宽度
        width, height = None, None
        if "|" in match.group(1):
            if "x" in match.group(1).split("|")[1]:
                width = int(match.group(1).split("|")[1].strip().split("x")[0])
                height = int(match.group(1).split("|")[1].strip().split("x")[1])
            else:
                width = int(match.group(1).split("|")[1].strip())
        
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),
            "target" : target,
            "embedType" : embedType[1:],
            "align" : align,
            "width" : width,
            "height" : height,
            "text" : filename.name
        }
        return token, len(match.group(0))
    
    @print_return
    def _handle_image(self, match, rule, text):
        """
        处理图片 ![图片名称|宽x高](图片 URL)
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本
        :return: 图片节点 & 消耗的字符长度
        """
        # 从 match.group(1) 中提取 alt 文本（图片名称）
        alt = match.group(1).split("|")[0].strip()
        # 从 match.group(1) 中提取宽度、高度
        width, height = None, None
        if "|" in match.group(1):
            if "x" in match.group(1).split("|")[1]:
                width = int(match.group(1).split("|")[1].strip().split("x")[0])
                height = int(match.group(1).split("|")[1].strip().split("x")[1])
            else:
                width = int(match.group(1).split("|")[1].strip())
        
        # 构造 AST 节点
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),
            "alt" : alt,
            "width" : width,
            "height" : height,
            "src" : match.group(2),
            "text" : alt
        }
        return token, len(match.group(0))

    @print_return
    def _handle_wikiLink(self, match, rule, text):
        """
        处理 Wiki 链接 [[需要链接的 Markdown 文件名#引用的段落标识|显示的内容]]
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本
        :return: Wiki 链接节点 & 消耗的字符长度
        """
        # 从 match.group(1) 中提取目标文件名称（包含后缀）
        target = match.group(1).split("#")[0]
        # 从 match.group(1) 中提取引用段落标识（如果有）
        anchor = match.group(1).split("#")[1].split("|")[0] if "#" in match.group(1) else None
        # 从 match.group(1) 中提取显示内容（如果有）
        display = match.group(1).split("|")[1] if "|" in match.group(1) else match.group(1)
        # 构造 AST 节点
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),
            "target" : target,
            "anchor" : anchor,
            "display" : display,
            "fileType" : Path(target).suffix[1:] if '.' in target else 'md',
            "text" : display
        }
        return token, len(match.group(0))

    @print_return
    def _handle_link(self, match, rule, text):
        """
        处理链接 [显示内容](链接 URL)
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本
        :return: 链接节点 & 消耗的字符长度
        """
        # 构造 AST 节点
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),
            "src" : match.group(2),
            "text" : match.group(1)
        }
        return token, len(match.group(0))

    @print_return
    def _handle_strong(self, match, rule, text):
        """
        处理加粗文本 **粗体**
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :return: 加粗文本节点 & 消耗的字符长度
        """
        # 构造 AST 节点
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),
            "text" : match.group(1),
            "tokens" : self.parse(match.group(1), parse_type = 'inline') # 粗体中可能包含其他行内格式
        }
        return token, len(match.group(0))

    @print_return
    def _handle_italic(self, match, rule, text):
        """
        处理斜体文本 *斜体*
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本
        :return: 斜体文本节点 & 消耗的字符长度
        """
        # 构造 AST 节点
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),
            "text" : match.group(1),
            "tokens" : self.parse(match.group(1), parse_type = 'inline') # 斜体中可能包含其他行内格式
        }
        return token, len(match.group(0))

    @print_return
    def _handle_del(self, match, rule, text):
        """
        处理删除线文本
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :return: 删除线文本节点 & 消耗的字符长度
        """
        # 构造 AST 节点
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),
            "text" : match.group(1),
            "tokens" : self.parse(match.group(1), parse_type = 'inline') # 删除线中可能包含其他行内格式
        }
        return token, len(match.group(0))

    @print_return
    def _handle_mark(self, match, rule, text):
        """
        处理高亮文本  ==高亮==
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本
        :return: 高亮文本节点 , 消耗的字符长度
        """
        # 构造 AST 节点
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),
            "text" : match.group(1),
            "tokens" : self.parse(match.group(1), parse_type = 'inline') # 高亮中可能包含其他行内格式
        }
        return token, len(match.group(0))

    @print_return
    def _handle_text(self, match, rule, text):
        """
        处理普通文本
        :param match: 正则匹配对象
        :param rule: 当前匹配的规则
        :param text: 原始文本
        :return: 普通文本节点 & 消耗的字符长度
        """
        token = {
            "type" : rule['handler'],
            "raw" : match.group(0),
            "text" : match.group(0)
        }
        return token, len(match.group(0))

if __name__ == "__main__":
    content = """# 123"""
    # 从 sqlite 数据库中读取规则
    parser = MarkdownASTParser(db_path = r'../../../res/database.db')
    ast = parser.parse(content)
    # 打印 JSON 结果
    # ast: 要序列化的 AST 树
    # indent: 缩进空格数，每层嵌套缩进 2 个空格，形成层级结构
    # ensure_ascii=False: 确保非 ASCII 字符正常显示，避免编码问题，当为 True 时，中文会以 \uXXXX 编码显示
    print(json.dumps(ast, indent=2, ensure_ascii=False))