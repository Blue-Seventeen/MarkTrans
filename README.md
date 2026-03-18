<p align="center">
  <img src="./doc/images/MARKTRANS_LOGO_V3.svg" alt="MarkTrans Logo" width="860" />
</p>

<p align="center">
    <a href="./README.md">中文说明</a> | <a href="./README.en.md">English Manual</a>
</p>

# 0x01：MarkTrans —— ⚡项目概述

**MarkTrans** 是一款使用 Python 语言开发的基于 **规则引擎** 的 Markdown 转换工具。该工具通过读取预先配置在 `/res/database.db` 中的规则，将 Markdown 文本转换为用户需要的 HTML 格式。

本项目采用双阶段架构设计：

1.  **AST 转换**：通过可配置的规则库（SQLite）将 Markdown 解析为抽象语法树（AST）。
2.  **HTML 渲染**：依据自定义规则将 AST 渲染为符合特定场景需求的 HTML 结构。

通过此架构，该项目支持各种非标准 Markdown 扩展语法的识别与转换，适用于需要深度定制内容发布流程的自媒体平台及静态站点生成场景。
# 0x02：MarkTrans —— 🎬 项目预览

![IMAGE_001](./doc/images/IMAGE_001.gif)
# 0x03：MarkTrans —— 🚀 快速开始
## 0x0301：MarkTrans · 快速开始 — 环境要求

- Python 3.8+
## 0x0302：MarkTrans · 快速开始 — 安装与运行

1. **克隆项目**

```bash
git clone https://github.com/Blue-Seventeen/MarkTrans.git
cd MarkTrans
```

2.  **安装依赖**

```bash
pip install -r requirements.txt
```

3.  **启动 Web 服务**

```
python app.py
```

# 0x04：MarkTrans —— 📂 项目结构
## 0x0301：MarkTrans · 项目结构 — 目录结构

别看文件很多，核心的也就三个文件：存放映射规则的 database.db，读取规则并将 Markdown 转换为 AST 格式的 markdown_ast_parser.py 以及将 AST 格式转换为 HTML 的 ast_html_translator.py。

```
MarkTrans/
├── doc/        # 存放一些开发文档
├── res/        # 存放资源类文件
│   ├── images/         # 存放图片类文件
│   ├── static/         # 存放前端需要的一些 js 和 css 文件
│   ├── templates/      # 存放前端界面的模板 html 文件
│   ├── database.db     #（核心）里面存放了各种转换规则
│   └── database_template.db    # （核心）这个是模板数据库，如果 database.db 的原始内容不幸被修改，可以利用这个数据库恢复
├── src/        # 存放代码类资源
│   ├── main/    # 存放主代码类资源（项目的核心代码）
│   │   ├── ast_html_translator/ #（核心）该文件夹的代码主要通过读取数据库将 AST 转换为 HTML 格式
│   │   └── markdown_ast_parser/ #（核心）该文件夹的代码主要通过读取数据将 Markdown 转换为 AST 格式
│   └── test/    # 存放测试类代码资源（主要是测试 main 中的代码能不能完成预期工作）
│       ├── ast_html_translator/   # 用于测试 main 中的 ast_html_translator
│       └── markdown_ast_parser/   # 用于测试 main 中的 markdown_ast_parser
├── app.py      # Web 服务页面，为了展现功能才随便写的网页
└──  database.py # 数据库服务，它可以帮你根据 database_template.db 重置 database.db
```
## 0x0302：MarkTrans · 项目结构 — 数据库结构

本项目的核心就是依赖 database.db（SQLite）数据库中的三张表，这三张表中存放了具体的映射规则以及映射模板，掌握了这三个数据库的结构，也就掌握了整个项目的转换原理，方便用户自定义属于自己的映射样式。
### 1. mapping_base 表

database.db 中的 mapping_base 表中存放了当前项目所有支持的 Markdown 格式，该表的结构如下：

