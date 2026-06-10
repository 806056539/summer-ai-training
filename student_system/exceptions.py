"""自定义异常类层次结构。

提供该系统所有模块使用的统一异常类型，使错误处理更加精确和一致。

Examples:
    >>> from student_system.exceptions import ValidationError
    >>> raise ValidationError("学生姓名不能为空")
    Traceback (most recent call last):
        ...
    student_system.exceptions.ValidationError: 学生姓名不能为空

    >>> try:
    ...     raise StudentNotFoundError("1")
    ... except StudentSystemError as e:
    ...     print(f"捕获到系统错误: {e}")
    捕获到系统错误: 未找到学号为 '1' 的学生
"""

from __future__ import annotations


class StudentSystemError(Exception):
    """所有学生管理系统异常的基类。

    用于捕获所有由本系统产生的异常，便于统一处理。
    """


class ValidationError(StudentSystemError):
    """输入数据不符合约束时抛出。

    用于参数验证失败、数据格式错误等场景。

    Attributes:
        field: 可选，指出哪个字段验证失败。
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class StudentNotFoundError(StudentSystemError):
    """请求的学生不存在时抛出。

    Attributes:
        student_id: 被查找但未找到的学号。
    """

    def __init__(self, student_id: str) -> None:
        self.student_id = student_id
        super().__init__(f"未找到学号为 '{student_id}' 的学生")


class DuplicateStudentError(StudentSystemError):
    """尝试添加重复学生时抛出。

    Attributes:
        name: 重复的学生姓名。
        existing_id: 已存在学生的学号。
    """

    def __init__(self, name: str, existing_id: str) -> None:
        self.name = name
        self.existing_id = existing_id
        super().__init__(
            f"已存在学生 '{name}' (学号 {existing_id})"
        )


class StorageError(StudentSystemError):
    """数据持久化操作失败时抛出。

    包括文件读写错误、JSON 解析错误、文件权限问题等。

    Attributes:
        filepath: 操作涉及的文件路径。
    """

    def __init__(self, message: str, filepath: str | None = None) -> None:
        super().__init__(message)
        self.filepath = filepath


class DataCorruptionError(StorageError):
    """加载的数据格式不正确或损坏时抛出。"""

    def __init__(self, filepath: str, detail: str = "") -> None:
        self.detail = detail
        msg = f"数据文件 '{filepath}' 格式异常"
        if detail:
            msg += f": {detail}"
        super().__init__(msg, filepath=filepath)


__all__ = [
    "StudentSystemError",
    "ValidationError",
    "StudentNotFoundError",
    "DuplicateStudentError",
    "StorageError",
    "DataCorruptionError",
]
