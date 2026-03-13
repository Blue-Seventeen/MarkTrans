# MarkTrans

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-Alpha%20v0.3.0-orange)](https://github.com/Blue-Seventeen/MarkTrans)

**MarkTrans** 是一个基于**规则引擎**的 Markdown 到 HTML 灵活转换工具。

项目采用双阶段架构：
1.  **AST 解析 (当前重点)**：通过可配置的规则库（SQLite）将 Markdown 解析为抽象语法树（AST）。
2.  **HTML 渲染**：依据自定义规则将 AST 渲染为符合特定场景需求的 HTML 结构。

支持非标准 Markdown 扩展语法的识别与转换，适用于需要深度定制内容发布流程的自媒体平台及静态站点生成场景。

## ✨ 特性 (v0.3.0)

*   **数据库驱动的规则引擎**：所有的解析规则（正则、权重、处理函数映射）均存储在 SQLite 数据库中，支持动态配置。
*   **高度可扩展的 AST 解析器**：
    *   `MarkdownASTParser` 核心类支持 **Block** (块级) 和 **Inline** (行内) 两种解析模式。
    *   通过 `weight` 字段精确控制解析优先级。
    *   支持递归解析嵌套结构。
*   **Web 管理界面 (开发中)**：基于 Flask 提供 API 和简单的管理后台，用于可视化管理解析规则。
*   **支持自定义语法**：已内置支持标准 Markdown 及部分扩展语法（如 Callouts、Card Links 等）。

## 📂 项目结构

```
MarkTrans/
├── src/
│   ├── main/
│   │   └── markdown_ast_parser/  # AST 解析器核心逻辑
│   │       └── markdown_ast_parser.py
│   └── test/                     # 测试用例
├── res/                          # 资源文件
│   ├── database.db               # 规则数据库 (SQLite)
│   ├── static/                   # 静态资源 (CSS/JS)
│   └── templates/                # Flask 模板
├── app.py                        # Web 入口 (Flask)
├── database.py                   # 数据库初始化脚本
├── requirements.txt              # 依赖列表
└── README.md
```

## 🚀 快速开始

### 环境要求
*   Python 3.8+

### 安装与运行

1.  **克隆项目**
    ```bash
    git clone https://github.com/Blue-Seventeen/MarkTrans.git
    cd MarkTrans
    ```

2.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

3.  **初始化数据库**
    ```bash
    # 首次运行会自动创建 res/database.db 并写入默认规则
    python database.py
    ```

4.  **启动 Web 服务**
    ```bash
    python app.py
    ```
    访问 `http://localhost:7000` 查看演示界面，访问 `http://localhost:7000/admin` 管理规则。

## 🛠️ 扩展开发

### 如何新增一种 Markdown 语法支持？

1.  **数据库配置**：在 `mapping_base` 表中新增一条记录，配置正则规则 (`element_regex_rule`) 和权重 (`weight`)。
2.  **编写 Handler**：在 `MarkdownASTParser` 类中新增一个处理方法，命名规则为 `_handle_{handler_name}`。
    ```python
    @print_return
    def _handle_myCustomSyntax(self, match, rule, text):
        # 解析逻辑...
        return token, consumed_length
    ```

## 📄 License

本项目采用 [Apache-2.0](LICENSE) 协议开源。