```mysql
id : int 型，自增，用于标识每一个 Markdown 样式
element_name : str 型，Markdown 格式中文名（比如：一级标题）
element_name_en : str 型，唯一，Markdown 格式英文名（比如：Heading 1）
element_description: str 型，用于描述 Markdown 格式注意点（比如：以 # 号 + 空格开头的块级别格式）
element_category：str 型，用于描述格式类别 [（Block Elements）| （Inline Elements）]
weight : int 型，格式权重，权重越高，该格式的规则越先被处理
ast_example_input : str 型，用于存放一个演示案例（比如: # 一级标题）
ast_example_output : str 型，用于存放一个演示的 AST 输出，便于后期开发对照
element_regex_rule : str 型，用于存放匹配该格式的正则表达式（比如：^# (.*)\n?）
element_handler_name: str 型，用于存放用来转换该 Markdown 格式的函数名称
```

针对上面的结构，有如下几点需要说明：

1. **element_category：** 所谓块级（Block）格式，即该格式自身就独占一块，比如常见的代码块，引用块，标题块等；所谓的行内（Inline）格式，即该格式可以被包含在块级格式内使用，比如常见的加粗，倾斜等。
2. **element_regex_rule：** 这个是用来匹配对应格式的正则表达式，有的格式内部复杂，无法通过一个正则把整个块匹配，此时用户可以仅写一个正则来匹配该格式的开头，剩下未匹配的内容我们可以通过编写代码来完成（笔者一开始妄想仅通过正则就实现 Markdown 格式的分解，后面发现太天真了，于是采用来正则 + 对应代码块的方式来拆解 Markdown 格式）。
3. **element_handler_name：** 这个是用来指定 markdown_ast_parser.py 中调用哪个函数来处理该格式的字段，这个我们在 **扩展开发** 部分会讲解到。
### 2. mapping_style 表

database.db 中的 mapping_style 表中则是用来管理用户预设的样式组的（即 AST => HTML 的模板组），方便用户后期在多个样式集中一键切换，该表的结构如下：

```mysql
id : int 型，自增，用来标注样式 id
style_name : str 型，风格名称（比如：系统默认风格）
is_active : int 型，标注当前正在使用的风格（为 1 时，代表该风格正在使用，为 0 代表未启用）
is_deletable : int 型，标注当前风格是否允许被删除（为 0 时，代表该风格不允许被删除）
remark : str 型，风格备注，这个可以由用户自定义
```

针对上面的结构，有如下几点需要说明：

1. **is_active：** 用户可以设置多个风格，但同一时间只能启用一种风格。
2. **is_deletable：** 系统默认的风格（id = 1）不推荐用户删除，因为系统需要一种风格作为兜底选择，如果全部删除，系统将不知道依据什么模板将 AST 转换为 HTML 格式。
### 4. mapping_rule 表

database.db 中的 mapping_rule 表中存放了具体的 AST 转 HTML 的映射模板和匹配规则，方便 ast_html_translator.py 读取并依据规则进行转换：

```mysql
id : int 型，主键，自动递增
style_id : int 型，样式 ID，用于关联 maping_style 表中的样式
style_rule_name: str 型，样式规则名称（比如：一级标题）
ast_input : str 型，AST 的输入案例（这个是通过 markdown_ast_parser.py 解析得到）
matching_rule : str 型，命中的规则，若检测到 AST 符合该规则，则将此 AST 按 html_output 进行转换
html_output : str 型，用于进行渲染的 HTML 模板，自定义部分通过 `§token['属性']§` 进行占位
render_name: str 型，此字段与 ast_input 中的 type_name 保持一致即可，决定了后续渲染该格式的方法
weight: int 型，权重信息（决定了解析顺序，权重按照 style_id 分组，不同的 style_id 权重互不影响）
```
# 0x05：MarkTrans —— 🛠️ 扩展开发

在进行扩展开发前，笔者要先 Say Sorry 一下，在笔者预先的发布计划中是准备为已经支持的 44 种格式每个都配置一个 HTML 模板，但是，任务量实在太大，最终，笔者只配置了 14 个。

本着授人以鱼不如授人以渔的态度，项目的核心逻辑已经疏通了，剩下的部分主要就是自定义渲染模板了，所以这里，笔者将列举两个案例，来教用户如何使用本项目支持拓展 Markdown 格式，并渲染出自己想要的 HTML 结构。
## 0x0501：MarkTrans · 扩展开发  — Easy Heading 1

