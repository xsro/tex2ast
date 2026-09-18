# tex2ast

支持 XeLaTeX 的 LaTeX 转 AST 工具，支持往返转换和实用命令。

## 功能

- **LaTeX 转 AST**：将 LaTeX 文件解析为带位置信息的抽象语法树
- **往返转换**：tex → json → tex 输出完全一致
- **changes 包**：剥离 `\added`、`\deleted`、`\replaced` 标记，生成新旧版本
- **依赖分析**：查找所有引用的 input/graphics 文件，清理未引用的文件
- **BibTeX 提取**：将引用的 bib 条目导出到新文件
- **展开 include**：将 `\input` 和 `\include` 合并为单个自包含 .tex 文件
- **构建自动化**：按顺序运行 xelatex/pdflatex/biber/bibtex 并跟踪文件
- 完整的 XeLaTeX 语法支持（CJK、数学、表格、图片等）

## 安装

```bash
git clone <repository-url>
cd tex2ast

uv venv
uv pip install -e .
```

## 命令

### `tex2ast ast` - 将 LaTeX 转换为 AST JSON

```bash
tex2ast ast -i document.tex -o document.json
tex2ast ast -i document.tex -o document.json --pretty
```

### `tex2ast tex` - 将 AST JSON 转换回 LaTeX

```bash
tex2ast tex -i document.json -o document.tex
```

### 往返转换

```bash
tex2ast ast -i document.tex -o document.json
tex2ast tex -i document.json -o document.tex
diff document.tex document.tex  # 完全一致！
```

### `tex2ast ast-remove-changes` - 剥离 changes 包标记（基于 AST）

与 `remove-changes` 类似，但使用 AST 转换而非正则表达式，处理更稳健。
支持多行参数（如 `\replaced{新\n行}{旧}`），并正确处理嵌套的 changes 命令。

```bash
tex2ast ast-remove-changes -i document.tex                  # → document_new.tex
tex2ast ast-remove-changes -i document.tex --old            # → document_old.tex
tex2ast ast-remove-changes -i document.tex -o clean.tex     # 自定义输出
tex2ast ast-remove-changes -i document.tex --print_change new   # 同时输出到 stdout
tex2ast ast-remove-changes -i document.tex --changes-list=none         # 禁用自定义命令
tex2ast ast-remove-changes -i document.tex --changes-list=myconfig.txt # 使用自定义配置
tex2ast ast-remove-changes -i document.tex --remove-empty-math           # 移除空数学环境
tex2ast ast-remove-changes --project tex2ast.config.py     # 使用项目配置文件
```

### `tex2ast remove-changes` - 剥离 changes 包标记（基于正则表达式）

支持 `\added`、`\deleted`、`\replaced`、`\comment`、`\highlight` 命令。
递归展开 `\include` 和 `\input` 为单个输出文件。

自定义修订命令可通过 `.config/remove-changes.txt` 配置。
使用 `--changes-list=none` 禁用，或 `--changes-list=<path>` 使用自定义配置。

```bash
tex2ast remove-changes -i document.tex                  # → document_new.tex
tex2ast remove-changes -i document.tex --old            # → document_old.tex
tex2ast remove-changes -i document.tex -o clean.tex     # 自定义输出
tex2ast remove-changes -i document.tex --print_change new   # 同时输出到 stdout
tex2ast remove-changes -i document.tex --print_change no    # 静默
tex2ast remove-changes -i document.tex --changes-list=none         # 禁用自定义命令
tex2ast remove-changes -i document.tex --changes-list=myconfig.txt # 使用自定义配置
tex2ast remove-changes -i document.tex --remove-empty-math           # 移除空数学环境
tex2ast remove-changes --project tex2ast.config.py     # 使用项目配置文件
```

> **注意：** 当某行被完全删除时（如 `\deleted{...}` 占据整行），
> 会保留 `%` 注释以防止 LaTeX 合并段落。
> 多行参数（如 `\replaced{新\n行}{旧}`）完全支持。

| 命令 | 默认（新） | `--old` |
|------|-----------|---------|
| `\added{text}` | 保留文本 | 移除 |
| `\deleted{text}` | 移除 | 保留文本 |
| `\replaced{new}{old}` | 使用新 | 使用旧 |
| `\comment{text}` | 移除 | 移除 |
| `\highlight{text}` | 保留文本 | 保留文本 |

#### 自定义修订命令

`.config/remove-changes.txt` 文件定义额外的修订命令：

- 包含 `{old}` 的行 → 内容被移除
- 包含 `{new}` 的行 → 内容被保留
- 同时包含 `{new}{old}` 的行 → 替换（保留新，移除旧）

默认命令：

```text
\cancel{old}
\xcancel{old}
\sG{old}
\tG{new}
\replaceG{new}{old}
```

#### 项目配置文件

`tex2ast.config.py` 文件可定义项目级设置：

```python
tex2ast_config=dict(
    input_tex="main.tex",
    output_tex="main_clean.tex",
    remove_empty_math=True,
    changes_list=r"""
    \cancel{old}
    \tG{new}
    """,
)
```

