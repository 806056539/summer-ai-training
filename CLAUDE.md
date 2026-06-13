# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在此仓库中处理代码时提供指导。

## 概述

一个学生成绩管理命令行应用，从最初的单文件 `task.py` 重构为多模块架构，具有关注点分离、全面的错误处理、详细的文档字符串以及完整的单元测试覆盖。

## 如何运行

```bash
python main.py          # 运行应用程序
```

## 如何测试

```bash
python -m unittest discover tests -v   # 运行全部 124 个测试
```

除 Python 3 标准库外无其他依赖。无需虚拟环境或安装额外包。

原始（未重构）版本保留在 `task.py` 中以供对比。

## 架构

```
main.py                         # App 类：入口点，统一调度（所有处理函数共享相同签名）
student_system/
  __init__.py
  exceptions.py                 # 自定义异常层次结构（StudentSystemError 基类）
  models.py                     # Student 数据类、MenuAction 枚举、validate_score/validate_name
  manager.py                    # StudentManager — 纯业务逻辑，遇到错误抛出异常
  storage.py                    # Storage — 原子化 JSON 文件持久化（临时文件 + os.replace）
  ui.py                         # 所有打印/输入、可复用验证器、KeyboardInterrupt 处理
tests/
  test_exceptions.py            # 异常层次结构测试
  test_models.py                # Student、MenuAction、验证测试
  test_manager.py               # StudentManager CRUD/统计/排名测试
  test_storage.py               # Storage 保存/加载/原子写入/错误测试
  test_integration.py           # 跨模块工作流测试
```

### 关键设计决策

- **基于异常驱动的错误处理**：`manager.py` 中的方法会抛出 `StudentNotFoundError`、`ValidationError` 等异常，而非返回 `False` 或 `None`。统一的 `StudentSystemError` 基类使得 `main.py` 中可以统一捕获所有错误。
- **`App` 类**（`main.py`）：所有处理函数通过闭包捕获 `self.manager` 和 `self.storage`，共享相同的 `(self) -> None` 签名，消除了旧版签名不匹配的问题。字典分派，无需特殊情况处理。
- **原子化写入**（`storage.py`）：数据先写入临时文件，然后通过 `os.replace` 原子性地替换——保存过程中的崩溃不会损坏现有数据。
- **输入健壮性**（`ui.py`）：每个输入函数都处理了 `KeyboardInterrupt` 和 `EOFError`，确保能够优雅退出。
- **`Student`** 数据类在 `__post_init__` 中进行验证——确保数据在创建时即完整可靠。
- **数据流**：`main.py` → `ui.py`（获取输入）→ `manager.py`（变更状态）→ `ui.py`（显示结果）。持久化方面：`main.py` → `manager.to_dict()` → `storage.save()`。

## 编码规范

### 文件头部

每个 `.py` 文件必须包含以下内容，按顺序排列：

1. **模块级 docstring**：描述模块职责，可选包含 `Examples:` 代码示例。
2. `from __future__ import annotations`：除 `__init__.py` 外所有模块均需放置在最顶部。
3. **4 段式导入顺序**（每段之间空一行）：
   - 标准库导入
   - 第三方库导入（本项目暂无）
   - 同包相对导入（`from .xxx import ...`）
   - `main.py` 使用绝对导入（`from student_system.xxx import ...`）

示例：

```python
"""学生数据持久化模块，负责 JSON 文件的原子化读写。

Examples:
    >>> from student_system.storage import Storage
    >>> storage = Storage("test_data.json")
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

from .exceptions import DataCorruptionError, StorageError
from .models import DEFAULT_DATA_FILE
```

### 命名规范

| 类别 | 规范 | 示例 |
|---|---|---|
| 变量/函数 | 蛇形命名法 `snake_case` | `student_count`, `add_student()` |
| 私有函数/方法 | 单下划线前缀 | `_dispatch()`, `_handle_input_cancellation()` |
| 私有属性 | 单下划线前缀 | `self._students`, `self._counter` |
| 类 | 大驼峰命名法 `PascalCase` | `StudentManager`, `StorageError` |
| 常量 | 全大写蛇形命名法 | `MIN_SCORE`, `DEFAULT_DATA_FILE` |
| 枚举成员 | 大驼峰命名法 | `MenuAction.ADD_STUDENT` |

### Docstring 风格

遵循 **Google 风格**，全部使用中文撰写：

- **函数/方法**：必须包含 `Args:`、`Returns:`、`Raises:` 小节（如适用）。
- **类**：包含简要说明和 `Attributes:` 小节。
- **模块**：描述模块职责，可选包含 `Examples:` 小节。