第一个扩展开发案例，是兼容 Heading 1 格式，即一级标题格式，难度为 Easy：
### 1. mapping_base 表新增拓展格式

要想让项目支持解析一级标题格式，我们首先得来到项目的 mapping_base 表，新增一条数据（我们可以通过前端 Web 的 “规则与数据管理” 页面实现）：

![IMAGE_002](./doc/images/IMAGE_002.png)

来看一下新增规则我们需要填写哪些内容：

1. **element_name：** Markdown 格式中文名（这边直接写 “一级标题” 即可）
2. **element_name_en：** Markdown 格式英文名（这边直接写 “Heading 1” 即可）
3. **element_description：** Markdown 格式描述（可以不写的，不影响）
4. **element_category：** Markdown 格式分类（标题都是独占一行的，属于块级（Block）格式）
5. **weight：** 权重信息（没啥注意的，别高于转义字符就行，这里笔者设置了 70）
6. **ast_example_input：** 其实就是 Markdown 格式样本（比如：# Title）
7. **ast_example_output：** 你期待该格式应该转换成什么样的 AST 结构，需要自己设计
8. **element_regex_rule：** 用于匹配该格式的正则表达式，可以用 AI 生成
9. **element_handler_name：** 你期望该格式由哪个函数处理（得到 AST 结构）

纵观上面这些内容，也就是 **ast_example_output** 和 **element_regex_rule** 有点难搞需要自己设计一下。我们一个一个来，首先是 **ast_example_output**（你可以不写到数据库中，但是你需要设计字段，即你期待从这个格式中提取出哪些有用信息），这里笔者给出自己设计的格式：

```bash
{                       # 被这个 { 包裹在内的笔者称其为 token
  "type": "heading",    # 当前格式的类型，属于 heading，即标题
  "raw": "# Title\n",   # 当前格式的字符串原始文本，即你通过正则匹配的内容
  "depth": 1,           # 这个其实是标题层级，一级标题 depth = 1, 二级标题 depth = 2
  "text": "Title",      # 这个存放了标题的内容，注意哦，标题内容中可能会含有加粗在内的行内格式哦
  "tokens": [           # 这个是对 text 进行递归解析，看内部是否存在其它格式
    {
      "type": "text",   # 代表这是一个 text 格式，最小的文本单元
      "raw": "Title",   # 原始内容为 Title
      "text": "Title"   # 内部的纯文本为 Title
    }
  ]
}
```

其次是 **element_regex_rule**，即用来匹配该格式的正则表达式，这个比较重要，是一定要写的，如果不知道怎么写可以让 AI 帮你，下面是笔者设计的来匹配一级标题的正则：

```bash
^# (.*)\n?
```

![IMAGE_003](./doc/images/IMAGE_003.jpeg)

OK，最终我们设计成功后的样式如下（主要填写 **element_name**，**element_name_en**，**weight**,**element_category**，**element_regex_rule**，**element_handler_name**）：

![IMAGE_004](./doc/images/IMAGE_004.png)
### 2. markdown_ast_parser 新增 handle 函数

在上一步的设计中，我们新增了 “一级标题” 格式，以及该格式的正则匹配语法和后端处理函数的名称。接下来我们就要到 markdown_ast_parser.py 中编写具体的处理函数了。将 Markdown 转换为 AST 格式的处理函数的语法格式如下：

```python
@print_return
def _handle_myCustomSyntax(self, match, rule, text):
    """
    :param match: 正则匹配对象，即 re.compile(element_regex_rule, re.MULTILINE).match(text)
    :param rule: 当前匹配的规则
        格式: 
            {
                'name' : element_name_en,            // 对应格式的英文名称，此字段唯一
                'weight' : weight,                   // 对应格式的权重，数值越大越优先处理
                'regex' : element_regex_rule,        // 对应格式的正则匹配表达式（仅匹配开始字段，符合要求的就被视为该格式）
                'compiled_regex' : None,             // 编译后的正则表达式对象，用于后续匹配
                'handler' : element_handler_name,    // 对应格式的处理函数名，用于处理匹配到的文本
                'scope' : '(block/inline)'      // 对应格式的作用域，block 表示块级元素，inline 表示行内元素
            }
    :param text: 剩余的原始文本
    :return: 标题节点 , 消耗的字符长度
    """
    # 解析逻辑...
    return token, consumed_length
```

