"""数据模型、常量与类型定义。

本模块定义了学生成绩管理系统的核心数据结构，包括：
- 成绩范围常量
- 菜单动作枚举
- Student 数据类（带验证）
- 统计与排名结果的类型定义

Examples:
    >>> from student_system.models import Student, MenuAction
    >>> s = Student(student_id="1", name="张三")
    >>> s.grades["数学"] = 95.0
    >>> s.total_score
    95.0
    >>> action = MenuAction.from_key("1")
    >>> action.label
    '添加学生'
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypedDict

from .exceptions import ValidationError

# ============================================================
# 常量
# ============================================================

MIN_SCORE: float = 0.0
"""有效成绩的最低值"""

MAX_SCORE: float = 100.0
"""有效成绩的最高值"""

DEFAULT_DATA_FILE: str = "students_data.json"
"""默认的 JSON 数据持久化文件名"""

VALID_YES_NO: tuple[str, ...] = ("y", "yes", "n", "no")
"""确认提示支持的有效输入"""


def validate_score(score: float) -> float:
    """验证成绩是否在有效范围内。

    Args:
        score: 待验证的成绩值。

    Returns:
        验证通过的成绩值（不变）。

    Raises:
        ValidationError: 成绩不在 [MIN_SCORE, MAX_SCORE] 范围内。
    """
    if not isinstance(score, (int, float)):
        raise ValidationError(
            f"成绩必须是数字，但收到了 {type(score).__name__}",
            field="score",
        )
    # NaN 的比较永远返回 False，需要单独检测
    import math
    if math.isnan(score) or score < MIN_SCORE or score > MAX_SCORE:
        raise ValidationError(
            f"成绩应在 {int(MIN_SCORE)}-{int(MAX_SCORE)} 之间，但收到了 {score}",
            field="score",
        )
    return score


def validate_name(name: str) -> str:
    """验证姓名是否有效（非空且仅含允许字符）。

    Args:
        name: 待验证的姓名。

    Returns:
        去除首尾空白后的姓名。

    Raises:
        ValidationError: 姓名为空。
    """
    name = name.strip()
    if not name:
        raise ValidationError("姓名不能为空", field="name")
    return name


# ============================================================
# 菜单动作枚举
# ============================================================

class MenuAction(Enum):
    """主菜单的 9 个操作项。

    每个枚举成员包含一个 key（菜单数字键）和一个 label（中文显示名）。
    通过 :meth:`from_key` 可将用户输入的数字字符串映射为对应的枚举成员。

    Examples:
        >>> action = MenuAction.from_key("3")
        >>> (action.key, action.label)
        ('3', '添加/修改成绩')
    """

    ADD_STUDENT = ("1", "添加学生")
    DELETE_STUDENT = ("2", "删除学生")
    ADD_GRADE = ("3", "添加/修改成绩")
    VIEW_GRADES = ("4", "查看所有学生成绩")
    VIEW_STATS = ("5", "查看学生统计（平均分/总分/排名）")
    VIEW_RANKING = ("6", "按总分排名显示")
    SAVE_DATA = ("7", "保存数据到文件")
    LOAD_DATA = ("8", "从文件加载数据")
    EXIT = ("9", "退出系统")

    def __init__(self, key: str, label: str) -> None:
        self.key = key
        self.label = label

    @classmethod
    def from_key(cls, key: str) -> MenuAction | None:
        """根据菜单数字键查找对应的枚举成员。

        Args:
            key: 用户输入的数字字符串，例如 ``"1"``。

        Returns:
            匹配的 MenuAction，如果 key 无效则返回 None。
        """
        for action in cls:
            if action.key == key:
                return action
        return None


# ============================================================
# 统计和排名类型定义
# ============================================================

class StudentStats(TypedDict):
    """单个学生的统计信息。

    Attributes:
        student_id: 学号。
        name: 学生姓名。
        total: 所有课程总分。
        avg: 所有课程平均分。
        course_count: 已录入成绩的课程数量。
    """

    student_id: str
    name: str
    total: float
    avg: float
    course_count: int


class RankingEntry(TypedDict):
    """排名中的一条记录，结构与 StudentStats 相同。"""

    student_id: str
    name: str
    total: float
    avg: float
    course_count: int


# ============================================================
# 学生数据类
# ============================================================

@dataclass
class Student:
    """学生数据模型，包含学号、姓名和各科成绩。

    成绩以课程名称为键、分数为值的字典存储。
    通过属性可便捷获取总分、平均分和课程数。

    Attributes:
        student_id: 自动递增分配的学号（字符串形式）。
        name: 学生姓名。
        grades: 课程名到分数的映射字典。

    Examples:
        >>> s = Student("1", "李四")
        >>> s.set_grade("英语", 88.5)
        >>> s.total_score
        88.5
        >>> s.average_score
        88.5
        >>> s.to_dict()
        {'name': '李四', 'grades': {'英语': 88.5}}
    """

    student_id: str
    name: str
    grades: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """初始化后验证数据完整性。"""
        # 验证 name（跳过 from_dict 中可能传入的已清理数据）
        if not self.name or not self.name.strip():
            raise ValidationError("学生姓名不能为空", field="name")
        self.name = self.name.strip()

        # 验证所有已有成绩
        for course, score in self.grades.items():
            if not course.strip():
                raise ValidationError("课程名称不能为空", field="grades")
            validate_score(score)

    # --- 计算属性 ---

    @property
    def total_score(self) -> float:
        """所有课程的总分。无成绩时返回 0.0。"""
        return sum(self.grades.values()) if self.grades else 0.0

    @property
    def average_score(self) -> float:
        """所有课程的平均分。无成绩时返回 0.0。"""
        if not self.grades:
            return 0.0
        return self.total_score / len(self.grades)

    @property
    def course_count(self) -> int:
        """已录入成绩的课程数量。"""
        return len(self.grades)

    # --- 成绩操作 ---

    def set_grade(self, course: str, score: float) -> None:
        """设置或更新一门课程的成绩。

        Args:
            course: 课程名称，不能为空。
            score: 分数值，必须在 [MIN_SCORE, MAX_SCORE] 范围内。

        Raises:
            ValidationError: 课程名为空或成绩无效。
        """
        course = course.strip()
        if not course:
            raise ValidationError("课程名称不能为空", field="course")
        validate_score(score)
        self.grades[course] = score

    def remove_grade(self, course: str) -> bool:
        """删除一门课程的成绩记录。

        Args:
            course: 要删除的课程名称。

        Returns:
            True 如果该课程成绩存在并被删除，False 如果该课程不存在。
        """
        if course in self.grades:
            del self.grades[course]
            return True
        return False

    # --- 序列化 ---

    def to_dict(self) -> dict[str, Any]:
        """将学生对象序列化为可用于 JSON 持久化的字典。

        Returns:
            包含 name 和 grades 的字典。注意学号不在其中，由外部管理。

        Examples:
            >>> s = Student("1", "王五")
            >>> s.set_grade("物理", 92)
            >>> s.to_dict()
            {'name': '王五', 'grades': {'物理': 92.0}}
        """
        return {
            "name": self.name,
            "grades": dict(self.grades),
        }

    @classmethod
    def from_dict(cls, student_id: str, data: dict[str, Any]) -> Student:
        """从字典反序列化创建 Student 实例。

        Args:
            student_id: 该学生的学号。
            data: 包含 ``name`` 和可选的 ``grades`` 键的字典。

        Returns:
            新创建的 Student 对象。

        Raises:
            ValidationError: data 中缺少必要的 name 字段或格式错误。
        """
        if "name" not in data:
            raise ValidationError(
                f"学生 {student_id} 的数据缺少 'name' 字段",
                field="name",
            )
        if not isinstance(data.get("grades", {}), dict):
            raise ValidationError(
                f"学生 {student_id} 的 'grades' 必须是字典",
                field="grades",
            )
        return cls(
            student_id=student_id,
            name=data["name"],
            grades=data.get("grades", {}),
        )

    def __repr__(self) -> str:
        return (
            f"Student(student_id={self.student_id!r}, "
            f"name={self.name!r}, "
            f"course_count={self.course_count})"
        )


__all__ = [
    "MIN_SCORE",
    "MAX_SCORE",
    "DEFAULT_DATA_FILE",
    "VALID_YES_NO",
    "validate_score",
    "validate_name",
    "MenuAction",
    "StudentStats",
    "RankingEntry",
    "Student",
]
