---
name: log-extract
description: 为项目添加 Python logging 日志模块，并从 JSON 数据文件（students_data.json）中提取操作时间线。当你需要添加日志、查看操作记录、提取操作时间线、分析数据变更历史、或提到"日志""log""时间线""操作记录"时使用此技能。
---

# 日志自动提取技能

两步走：首先为项目添加完整的 logging 日志基础设施，然后从 JSON 数据文件中提取操作时间线。

## 第一步：添加日志模块

### 1.1 创建日志配置模块

在 `student_system/` 下创建 `logger.py`，包含：

- 使用 Python 标准库 `logging`
- 同时输出到**文件**（`app.log`）和**控制台**（stdout）
- 日志格式：`[YYYY-MM-DD HH:MM:SS] [LEVEL] [模块名] 消息内容`
- 文件日志级别：`DEBUG`（记录所有操作细节）
- 控制台日志级别：`INFO`（仅显示关键信息）
- 自动轮转：使用 `RotatingFileHandler`，单文件最大 1MB，保留 3 个备份

```python
"""日志配置模块，提供统一的日志记录器。

Examples:
    >>> from student_system.logger import get_logger
    >>> logger = get_logger(__name__)
    >>> logger.info("应用启动")
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_FILE: str = "app.log"
MAX_BYTES: int = 1_048_576  # 1MB
BACKUP_COUNT: int = 3


def setup_logging(
    log_file: str = LOG_FILE,
    file_level: int = logging.DEBUG,
    console_level: int = logging.INFO,
) -> None:
    """初始化全局日志配置。

    Args:
        log_file: 日志文件路径。
        file_level: 文件日志级别。
        console_level: 控制台日志级别。
    """
    ...


def get_logger(name: str) -> logging.Logger:
    """获取指定模块的日志记录器。

    Args:
        name: 模块名称（通常传入 __name__）。

    Returns:
        配置好的 Logger 实例。
    """
    ...


__all__ = ["setup_logging", "get_logger", "LOG_FILE"]
```

### 1.2 在各模块中添加日志调用

按照以下规则为各模块添加日志：

**`main.py`**：
- 应用启动时：`logger.info("学生成绩管理系统启动")`
- 加载数据成功：`logger.info(f"从 {filepath} 加载数据，共 {count} 名学生")`
- 加载数据失败：`logger.warning(f"未找到数据文件 {filepath}，将创建新文件")`
- 退出时：`logger.info("系统正常退出")`
- 捕获异常时：`logger.error(f"操作失败: {e}", exc_info=True)`

**`manager.py`**：
- 添加学生：`logger.info(f"添加学生: {name} -> {student_id}")`
- 删除学生：`logger.info(f"删除学生: {student_id} ({name})")`
- 设置成绩：`logger.info(f"设置成绩: {student_id} {course} = {score}")`
- 更新学生：`logger.info(f"更新学生信息: {student_id}")`
- 参数校验失败：`logger.warning(f"校验失败: {msg}")`

**`storage.py`**：
- 保存数据：`logger.debug(f"保存数据到 {filepath}，共 {count} 条记录")`
- 加载数据：`logger.debug(f"从 {filepath} 加载数据")`
- 数据损坏：`logger.error(f"数据文件损坏: {detail}")`
- 原子写入：`logger.debug(f"原子写入完成: {filepath}")`

### 1.3 日志文件与测试

- 日志文件 `app.log` 加入 `.gitignore`
- 保持所有 124 个测试通过
- 测试中可使用 `self.assertLogs()` 验证日志输出

## 第二步：提取操作时间线

### 2.1 从日志文件提取

解析 `app.log`，提取所有带时间戳的操作记录，输出结构化时间线：

```markdown
# 操作时间线

**数据源**：app.log
**提取时间**：YYYY-MM-DD HH:MM:SS
**操作总数**：N

## 时间线

| 时间 | 级别 | 模块 | 操作 | 详情 |
|------|------|------|------|------|
| 2026-06-13 10:00:01 | INFO | main | 系统启动 | — |
| 2026-06-13 10:00:02 | INFO | storage | 加载数据 | 共 5 名学生 |
| 2026-06-13 10:01:15 | INFO | manager | 添加学生 | 张三 -> S001 |
| 2026-06-13 10:02:30 | INFO | manager | 设置成绩 | S001 数学 = 95.0 |
| ... | ... | ... | ... | ... |

## 操作统计

- 添加学生: N 次
- 删除学生: N 次
- 设置成绩: N 次
- 更新信息: N 次
```

### 2.2 从 JSON 数据文件提取快照信息

解析 `students_data.json`，输出当前数据状态：

```markdown
# 数据快照

**数据源**：students_data.json
**提取时间**：YYYY-MM-DD HH:MM:SS

## 学生列表

| 学号 | 姓名 | 课程数 | 总分 | 平均分 |
|------|------|--------|------|--------|
| S001 | 张三 | 3 | 270.0 | 90.0 |
| ... | ... | ... | ... | ... |

## 统计

- 学生总数: N
- 课程总数: N
- 全班总平均分: XX.X
- 最高分学生: 姓名 (学号) — XX.X
- 最低分学生: 姓名 (学号) — XX.X
```

### 2.3 整合报告

将日志时间线和数据快照合并为一份完整的操作审计报告。

## 执行流程

当用户触发此技能时：

1. **检查** `student_system/logger.py` 是否存在
   - 若不存在，按第一步创建日志模块
   - 若已存在，跳过创建步骤
2. **检查** 各模块是否已有日志调用
   - 若没有，按 1.2 节添加日志调用
   - 若有但不足，补充缺失的日志点
3. **运行测试** 确保所有 124 个测试仍通过
4. **提取时间线** — 按第二步生成报告
   - 若 `app.log` 存在，解析并生成操作时间线
   - 若 `students_data.json` 存在，生成数据快照
   - 合并输出整合报告