我们在 markdown_ast_parser.py 中合适的部分插入上面的函数，然后编写对应的解析逻辑，下面是笔者编写的用来构造我们前面设计的 “一级标题” 的 AST 解析代码（因为我们在数据库中填写的 **element_handler_name** 为 **heading**，所以这个函数的名称就叫 **`_handle_heading`**）：

![IMAGE_005](./doc/images/IMAGE_005.jpeg)

在 Markdown 中，标题里也是可以部分加粗倾斜的，即可以嵌套部分行内格式，所以在上面构造 AST 结构时，我的 `tokens` 字段写成 `self.parse(match.group(1), 'inline')`，其实就是递归以行内格式解析标题内容，最终会返回标题内容的 AST 节点格式。

那么，至此，我们的系统已经成功认识了 “一级标题” 格式，能成功识别该格式的 Markdown 语法并将其转换为我们设计的 AST 格式了。
### 3. mapping_rule 表新增映射格式

在前面两步中，我们主要是让系统完成，识别 Markdown 特定语法并将其转换为 AST 格式。那么下面，我们就要让系统识别 AST 格式，并将其渲染为我们想要的 HTML 格式。

为了不与我们之前设置的映射格式搞混，我们来到系统的 “风格管理” 界面，选择基于 “系统默认风格” 创建一个 “自定义测试风格”，填写好信息后，点击 “基于选中风格创建新的风格” 即可：

![IMAGE_006](./doc/images/IMAGE_006.jpeg)

创建好新风格后，我们点击 “编辑”，然后找到对应的 style_rule_name，笔者之前是写过 “一级标题” 的映射规则的，如果没有写过，那就点击 “新增规则” 就好啦：

![IMAGE_007](./doc/images/IMAGE_007.jpeg)

来看一下这里我们需要填写哪些内容：

1. **style_rule_name：** 渲染样式规则名称（比如：一级标题） 
2. **render_name：** 后续执行渲染逻辑的渲染方法
3. **weight：** 权重信息，决定了规则匹配的优先级（如果你觉得哪个格式常用，可以把优先级调高）
4. **ast_input：** AST 输入案例，即我们前面设计的 AST 格式（可以忽略不写）
5. **matching_rule：** 命中的规则，如果符合要求，则会交给对应的 render_name 函数处理
6. **html_output：** 用于渲染的 HTML 模板（行内格式）

这里介绍几个主要的，首先是 **render_name** 字段，该字段一般与 AST 的 type 字段一致，我们刚刚设计的是 `heading`，所以这里也填 `heading` 即可。然后是 **matching_rule** 字段，即命中的规则，我们先回顾一下我们设计的 AST 格式：

```bash
{                       # 被这个 { 包裹在内的笔者称其为 token
  "type": "heading",    # 当前格式的类型，属于 heading，即标题
  "raw": "# Title\n",   # 当前格式的字符串原始文本，即你通过正则匹配的内容
  "depth": 1,           # 这个其实是标题层级，一级标题 depth = 1, 二级标题 depth = 2
  "text": "Title",      # 这个存放了标题的内容，注意哦，标题内容中可能会含有加粗在内的行内格式哦
  "tokens": [           # 这个是对 text 进行递归解析，看内部是否存在其它格式
    {
      "type": "text",   # 代表这是一个 text 格式，最小的文本单元
      "raw": "Title",   # 原始内容为 Title
      "text": "Title"   # 内部的纯文本为 Title
    }
  ]
}
```

上面这个结构代表的就是一级标题，下面看一下笔者填写的命中规则（type 要为 'heading' 且层级为 1 级）：

```bash
token['type'] == 'heading' and token['depth'] == 1
```

这就是我们要在 **matching_rule** 中填写的内容，其实就是伪 Python 判断表达式。

再来看最后一个字段，即 **html_ouput** 即渲染的 HTML 模板，简单点的写法可以写下面这样：

```bash
<h1>§token['tokens']§</h1>
```

这样在后面进行渲染时，一级标题的 AST 中的 "tokens" 内容就会被渲染到 `<h1></h1>` 标签之间。但是这样的 H1 标签很没有灵魂，所以我设计的有灵魂的 H1 标签如下（增加了部分行内样式）：