```python
def add_student(self, name: str) -> Student:
    """添加一名新学生，自动分配学号。

    Args:
        name: 学生姓名，不能为空。

    Returns:
        新创建的 Student 对象（包含分配的学号）。

    Raises:
        ValidationError: 姓名为空或仅含空白字符。
    """
```

### 类型注解

- 所有函数/方法的**参数和返回值**必须有类型注解。
- 所有实例属性必须在 `__init__` 中声明类型注解。
- 使用 `| None` 替代 `Optional[...]`（Python 3.10+ 联合类型语法）。
- 复杂字典结构使用 `TypedDict` 定义类型。
- 数据类使用 `@dataclass` + 字段类型注解，验证逻辑放在 `__post_init__` 中。

```python
self._students: dict[str, Student] = {}
self._counter: int = 0

def find_by_name(self, name: str) -> Student | None:
    ...
```

### 格式化

- **缩进**：4 空格，禁止使用 Tab。
- **行宽**：控制在 88–100 字符以内。长字符串使用隐式拼接（`f"..." f"..."`）或括号换行。
- **字符串引号**：统一使用双引号 `"`，仅在内部含双引号时使用单引号。
- **段落分隔**：模块内部使用分隔注释组织逻辑区块：

```python
# ----------------------------------------------------------
# 属性
# ----------------------------------------------------------

# ============================================================
# 内部辅助
# ============================================================
```

- **空行规则**：
  - 模块级 docstring 后：1 个空行
  - import 段之间：1 个空行
  - 顶级类和顶级函数之间：2 个空行
  - 类内方法之间：1 个空行
  - 方法内逻辑段之间：1 个空行

### 错误处理

- 所有自定义异常继承自统一的基类 `StudentSystemError`。
- 业务逻辑中**不返回 `False` 或 `None` 表示错误**，始终通过抛出异常报告失败。
- 使用 `raise ... from e` 保留异常链，不截断原始异常上下文。
- UI 层（`main.py`、`ui.py`）负责**集中捕获和友好提示**，Manager/Storage 层只负责抛出。

```python
# Manager 层：抛出异常
def delete_student(self, student_id: str) -> None:
    if student_id not in self._students:
        raise StudentNotFoundError(student_id)

# Storage 层：保留异常链
except (OSError, TypeError, ValueError) as e:
    raise StorageError(f"保存数据失败: {e}", filepath=self.filepath) from e

# UI 层：集中捕获
except StudentSystemError as e:
    ui.display_error(str(e))
```

### 模块公开接口

每个模块末尾显式定义 `__all__` 列表，精确控制公开接口：

```python
__all__ = [
    "MIN_SCORE",
    "MAX_SCORE",
    "DEFAULT_DATA_FILE",
    "Student",
    "MenuAction",
]
```

### 测试规范

- 框架：使用 `unittest` 标准库（不额外引入 pytest）。
- 文件命名：`test_<module>.py`，与 source 模块一一对应。
- 测试类命名：`Test<Component>` 或 `Test<MethodName>`。
- 测试方法命名：`test_<scenario>`，方法名清晰描述测试场景。
- 参数化测试：使用 `with self.subTest(...)`。
- 临时文件：使用 `tempfile.TemporaryDirectory()` 自动清理。
- 断言：使用 `self.assertEqual`、`self.assertRaises` 等 unittest 方法，不使用裸 `assert`。
- 每个测试文件末尾添加 `if __name__ == "__main__": unittest.main()`。

```python
def test_set_grade_negative_raises(self) -> None:
    with self.assertRaises(ValidationError):
        self.manager.set_grade("S001", "数学", -10)

def test_validate_score_boundary(self) -> None:
    for score in (0, 0.0, 50, 50.5, 100, 100.0):
        with self.subTest(score=score):
            self.assertEqual(validate_score(score), float(score))
```

## 常用指令

### 运行与调试

```bash
python main.py                                # 启动应用
```

### 测试

```bash
python -m unittest discover tests -v                        # 运行全部测试
python -m unittest discover tests -v -k "test_add"          # 按关键字筛选运行
python -m unittest tests.test_manager -v                    # 运行单个测试模块
python -m unittest tests.test_manager.TestAddStudent -v     # 运行单个测试类
python -m unittest tests.test_manager.TestAddStudent.test_add_student_basic -v  # 运行单个测试方法
```

### Git 工作流

```bash
git pull --rebase                           # 拉取最新代码并 rebase
git add -A && git commit -m "<message>"     # 暂存全部变更并提交
git push                                    # 推送到远程
git log --oneline -10                       # 查看最近 10 条提交
git diff                                    # 查看未暂存的变更
git diff --staged                           # 查看已暂存的变更
```
