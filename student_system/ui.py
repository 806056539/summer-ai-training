"""用户界面层 — 所有终端 I/O 的集中管理。

本模块是系统中**唯一**调用 :func:`print` 和 :func:`input` 的地方。
提供三类函数：
1. **菜单显示** — 渲染主菜单和获取用户选择
2. **输入验证** — 带循环重试的健壮输入函数
3. **数据展示** — 格式化打印学生列表、统计和排名

所有输入函数在收到 EOF (Ctrl+D) 或中断 (Ctrl+C) 时会做适当处理。

Examples:
    >>> from student_system import ui
    >>> ui.show_menu()
    <prints the main menu>
    >>> name = ui.prompt_non_empty("姓名: ")
"""

from __future__ import annotations

import sys
from typing import Sequence

from .models import MAX_SCORE, MIN_SCORE, MenuAction


# ============================================================
# 内部辅助
# ============================================================

def _handle_input_cancellation(prompt: str) -> None:
    """处理用户取消输入（EOF 或中断）的默认行为。

    Args:
        prompt: 引发取消时的提示文本。
    """
    print()  # 换行
    print("输入已取消，返回主菜单。")


# ============================================================
# 菜单显示
# ============================================================

def show_menu() -> None:
    """打印主菜单，列出全部 9 个操作项及其数字键。

    菜单内容由 :class:`~.models.MenuAction` 枚举动态生成，
    因此添加新的菜单项时无需修改此函数。
    """
    print()
    print("========== 学生成绩管理系统 ==========")
    for action in MenuAction:
        print(f"  {action.key}. {action.label}")
    print("=====================================")


def get_choice() -> str:
    """从用户获取菜单选择。

    不做有效性验证（由调用方通过 DISPATCH 字典处理），
    仅去除首尾空白。

    Returns:
        用户输入的字符串（可能为空或无效）。
    """
    try:
        return input("请选择操作 (1-9): ").strip()
    except (EOFError, KeyboardInterrupt):
        return "9"  # 返回退出键


# ============================================================
# 输入验证辅助函数
# ============================================================

def prompt_non_empty(prompt: str) -> str:
    """持续提示直到用户输入非空字符串。

    Args:
        prompt: 提示文本（不含换行符）。

    Returns:
        用户输入的去除首尾空白的非空字符串。

    按 Ctrl+C 或 Ctrl+D 将退出程序。
    """
    while True:
        try:
            value = input(prompt).strip()
            if value:
                return value
            print("输入不能为空，请重新输入！")
        except KeyboardInterrupt:
            print("\n\n操作已取消，退出系统。")
            sys.exit(0)
        except EOFError:
            print("\n\n检测到输入结束，退出系统。")
            sys.exit(0)


def prompt_yes_no(prompt: str) -> bool:
    """提示用户输入 yes/no，返回对应的布尔值。

    支持的输入格式：y / yes（返回 True），n / no（返回 False），大小写不敏感。

    Args:
        prompt: 提示文本。

    Returns:
        True 表示确认，False 表示否定。

    按 Ctrl+C 或 Ctrl+D 默认视为否定（安全默认）。
    """
    while True:
        try:
            choice = input(prompt).strip().lower()
            if choice in ("y", "yes"):
                return True
            if choice in ("n", "no"):
                return False
            print("请输入 y 或 n！")
        except KeyboardInterrupt:
            print("\n操作已取消。")
            return False
        except EOFError:
            print("\n输入已取消。")
            return False


def prompt_score(prompt: str = "请输入成绩(0-100): ") -> float:
    """持续提示直到用户输入有效的成绩值。

    Args:
        prompt: 提示文本。

    Returns:
        有效的浮点数成绩，范围在 [MIN_SCORE, MAX_SCORE] 之间。

    按 Ctrl+C 或 Ctrl+D 将推出程序。
    """
    while True:
        try:
            raw = input(prompt).strip()
            score = float(raw)
            if MIN_SCORE <= score <= MAX_SCORE:
                return score
            print(f"成绩范围应在 {int(MIN_SCORE)}-{int(MAX_SCORE)} 之间！")
        except ValueError:
            print("成绩必须是数字，请重新输入！")
        except KeyboardInterrupt:
            print("\n\n操作已取消，退出系统。")
            sys.exit(0)
        except EOFError:
            print("\n\n检测到输入结束，退出系统。")
            sys.exit(0)