```html
<div dir="ltr" style="display:block;clear:left;margin:-2em 0 -3em 0;position:relative;white-space:break-spaces;word-break:break-word;">
        <span style="display:block;font-family:inherit;font-size:1.802em;font-weight:700;line-height:1.2;letter-spacing:-0.015em;color:rgb(243, 139, 168);margin:0;padding:0;text-indent:0;">§token['tokens']§</span>
    </div>
```

我们来整体看一下最终填写的成果：

![IMAGE_008](./doc/images/IMAGE_008.png)
### 4. ast_html_translator.py 新增 render 函数

在上一步的设计中，我们新增了 “一级标题” 的渲染规则，接下来我们就需要到 ast_html_translator.py 中编写具体的渲染函数了。将 AST 转换为 HTML 格式的处理函数的语法格式如下：

```python
def _render_myCustomSyntax(self, token, rule_list):
    """
    :param token : AST 中对应的节点
    :param rule_list : 匹配的规则列表
    :return "渲染后的 html 代码"
    """
    # 渲染逻辑
    return html_output_template
```

在进行渲染的过程中笔者发现了一个特点，就是大部分的渲染其本质都是模板的替换，比如 `<h1>text</h1>`其外围包裹的 `<h1>` 是不变的，变的仅仅是 `text` 而已，所以针对这种通过替换关键字来进行渲染的样式，笔者特地编写了一个通用方法，叫 `_render_easy()`，这里我们调用一下就可以了：

![IMAGE_009](./doc/images/IMAGE_009.png)

当然，如果你感兴趣的话，可以追踪一下函数的实现，整体逻辑其实不是很复杂。

OK，那么至此，我们就已经成功为我们的系统新增了一个 “一级标题” 的样式，我们去前端执行一下转换看看结果（HTML 是可以切换到源码查看的）：

![IMAGE_010](./doc/images/IMAGE_010.png)

OK，如果这个渲染的结果你不是很满意，我们还可以让 AI 再设计一个赛博朋克风的：

![IMAGE_011](./doc/images/IMAGE_011.jpeg)

我们拿着第一步在 mapping_base 中预设的样式让 AI 重新设计后再次填写到 mapping_base 表中就完成了渲染模板的修改：

![IMAGE_012](./doc/images/IMAGE_012.jpeg)

修改完毕后，我们重新执行一下渲染看看 AI 给的样式结果如何：

![IMAGE_013](./doc/images/IMAGE_013.jpeg)

怎么样，是你喜欢的样式嘛，OK，那么至此，我们已经完成了一套简单语法的扩展开发。
## 0x0502：MarkTrans · 扩展开发 — Hard Table

第二个扩展开发案例，是兼容 Table 格式，即表格格式，难度为 Hard。该格式截至笔者写这篇说明书时还未完成兼容，所以笔者是一边撸代码一边写这个的，先看一下开发前的系统表现：

![IMAGE_014](./doc/images/IMAGE_014.png)

笔者目前已经完成了从 Markdown 到 AST 结构的转换部分，但是渲染部分还未完全开发完成，OK，那么接下来我们就完整的梳理一遍表格格式的兼容。
### 1. mapping_base 表新增拓展格式

第一步，先通过前端的 “规则与数据管理” 功能来到项目的 mapping_base 表，找到 ”表格“规则，我们过一遍：

![IMAGE_015](./doc/images/IMAGE_015.png)

相信用户比较在意的是两点，一个是 AST 结构的设计，一个是用来匹配表格格式的正则应该怎么写，下面我们一个一个分析一下。

对于设计 AST 结构，我们说白了，就是你觉得你需要从这个格式中提取出哪些有效信息，来方便你后期通过 HTML 重新渲染这个格式。对于表格，笔者梳理出了以下有效信息：

1. 表格的列对齐格式（这个需要参考 Markdown 表格语法） => AST 设计：通过 align 字段标注
2. 表格由几行几列构成 => AST 设计：通过  columnCount 与 rowCount 字段标注
3. 表格的标题行具体内容结构是啥 => AST 设计：通过 header 字段标注
4. 表格每列的的具体内容解雇是啥 => AST 设计：通过 rows 字段标注