使用 `tex2ast remove-changes --project tex2ast.config.py` 运行。
CLI 选项覆盖配置文件设置。

### `tex2ast dependency` - 分析文件依赖

```bash
tex2ast dependency -i document.tex                              # 列出依赖
tex2ast dependency -i document.tex --clean_dir ./figures        # 查找未引用的文件
tex2ast dependency -i document.tex --clean_dir ./figures --run  # 删除未引用的文件
```

输出：
- `!` 标记引用但缺失的文件
- `--clean_dir` 列出目录中未被引用的文件
- `--run` 删除未引用的文件

### `tex2ast extract-bib` - 提取引用的 bib 条目

```bash
tex2ast extract-bib -i document.tex -o cited.bib
tex2ast extract-bib -i document.tex                         # 输出到 stdout
tex2ast extract-bib -i document.tex -o cited.bib --bib refs.bib
```

- 从 `\bibliography` 和 `\addbibresource` 自动检测 bib 文件
- 解析 `\cite`、`\citep`、`\citet`、`\autocite`、`\parencite`、`\textcite`、`\nocite` 等
- 递归处理 `\include`/`\input` 中的引用

### `tex2ast expand` - 合并 include 为单个文件

```bash
tex2ast expand -i main.tex                    # 输出: mainexpanded.tex
tex2ast expand -i main.tex -o merged.tex      # 自定义输出路径
```

- 递归替换 `\input{...}` 为文件内容
- `\include{...}` 替换为包裹 `\clearpage` 的文件内容
- 相对路径从主文件目录解析
- 检测并跳过循环引用

### `tex2ast build` - 运行 LaTeX 构建工具

```bash
tex2ast build -i main.tex --steps xelatex,biber,xelatex,xelatex
tex2ast build -i main.tex --steps xe,bt,xe2 --log-dir ./logs  # 自定义日志目录
tex2ast build -i main.tex --steps pdf,bibtex,pdf2 --pack project.zip  # 打包依赖
tex2ast build -i project.zip --main main.tex --steps pdf,bibtex,pdf2  # 从 zip 构建
```

支持的工具：`xelatex`、`pdflatex`、`biber`、`bibtex`

步骤别名：

| 别名 | 展开为 |
|------|--------|
| `pdf` | `pdflatex` |
| `xe` | `xelatex` |
| `pdf2` | `pdflatex, pdflatex` |
| `xe2` | `xelatex, xelatex` |
| `pdf3` | `pdflatex, pdflatex, pdflatex` |
| `xe3` | `xelatex, xelatex, xelatex` |
| `br` | `biber` |
| `bt` | `bibtex` |

Zip 输入：使用 `-i project.zip --main main.tex` 从 zip 归档中提取并构建。
文件解压到临时目录（`tex2ast/{timestamp}`）。从 zip 构建时忽略 `--pack`。

输出（默认在系统临时目录，用 `--log-dir` 覆盖）：
- `build.log` - 每一步的编译输出
- `build-io.log` - 构建过程中读取的所有文件摘要（绝对路径）

## 路径解析

LaTeX 中的相对路径始终相对于**主 .tex 文件的目录**解析，无论引用文件位于何处。
所有命令均遵循此规则。

## JSON 输出格式

每个 AST 节点包含位置信息：

```json
{
  "type": "LatexAST",
  "children": [
    {
      "type": "Command",
      "pos": {
        "start": {"line": 1, "column": 15, "offset": 0},
        "end": {"line": 1, "column": 38, "offset": 7}
      },
      "name": "documentclass",
      "arguments": [...]
    }
  ],
  "metadata": {},
  "source": "\\documentclass{article}..."
}
```

## 支持的 LaTeX 特性

- 文档结构：`\documentclass`、`\usepackage`、章节
- 文本格式：`\textbf`、`\textit`、`\emph` 等
- 数学：行内 `$...$`、行间 `$$...$$`、环境（equation, align, matrix 等）
- 环境：itemize, enumerate, tabular, figure, table, quote 等
- 交叉引用：`\label`、`\ref`、`\cite`、`\footnote`
- 图片：`\includegraphics`
- 链接：`\href`、`\url`
- 特殊字符：`\#`、`\$`、`\%`、`\&`、`\_`、`\{`、`\}`、`\~`、`\^`
- 中文排版（ctex）
- 逐字环境（lstlisting, verbatim）

## 项目结构

```
tex2ast/
├── src/tex2ast/
│   ├── __init__.py
│   ├── ast_nodes.py      # 带位置信息的 AST 节点定义
│   ├── lexer.py          # LaTeX 词法分析器
│   ├── parser.py         # LaTeX 语法分析器
│   ├── serializer.py     # AST 到 LaTeX 序列化器
│   ├── remove_changes.py # changes 包移除器
│   ├── dependency.py     # 依赖分析器
│   ├── bib_parser.py     # BibTeX 解析器
│   ├── expand.py         # LaTeX include 展开器
│   ├── build.py          # LaTeX 构建自动化
│   └── cli.py            # 命令行接口
├── pyproject.toml
└── README.md
```

## 许可证

MIT License