def prompt_student_id(prompt: str = "请输入学生学号: ") -> str:
    """提示输入学号，确保非空。

    Args:
        prompt: 提示文本。

    Returns:
        非空学号字符串。
    """
    return prompt_non_empty(prompt)


def prompt_course_name(prompt: str = "请输入课程名称: ") -> str:
    """提示输入课程名称，确保非空。

    Args:
        prompt: 提示文本。

    Returns:
        非空课程名称字符串。
    """
    return prompt_non_empty(prompt)


# ============================================================
# 数据展示函数
# ============================================================

def display_message(msg: str) -> None:
    """打印一条通用消息。

    Args:
        msg: 要显示的消息文本。
    """
    print(msg)


def display_success(msg: str) -> None:
    """打印一条成功消息（带前缀）。

    Args:
        msg: 成功描述文本。
    """
    print(f"[成功] {msg}")


def display_error(msg: str) -> None:
    """打印一条错误消息（带前缀）。

    Args:
        msg: 错误描述文本。
    """
    print(f"[错误] {msg}")


def display_warning(msg: str) -> None:
    """打印一条警告消息（带前缀）。

    Args:
        msg: 警告描述文本。
    """
    print(f"[警告] {msg}")


def display_student_list(students: Sequence) -> None:
    """格式化打印所有学生的成绩表。

    包含学号、姓名以及每门课程的成绩。
    无成绩的学生会显示"暂无成绩"标记。

    Args:
        students: Student 对象的可迭代序列（支持 StudentManager.get_all_students() 的返回值）。
    """
    if not students:
        print("暂无学生数据。")
        return

    print()
    print("================ 所有学生成绩表 ================")
    for student in students:
        print(f"学号: {student.student_id}  |  姓名: {student.name}")
        if not student.grades:
            print("  (暂无成绩)")
        else:
            for course, score in student.grades.items():
                print(f"  {course}: {score}")
        print("-" * 40)


def display_stats(stats: list[dict]) -> None:
    """格式化打印学生统计信息表。

    展示每位学生的总分、平均分和课程数量。
    使用固定列宽对齐，便于阅读。

    Args:
        stats: StudentManager.get_stats() 返回的统计字典列表。
    """
    if not stats:
        print("暂无学生数据。")
        return

    print()
    print("================ 学生统计信息 ================")
    header = f"{'学号':<8}{'姓名':<12}{'总分':<10}{'平均分':<10}{'课程数':<8}"
    print(header)
    print("-" * len(header))
    for entry in stats:
        print(
            f"{entry['student_id']:<8}"
            f"{entry['name']:<12}"
            f"{entry['total']:<10.2f}"
            f"{entry['avg']:<10.2f}"
            f"{entry['course_count']:<8}"
        )


def display_ranking(ranking: list[dict]) -> None:
    """格式化打印总分排名表。

    按总分从高到低显示排名、学号、姓名和各项成绩指标。

    Args:
        ranking: StudentManager.get_ranking() 返回的排名字典列表。
    """
    if not ranking:
        print("暂无学生数据。")
        return

    print()
    print("================ 总分排名 ================")
    header = f"{'排名':<8}{'学号':<8}{'姓名':<12}{'总分':<10}{'平均分':<10}"
    print(header)
    print("-" * len(header))
    for rank, entry in enumerate(ranking, start=1):
        print(
            f"{rank:<8}"
            f"{entry['student_id']:<8}"
            f"{entry['name']:<12}"
            f"{entry['total']:<10.2f}"
            f"{entry['avg']:<10.2f}"
        )


__all__ = [
    "show_menu",
    "get_choice",
    "prompt_non_empty",
    "prompt_yes_no",
    "prompt_score",
    "prompt_student_id",
    "prompt_course_name",
    "display_message",
    "display_success",
    "display_error",
    "display_warning",
    "display_student_list",
    "display_stats",
    "display_ranking",
]