OK，基于上述有效信息，笔者设计的表格的 AST 语法格式如下（缩略版）：

```json
{
    "type" : "table",  // 标注 AST 结构类型
    "raw": "| H1  | H2  |\n| --- | --- |\n| C1  | C2  |", // 构成表格的 Markdown 格式原样
    "align" : ["center", "center"], // 标注每列的对齐方式, 默认为 center
    "rowCount": 2,      // 标注表格行数
    "columnCount" : 2,  // 标注表格列数
    "header" : [        // 标注表格标题具体结构
        [第一列标题的格式组], // 表格中每个单元格内都是可以内嵌行内格式的
        [第二列标题的格式组]
    ],
    "rows" : [
        [[第一列内容的格式组],[第二列内容的格式组]]   // 这一行对应的是表格的第二行
    ]
}
```

AST 结构设计好了，第二个难点就是正则了，好在有 AI 帮忙，下面是 AI 设计的用于匹配 Markdown 表格格式的正则语法：

```bash
^ *\|(.+)\n *\|( *[-:]+[-| :]*)\n((?: *\|.*(?:\n|$))*)
```

![IMAGE_016](./doc/images/IMAGE_016.png)

OK，现在我们已经可以完全匹配出表格格式了，然后又设计出了表格对应的 AST 结构了，那么下面我们就是要去 markdown_ast_parser.py 中编写具体的处理函数了，即 `_handle_table()`。
### 2. markdown_ast_parser 新增 handle 函数

在上一步中我们已经完成了对表格格式的 AST 设计，那么这一步，我们就是编写函数来从正则匹配到的内容中提取出我们需要的属性，比如表格由几行几列构成，每行对齐方式是啥 。。。，提取出这些信息后，我们要将其组装成一个 AST 节点，然后返回该节点与我们已经处理的文本长度：

```python
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
                align_list.append("center")

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
```

上面是笔者编写的用来构造 AST 节点的代码逻辑，感兴趣的小伙伴可以瞅瞅，虽然很长，但其实都是比较 Easy 的字符串处理，反正简而言之，经过上面代码的处理，我们的 Markdown 就转换成我们预设的 AST 结构啦。
### 3. mapping_rule 表新增映射格式

我们得到 AST 后，下一步就是设计表格对应的渲染格式了，我们可以先让 AI 给我们设计一个表格的样式：

![IMAGE_017](./doc/images/IMAGE_017.png)

AI 设计的表格还是挺炫的，但是结构过于复杂，笔者简单精简了一下变成了下面这样：

![IMAGE_018](./doc/images/IMAGE_018.png)

其对应的一行一列的 HTML 代码如下（变成一行一列是为了方便我们提取特征）：

```html
<table style="
    width:100%;
    border-collapse:separate;
    border-spacing:0;
    font-family:'SF Mono','Monaco','Inconsolata','Fira Code','Consolas','monospace';
    font-size:0.85em;
    background:#0d1117;
    color:#c9d1d9;
    border:1px solid #30363d;
    border-radius:6px;
    overflow:hidden;
">
    <thead style="background:transparent;">
        <tr>
            <th style="padding:12px 16px;text-align:center;font-weight:600;color:#58a6ff;border-bottom:2px solid #21262d;text-transform:uppercase;letter-spacing:0.05em;font-size:0.9em;">ID</th>
        </tr>
    </thead>
    <tbody>
        <tr style="background:#161b22;">
            <td style="padding:10px 16px;border-bottom:1px solid #21262d;color:#f0f6fc;text-align:center;">#A001</td>
        </tr>
    </tbody>
</table>
```

![IMAGE_019](./doc/images/IMAGE_019.jpeg)

拿到了我们最终想要渲染的结果了，接下来，就是按块渲染。按块渲染的前提，是看我们要把表格拆分出哪几块，笔者拆出了：`<table>`、`<th>`、`<tr>`（除去表格标题的 `tr`）、`<td>` 这几个模块（当然你可以拆分的更细，这样更方便了以后的自定义格式）。

接下来是为每一块都去 mapping_rule 表中新增一个对应的渲染规则：
#### 3.1 Add Rule — table · \<table\>

