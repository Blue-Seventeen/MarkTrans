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
import html

class ASTHtmlTranslator:
    """
    AST HTML 转换器
    将 MarkdownASTParser 解析生成的 AST JSON 转换为 HTML 代码
    """
    def __init__(self):
        pass

    def translate(self, ast_tokens):
        """
        转换入口函数
        :param ast_tokens: AST 节点列表 (List[Dict])
        :return: 生成的 HTML 字符串
        """
        if not ast_tokens:
            return ""
        
        html_parts = []
        for token in ast_tokens:
            html_parts.append(self._dispatch(token))
        return '\n'.join(html_parts)

    def _dispatch(self, token):
        """
        根据 token 的 type 分发到对应的渲染函数
        """
        token_type = token.get('type')
        if not token_type:
            return ""

        # 动态查找处理方法，例如 type="heading" -> _render_heading
        handler_name = f"_render_{token_type}"
        handler = getattr(self, handler_name, self._render_default)
        return handler(token)

    def _render_default(self, token):
        """
        默认处理函数：如果找不到对应的渲染器，则尝试渲染子节点，否则直接返回 text 或 raw
        """
        if 'tokens' in token:
            return self.translate(token['tokens'])
        return html.escape(token.get('text', token.get('raw', '')))

    # ----------------------------------------------------------------------- #
    #                       块级元素渲染 (Block Elements)                       #
    # ----------------------------------------------------------------------- #

    def _render_heading(self, token):
        """渲染标题: <h1~h6>...</h1~h6>"""
        depth = token.get('depth', 1)
        text_content = ""
        if 'tokens' in token:
            text_content = self.translate(token['tokens'])
        else:
            text_content = html.escape(token.get('text', ''))
            
        # 为标题添加 id，方便生成目录锚点（可选）
        return f'<h{depth}>{text_content}</h{depth}>'

    def _render_paragraph(self, token):
        """渲染段落: <p>...</p>"""
        content = self.translate(token.get('tokens', []))
        # 如果段落为空，则不渲染，或者渲染一个 <br>
        if not content:
            return ""
        return f'<p>{content}</p>'

    def _render_br(self, token):
        """渲染换行"""
        return "<br>"

    def _render_hr(self, token):
        """渲染分割线"""
        return "<hr>"

    def _render_blockQuote(self, token):
        """渲染引用块: <blockquote>...</blockquote>"""
        content = self.translate(token.get('tokens', []))
        return f'<blockquote>\n{content}\n</blockquote>'

    def _render_codeBlock(self, token):
        """渲染代码块: <pre><code class="...">...</code></pre>"""
        lang = token.get('lang', '')
        code = token.get('text', '')
        # HTML 转义代码内容，防止 <script> 等被执行
        escaped_code = html.escape(code)
        
        class_attr = f' class="language-{lang}"' if lang else ''
        return f'<pre><code{class_attr}>{escaped_code}</code></pre>'

    def _render_list(self, token):
        """
        渲染列表容器 (AST Parser 有时将 list 作为容器，有时直接返回 list_items)
        注意：根据你的 AST 结构，list 节点本身包含了 tokens (list_items)
        """
        # 你的 AST 解析器似乎将整个列表作为一个 type="list" 的节点
        # 里面包含了 tokens (即 list_item 列表)
        # 我们需要检查第一个 item 的 listType 来决定是 <ul> 还是 <ol>
        # 但混合列表（有序+无序）在同一个 list 节点中比较少见，通常会被拆分
        # 这里做一个简单的推断
        
        items_html = self.translate(token.get('tokens', []))
        
        # 简单的启发式判断：看第一个子项是否是有序的
        is_ordered = False
        if token.get('tokens') and len(token['tokens']) > 0:
            if token['tokens'][0].get('listType') == 'ordered_list':
                is_ordered = True
                
        tag = 'ol' if is_ordered else 'ul'
        return f'<{tag}>\n{items_html}\n</{tag}>'

    def _render_list_item(self, token):
        """渲染列表项: <li>...</li>"""
        content = ""
        
        # 处理任务列表 Checkbox
        if token.get('listType') == 'task_list':
            is_checked = token.get('taskFinish', False)
            checked_str = 'checked' if is_checked else ''
            # input 设为 disabled，仅作展示
            content += f'<input type="checkbox" disabled {checked_str}> '

        # 渲染列表项内容
        # 注意：list_item 的 tokens 通常包含 paragraph，但也可能直接包含 text
        # 如果直接包含 paragraph，paragraph 会带 <p> 标签，这在 li 中是合法的但有时会导致间距过大
        # 视具体 CSS 需求而定，这里直接递归渲染
        content += self.translate(token.get('tokens', []))
        
        return f'<li>{content}</li>'

    def _render_table(self, token):
        """渲染表格"""
        # 1. Header
        header_html = ""
        if token.get('header'):
            headers = []
            aligns = token.get('align', [])
            for idx, cell_tokens in enumerate(token['header']):
                align_style = ""
                if idx < len(aligns) and aligns[idx] != 'none':
                    align_style = f' style="text-align: {aligns[idx]}"'
                
                cell_content = self.translate(cell_tokens)
                headers.append(f'<th{align_style}>{cell_content}</th>')
            header_html = f'<thead><tr>{"".join(headers)}</tr></thead>'

        # 2. Body
        body_html = ""
        if token.get('rows'):
            rows_html = []
            aligns = token.get('align', [])
            for row in token['rows']:
                cells = []
                for idx, cell_tokens in enumerate(row):
                    align_style = ""
                    if idx < len(aligns) and aligns[idx] != 'none':
                        align_style = f' style="text-align: {aligns[idx]}"'
                    
                    cell_content = self.translate(cell_tokens)
                    cells.append(f'<td{align_style}>{cell_content}</td>')
                rows_html.append(f'<tr>{"".join(cells)}</tr>')
            body_html = f'<tbody>\n{"".join(rows_html)}\n</tbody>'

        return f'<table>\n{header_html}\n{body_html}\n</table>'

    def _render_callout(self, token):
        """
        渲染 Obsidian Callout
        转换为带有特定 class 的 div
        """
        callout_type = token.get('calloutType', 'note').lower()
        title_tokens = token.get('title', [])
        content_tokens = token.get('tokens', []) # 注意：这里你的 AST 解析器似乎将内容放在 tokens 里，或者 text 里
        
        # 渲染标题
        title_html = "Callout"
        if title_tokens:
             # title 是一个 AST 列表 (inline)
             title_html = self.translate(title_tokens)
        
        # 渲染内容
        # 如果 tokens 存在则优先使用 tokens（结构化内容），否则使用 text
        content_html = ""
        if content_tokens:
             content_html = self.translate(content_tokens)
        else:
             # 如果内容只是纯文本
             content_html = html.escape(token.get('text', ''))

        fold_class = ""
        if token.get('fold') == 'collapse':
            fold_class = " is-collapsed"
        
        # 构建 HTML 结构
        # 这里使用常见的 Callout HTML 结构
        return f'''
<div class="callout callout-{callout_type}{fold_class}">
    <div class="callout-title">
        <div class="callout-icon"></div>
        <div class="callout-title-inner">{title_html}</div>
    </div>
    <div class="callout-content">
        {content_html}
    </div>
</div>
'''

    def _render_cardLink(self, token):
        """渲染卡片链接"""
        url = token.get('url', '#')
        title = token.get('title', 'Link')
        host = token.get('host', '')
        
        return f'''
<div class="card-link">
    <a href="{url}" target="_blank">
        <div class="card-link-title">{title}</div>
        <div class="card-link-host">{host}</div>
    </a>
</div>
'''

    def _render_comment(self, token):
        """渲染注释: HTML 注释"""
        text = token.get('text', '')
        # 移除可能的 Obsidian 注释标记 %%
        if text.startswith('%%'):
            text = text[2:]
        if text.endswith('%%'):
            text = text[:-2]
        return f'<!-- {html.escape(text.strip())} -->'

    def _render_footNoteSign(self, token):
        """渲染脚注引用: <sup><a href="#fn-1">[1]</a></sup>"""
        order = token.get('order', '')
        return f'<sup><a href="#fn-{order}" id="fnref-{order}">[{order}]</a></sup>'

    def _render_footNoteContent(self, token):
        """渲染脚注内容"""
        order = token.get('order', '')
        content = ""
        # 脚注内容通常包含 text 或 token
        if 'token' in token:
            content = self.translate(token['token'])
        else:
            content = html.escape(token.get('text', ''))
            
        return f'<div class="footnote" id="fn-{order}"><sup>[{order}]</sup> {content} <a href="#fnref-{order}">↩</a></div>'

    # -------------------------------------------------------------------------
    # 行内元素渲染 (Inline Elements)
    # -------------------------------------------------------------------------

    def _render_text(self, token):
        """渲染纯文本"""
        return html.escape(token.get('text', ''))

    def _render_strong(self, token):
        """渲染粗体"""
        content = self.translate(token.get('tokens', []))
        return f'<strong>{content}</strong>'

    def _render_italic(self, token):
        """渲染斜体"""
        content = self.translate(token.get('tokens', []))
        return f'<em>{content}</em>'

    def _render_del(self, token):
        """渲染删除线"""
        content = self.translate(token.get('tokens', []))
        return f'<del>{content}</del>'

    def _render_mark(self, token):
        """渲染高亮"""
        content = self.translate(token.get('tokens', []))
        return f'<mark>{content}</mark>'

    def _render_codeSpan(self, token):
        """渲染行内代码"""
        return f'<code>{html.escape(token.get("text", ""))}</code>'

    def _render_link(self, token):
        """渲染普通链接"""
        href = token.get('src', '#')
        text = token.get('text', '')
        return f'<a href="{href}" target="_blank">{text}</a>'

    def _render_image(self, token):
        """渲染图片"""
        src = token.get('src', '')
        alt = token.get('alt', '')
        width = token.get('width')
        height = token.get('height')
        
        style = ""
        if width:
            style += f"width: {width}px;"
        if height:
            style += f"height: {height}px;"
            
        style_attr = f' style="{style}"' if style else ""
        return f'<img src="{src}" alt="{alt}"{style_attr}>'

    def _render_wikiLink(self, token):
        """
        渲染 Wiki 链接 [[Link]]
        """
        target = token.get('target', '')
        display = token.get('display', target)
        # 这里需要根据你的系统逻辑生成实际 URL
        # 暂时生成一个占位链接
        return f'<a href="/wiki/{target}" class="internal-link">{display}</a>'
    
    def _render_escape(self, token):
        """渲染转义字符"""
        return html.escape(token.get('text', ''))
