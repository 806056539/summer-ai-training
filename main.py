"""学生成绩管理系统 — 应用程序入口。

本文件将各层组件（UI、业务逻辑、持久化）组装为可运行的应用。
使用 :class:`App` 类封装应用程序，实现：
- 统一的处理函数签名（字典分发，消除 if/elif 长链）
- 优雅的异常处理和用户反馈
- 程序启动时自动检测并加载已有数据

Usage:
    python main.py
"""

from __future__ import annotations

import sys
from typing import Callable

from student_system.exceptions import (
    DataCorruptionError,
    StudentNotFoundError,
    StudentSystemError,
    StorageError,
    ValidationError,
)
from student_system.manager import StudentManager
from student_system.models import MenuAction
from student_system.storage import Storage
from student_system import ui


class App:
    """应用程序主控制器。

    组装 Manager、Storage 和 UI 层，通过字典分发表处理用户菜单选择。

    Attributes:
        manager: 学生数据管理器（纯业务逻辑）。
        storage: JSON 文件持久化管理器。
    """

    def __init__(self) -> None:
        """初始化应用程序组件。"""
        self.manager = StudentManager()
        self.storage = Storage()

    # ----------------------------------------------------------
    # 菜单处理函数（统一的 self 签名）
    # ----------------------------------------------------------

    def handle_add_student(self) -> None:
        """菜单 1：添加学生。"""
        name = ui.prompt_non_empty("请输入学生姓名: ")
        existing = self.manager.find_by_name(name)
        if existing:
            ui.display_warning(
                f"已存在学生 '{name}' (学号 {existing.student_id})"
            )
            if not ui.prompt_yes_no("是否继续添加？(y/n): "):
                return
        student = self.manager.add_student(name)
        ui.display_success(f"添加学生 {student.name}，学号 {student.student_id}")

    def handle_delete_student(self) -> None:
        """菜单 2：删除学生。"""
        sid = ui.prompt_student_id("请输入要删除的学生学号: ")
        try:
            student = self.manager.get_student(sid)
        except StudentNotFoundError:
            ui.display_error("学号不存在！")
            return

        if ui.prompt_yes_no(
            f"确认删除学生 {student.name} (学号{sid})? (y/n): "
        ):
            self.manager.delete_student(sid)
            ui.display_success("删除成功！")
        else:
            ui.display_message("取消删除。")

    def handle_add_grade(self) -> None:
        """菜单 3：添加或修改成绩。"""
        sid = ui.prompt_student_id("请输入学生学号: ")
        try:
            self.manager.get_student(sid)
        except StudentNotFoundError:
            ui.display_error("学号不存在！")
            return

        course = ui.prompt_course_name("请输入课程名称: ")
        score = ui.prompt_score()
        try:
            self.manager.set_grade(sid, course, score)
        except ValidationError as e:
            ui.display_error(str(e))
            return

        student = self.manager.get_student(sid)
        ui.display_success(
            f"已为学生 {student.name} 设置 {course} 成绩: {score}"
        )

    def handle_view_grades(self) -> None:
        """菜单 4：查看所有学生成绩。"""
        ui.display_student_list(self.manager.get_all_students())

    def handle_view_stats(self) -> None:
        """菜单 5：查看学生统计信息。"""
        ui.display_stats(self.manager.get_stats())

    def handle_view_ranking(self) -> None:
        """菜单 6：按总分排名显示。"""
        ui.display_ranking(self.manager.get_ranking())

    def handle_save_data(self) -> None:
        """菜单 7：保存数据到文件。"""
        try:
            self.storage.save(self.manager.to_dict())
            ui.display_success(f"数据已保存到 {self.storage.filepath}")
        except StorageError as e:
            ui.display_error(str(e))

    def handle_load_data(self) -> None:
        """菜单 8：从文件加载数据。"""
        try:
            data, counter = self.storage.load()
            self.manager.load_data(data, counter)
            ui.display_success(
                f"成功从 {self.storage.filepath} 加载数据，"
                f"共 {self.manager.student_count} 名学生。"
            )
        except (StorageError, DataCorruptionError) as e:
            ui.display_error(str(e))

    def handle_exit(self) -> None:
        """菜单 9：退出系统。"""
        ui.display_message("感谢使用，再见！")
        sys.exit(0)

    # ----------------------------------------------------------
    # 分发表
    # ----------------------------------------------------------

    @property
    def _dispatch(self) -> dict[str, Callable[[], None]]:
        """菜单键到处理函数的映射。

        所有处理函数具有相同的 ``(self) -> None`` 签名，
        消除了旧版中不同数量参数导致的特殊处理逻辑。
        """
        return {
            MenuAction.ADD_STUDENT.key: self.handle_add_student,
            MenuAction.DELETE_STUDENT.key: self.handle_delete_student,
            MenuAction.ADD_GRADE.key: self.handle_add_grade,
            MenuAction.VIEW_GRADES.key: self.handle_view_grades,
            MenuAction.VIEW_STATS.key: self.handle_view_stats,
            MenuAction.VIEW_RANKING.key: self.handle_view_ranking,
            MenuAction.SAVE_DATA.key: self.handle_save_data,
            MenuAction.LOAD_DATA.key: self.handle_load_data,
            MenuAction.EXIT.key: self.handle_exit,
        }

    # ----------------------------------------------------------
    # 主循环
    # ----------------------------------------------------------

    def run(self) -> None:
        """启动应用程序主循环。

        1. 检测已有数据文件并提示加载
        2. 循环：显示菜单 → 读取选择 → 分发执行
        3. 每条操作被通用异常处理包裹，防止单个错误导致程序崩溃
        """
        # 启动时自动检测已有数据
        if self.storage.file_exists():
            ui.display_message("发现已有数据文件，是否加载？")
            if ui.prompt_yes_no("(y/n): "):
                self.handle_load_data()

        # 主事件循环
        while True:
            try:
                ui.show_menu()
                choice = ui.get_choice()

                handler = self._dispatch.get(choice)
                if handler is None:
                    ui.display_error("无效选择，请输入1-9之间的数字。")
                    continue

                handler()

            except StudentSystemError as e:
                ui.display_error(str(e))

            except KeyboardInterrupt:
                print()
                ui.display_message("操作已取消，返回主菜单。")
                continue

            except EOFError:
                print()
                self.handle_exit()

        # unreachable — handle_exit() calls sys.exit()


def main() -> None:
    """程序入口点，创建并运行 App。"""
    app = App()
    app.run()


if __name__ == "__main__":
    main()