首先新增的是 `表格 — <table>` 渲染，笔者这里填写的 html_output 内容如下（下面的 § 只是一个占位符，方便我们待会处理的时候把对应内容放进去）：

```html
<table style="
    width:100%;
    border-collapse:separate;
    border-spacing:0;
    font-family:'SF Mono','Monaco','Inconsolata','Fira Code','Consolas','monospace';
    font-size:0.85em;
    background:#0d1117;
    color:#c9d1d9;
    border:1px solid #30363d;
    border-radius:6px;
    overflow:hidden;
">
    <thead style="background:transparent;">
        <tr>
            §表格 — <th>§
        </tr>
    </thead>
    <tbody>
            §表格 — <tr>§
    </tbody>
</table>
```

完整的表格如下：

![IMAGE_020](./doc/images/IMAGE_020.png)
#### 3.2 Add Rule — table · \<th\>

然后是新增 `表格 - <th>` 渲染，笔者填写的 html_output 内容如下（这里的 `§text§` 没啥特殊的只是用来占位而已）：

```html
<th style="padding:12px 16px;text-align:center;font-weight:600;color:#58a6ff;border-bottom:2px solid #21262d;text-transform:uppercase;letter-spacing:0.05em;font-size:0.9em;">§text§</th>
```

完整的表单如下：

![IMAGE_021](./doc/images/IMAGE_021.jpeg)
#### 3.3 Add Rule — table · \<tr\>

再然后是新增 `表格 - <tr>` 渲染，笔者填写的 html_output 内容如下：

```html
<tr style="background:#161b22;">
    §td§
</tr>
```

完整的表单如下：

![IMAGE_022](./doc/images/IMAGE_022.png)
#### 3.4 Add Rule — table · \<td\>

最后一个是新增 `表格 - <td>` 渲染，笔者填写的 html_output 内容如下：

```bash
<td style="padding:10px 16px;border-bottom:1px solid #21262d;color:#f0f6fc;text-align:center;">§text§</td>
```

完整的表单如下：

![IMAGE_023](./doc/images/IMAGE_023.png)
### 4. ast_html_translator.py 新增 render 函数

在上一步的设计中，我们新增的 ”表格“ 的渲染规则，接下来我们需要到 ast_html_translator.py 中编写具体的渲染函数了，下面是笔者编写的渲染逻辑（其底层其实就是把这种复杂的需要拆分多块进行渲染的格式交给一个特定的函数依据规则进行渲染）：

```python
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
```

OK，至此，我们已经成功为我们的系统新增了一个 ”表格“ 样式，我们看看渲染后的结果：

![IMAGE_024](./doc/images/IMAGE_024.png)

我们还可以修改成三行三列的，然后每个格子里还可以嵌套行内格式：

![IMAGE_025](./doc/images/IMAGE_025.jpeg)

那么至此，我们已经成功完成了一套复杂语法的扩展开发。

## ❤️ 支持项目（打赏）

如果这份项目或手册对你有帮助，欢迎请作者喝杯咖啡 （打赏时记得留下 ”昵称 + 赞助项目名称（MarkTrans） + 修改建议 OR 优化建议 或留言（留个个人主页地址也行）“ 笔者会定时更新赞助名单哒）☕

<p align="center">
  <img src="./doc/images/206d3bb2b3bdb036caa9addfacabe9e5.jpg" alt="微信打赏码" width="220" />
    <img src="./doc/images/DONATE_ALIPAY.jpg" alt="支付宝打赏码" width="220" />
    <img src="./doc/images/c78611178dfe86b8e0f6916a40294505.jpg" alt="支付宝红包码" width="220" />
</p>

你也可以通过以下方式支持项目：

- 给仓库点一个 Star
- 提交 Issue / PR
- 分享你的实践反馈

## 🤝 交流学习

欢迎加入交流学习渠道（后续我会持续更新内容）：

<p align="center">
  <img src="./doc/images/COMMUNITY_QQ_1.jpg" alt="QQ交流群二维码" width="220" />
  <img src="./doc/images/COMMUNITY_WECHAT_CHANNEL_1.jpg" alt="微信公众号二维码" width="220" />
</p>