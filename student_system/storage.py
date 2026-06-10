"""数据持久化层 — JSON 文件读写与原子写入。

本模块为系统提供可靠的数据持久化能力，特性包括：
- 使用临时文件 + 原子重命名保证写入安全（避免写入中断导致数据损坏）
- 加载时对数据格式进行验证
- 统一的 StorageError 异常体系便于上层处理

Examples:
    >>> from student_system.storage import Storage
    >>> storage = Storage("test_data.json")
    >>> data = {"1": {"name": "张三", "grades": {"语文": 90}}}
    >>> storage.save(data)
    >>> loaded, counter = storage.load()
    >>> loaded["1"]["name"]
    '张三'
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

from .exceptions import DataCorruptionError, StorageError
from .models import DEFAULT_DATA_FILE


class Storage:
    """学生数据的 JSON 文件持久化管理器。

    提供带原子写入保护的保存和加载操作。
    所有公有方法在出错时抛出 :exc:`StorageError` 或其子类异常。

    Attributes:
        filepath: 当前使用的 JSON 文件路径。
    """

    def __init__(self, filepath: str = DEFAULT_DATA_FILE) -> None:
        """初始化持久化管理器。

        Args:
            filepath: JSON 数据文件的路径。
                      默认为当前目录下的 ``students_data.json``。
        """
        self.filepath = filepath

    # --- 文件状态查询 ---

    def file_exists(self) -> bool:
        """检查数据文件是否已存在。

        Returns:
            True 如果文件存在且可访问，False 否则。
        """
        return os.path.exists(self.filepath)

    @property
    def file_size(self) -> int | None:
        """获取数据文件的字节大小（不存在时返回 None）。"""
        if not self.file_exists():
            return None
        try:
            return os.path.getsize(self.filepath)
        except OSError:
            return None

    # --- 保存操作 ---

    def save(self, students: dict[str, dict[str, Any]]) -> None:
        """将学生数据以原子方式保存到 JSON 文件。

        原子写入流程：
        1. 先写入同目录下的临时文件
        2. 写入成功后，通过 os.replace 原子替换目标文件
        3. 如果任意步骤失败，临时文件被清理，原文件不受影响

        Args:
            students: 学号到学生信息字典的映射。
                      可通过 :meth:`StudentManager.to_dict()` 获取。

        Raises:
            StorageError: 写入或重命名过程中发生 I/O 错误。
        """
        directory = os.path.dirname(self.filepath) or "."
        try:
            # 创建临时文件，与目标文件同目录（确保同文件系统，原子重命名有效）
            fd, tmp_path = tempfile.mkstemp(
                dir=directory,
                prefix=".students_",
                suffix=".tmp",
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(
                        students,
                        f,
                        ensure_ascii=False,
                        indent=2,
                        default=str,
                    )
                # 原子替换：在 Windows 和 POSIX 上均可安全工作
                os.replace(tmp_path, self.filepath)
            except Exception:
                # 写入失败，清理临时文件
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise
        except (OSError, TypeError, ValueError) as e:
            raise StorageError(
                f"保存数据失败: {e}",
                filepath=self.filepath,
            ) from e

    # --- 加载操作 ---

    def load(self) -> tuple[dict[str, dict[str, Any]], int]:
        """从 JSON 文件加载学生数据。

        除读取和解析 JSON 外，还会验证数据结构的基本完整性。

        Returns:
            一个元组 ``(data, counter)``：
            - ``data`` — 学号到学生信息字典的映射
            - ``counter`` — 从学号中计算出的最大计数器值，
              便于 :meth:`StudentManager.load_data` 恢复学号递增状态

        Raises:
            StorageError: 文件不存在或无法读取。
            DataCorruptionError: JSON 解析成功但数据格式不符合预期。
        """
        if not self.file_exists():
            raise StorageError(
                f"数据文件不存在: {self.filepath}",
                filepath=self.filepath,
            )

        # 读取并解析 JSON
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise DataCorruptionError(
                self.filepath,
                f"JSON 解析失败 (行 {e.lineno}, 列 {e.colno}): {e.msg}",
            ) from e
        except OSError as e:
            raise StorageError(
                f"读取文件失败: {e}",
                filepath=self.filepath,
            ) from e

        # 验证数据结构
        if not isinstance(data, dict):
            raise DataCorruptionError(
                self.filepath,
                "顶层数据必须是 JSON 对象（字典）",
            )

        for sid, info in data.items():
            if not isinstance(info, dict):
                raise DataCorruptionError(
                    self.filepath,
                    f"学生 {sid} 的数据必须是字典，实际为 {type(info).__name__}",
                )
            if "name" not in info:
                raise DataCorruptionError(
                    self.filepath,
                    f"学生 {sid} 的数据缺少 'name' 字段",
                )

        # 计算最大学号
        max_id = 0
        for sid in data:
            if isinstance(sid, str) and sid.isdigit():
                max_id = max(max_id, int(sid))

        return data, max_id


__all__ = ["Storage"]
