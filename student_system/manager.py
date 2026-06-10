"""学生管理业务逻辑层。

StudentManager 是系统的核心，封装所有学生数据的状态管理与业务操作。
本模块严格遵循"纯逻辑"原则：所有方法均不涉及 print()、input() 或文件 I/O，
错误通过异常而非返回值无声传达（与旧版返回 bool 不同）。

Examples:
    >>> from student_system.manager import StudentManager
    >>> mgr = StudentManager()
    >>> student = mgr.add_student("张三")
    >>> mgr.set_grade(student.student_id, "数学", 95.0)
    >>> stats = mgr.get_stats()
    >>> stats[0]["avg"]
    95.0
"""

from __future__ import annotations

from typing import Sequence

from .exceptions import (
    DataCorruptionError,
    DuplicateStudentError,
    StudentNotFoundError,
    ValidationError,
)
from .models import (
    RankingEntry,
    Student,
    StudentStats,
    validate_name,
    validate_score,
)


class StudentManager:
    """学生数据的核心管理器。

    维护学生字典和自动递增学号计数器。
    所有变更操作通过异常报告失败，而非返回 bool 或静默忽略。

    Attributes:
        student_count: 当前系统中的学生总数（只读属性）。
        counter: 当前学号计数器的值，即已分配的最大学号（只读属性）。
    """

    def __init__(self) -> None:
        """初始化一个空的管理器，无任何学生数据。"""
        self._students: dict[str, Student] = {}
        self._counter: int = 0

    # ----------------------------------------------------------
    # 属性
    # ----------------------------------------------------------

    @property
    def student_count(self) -> int:
        """当前注册的学生总数。"""
        return len(self._students)

    @property
    def counter(self) -> int:
        """学号计数器——下次添加学生时将使用 counter + 1。"""
        return self._counter

    # ----------------------------------------------------------
    # 增删操作
    # ----------------------------------------------------------

    def add_student(self, name: str) -> Student:
        """添加一名新学生，自动分配学号。

        Args:
            name: 学生姓名，不能为空。

        Returns:
            新创建的 Student 对象（包含分配的学号）。

        Raises:
            ValidationError: 姓名为空或仅含空白字符。
        """
        name = validate_name(name)
        self._counter += 1
        student_id = str(self._counter)
        student = Student(student_id=student_id, name=name)
        self._students[student_id] = student
        return student

    def delete_student(self, student_id: str) -> None:
        """删除指定学号的学生。

        Args:
            student_id: 要删除的学生学号。

        Raises:
            StudentNotFoundError: 指定学号的学生不存在。
        """
        if student_id not in self._students:
            raise StudentNotFoundError(student_id)
        del self._students[student_id]

    # ----------------------------------------------------------
    # 查询操作
    # ----------------------------------------------------------

    def get_student(self, student_id: str) -> Student:
        """按学号精确查找学生。

        Args:
            student_id: 学生学号。

        Returns:
            匹配的 Student 对象。

        Raises:
            StudentNotFoundError: 指定学号的学生不存在。
        """
        student = self._students.get(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)
        return student

    def find_by_name(self, name: str) -> Student | None:
        """按姓名查找学生（返回第一个精确匹配）。

        Args:
            name: 要查找的学生姓名。

        Returns:
            第一个姓名匹配的 Student 对象，若无匹配则返回 None。
        """
        name = name.strip()
        for student in self._students.values():
            if student.name == name:
                return student
        return None

    def find_by_name_strict(self, name: str) -> Student:
        """按姓名查找学生，若无匹配则抛出异常。

        Args:
            name: 要查找的学生姓名。

        Returns:
            匹配的 Student 对象。

        Raises:
            StudentNotFoundError: 没有学生具有此姓名。
        """
        name = name.strip()
        for student in self._students.values():
            if student.name == name:
                return student
        raise StudentNotFoundError(f"(姓名: '{name}')")

    def get_all_students(self) -> list[Student]:
        """返回所有学生列表，按学号数字升序排列。

        Returns:
            Student 对象列表，可能为空。
        """
        return sorted(self._students.values(), key=lambda s: int(s.student_id))

    # ----------------------------------------------------------
    # 成绩操作
    # ----------------------------------------------------------

    def set_grade(self, student_id: str, course: str, score: float) -> None:
        """为指定学生设置或更新某门课程的成绩。

        Args:
            student_id: 学生学号。
            course: 课程名称，不能为空。
            score: 分数值，必须在 [MIN_SCORE, MAX_SCORE] 范围内。

        Raises:
            StudentNotFoundError: 指定学号的学生不存在。
            ValidationError: 课程名为空或成绩值无效。
        """
        student = self.get_student(student_id)  # 可能抛出 StudentNotFoundError
        student.set_grade(course, score)

    def get_grades(self, student_id: str) -> dict[str, float]:
        """获取指定学生的所有成绩。

        Args:
            student_id: 学生学号。

        Returns:
            课程名到分数的映射字典，可能为空。

        Raises:
            StudentNotFoundError: 指定学号的学生不存在。
        """
        return self.get_student(student_id).grades

    # ----------------------------------------------------------
    # 统计与排名
    # ----------------------------------------------------------

    def get_stats(self) -> list[StudentStats]:
        """计算所有学生的统计信息。

        为每位学生计算总分、平均分和课程数量。
        结果未排序，调用方可自行排序。

        Returns:
            StudentStats 字典列表，可能为空。
        """
        return [
            StudentStats(
                student_id=s.student_id,
                name=s.name,
                total=s.total_score,
                avg=s.average_score,
                course_count=s.course_count,
            )
            for s in self._students.values()
        ]

    def get_ranking(self) -> list[RankingEntry]:
        """获取按总分降序排列的学生排名。

        Returns:
            从高到低排序的 RankingEntry 字典列表。
        """
        stats = self.get_stats()
        stats.sort(key=lambda x: x["total"], reverse=True)
        return stats

    def get_student_rank(self, student_id: str) -> int:
        """获取指定学生的排名（按总分降序）。

        Args:
            student_id: 学生学号。

        Returns:
            排名（从 1 开始）。

        Raises:
            StudentNotFoundError: 指定学号的学生不存在。
        """
        self.get_student(student_id)  # 验证存在
        ranking = self.get_ranking()
        for rank, entry in enumerate(ranking, start=1):
            if entry["student_id"] == student_id:
                return rank
        # 理论上不会到这里，但做安全返回
        raise StudentNotFoundError(student_id)

    # ----------------------------------------------------------
    # 批量数据操作
    # ----------------------------------------------------------

    def load_data(self, data: dict[str, dict], counter: int) -> None:
        """从外部数据批量加载学生数据。

        此方法会**完全替换**当前管理器中的所有数据。
        通常由 storage 模块在加载文件后调用。

        Args:
            data: 学号到学生信息字典的映射。
                  每个学生信息应包含 ``name`` 和可选的 ``grades`` 键。
            counter: 对应数据中最大学号的计数器值。

        Raises:
            DataCorruptionError: 数据格式不正确或包含无效的学生信息。
        """
        if not isinstance(data, dict):
            raise DataCorruptionError("(内存)", "数据必须是字典")

        students: dict[str, Student] = {}
        for sid, info in data.items():
            if not isinstance(info, dict):
                raise DataCorruptionError(
                    "(内存)",
                    f"学生 {sid} 的数据必须是字典",
                )
            try:
                students[sid] = Student.from_dict(sid, info)
            except ValidationError as e:
                raise DataCorruptionError("(内存)", str(e)) from e

        self._students = students
        self._counter = counter

    def to_dict(self) -> dict[str, dict]:
        """将所有学生数据导出为可序列化的字典。

        Returns:
            学号到学生信息字典的映射，可直接 JSON 序列化。
        """
        return {sid: s.to_dict() for sid, s in self._students.items()}


__all__ = ["StudentManager"]
