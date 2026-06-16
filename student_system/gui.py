"""学生成绩管理系统 — 图形化界面（tkinter）。

本模块提供基于 tkinter 的 GUI，复用现有的 StudentManager 和 Storage 层，
将 CLI 的 9 个菜单操作映射为 5 个 Notebook 标签页。

Examples:
    >>> from student_system.gui import main
    >>> main()  # 启动 GUI 主窗口
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from .exceptions import (
    DataCorruptionError,
    StorageError,
    StudentSystemError,
)
from .manager import StudentManager
from .models import DEFAULT_DATA_FILE
from .storage import Storage


def main() -> None:
    """启动图形化学生成绩管理系统。"""
    root = tk.Tk()
    root.title("学生成绩管理系统")
    root.geometry("920x680")
    root.minsize(800, 550)

    # 设置 ttk 主题（Windows 下使用 vista 等效主题）
    style = ttk.Style()
    available_themes = style.theme_names()
    if "clam" in available_themes:
        style.theme_use("clam")

    app = StudentManagerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app._on_close)
    root.mainloop()


# ============================================================
# 主窗口类
# ============================================================


class StudentManagerGUI:
    """图形化学生成绩管理系统主窗口。

    使用 ttk.Notebook 将 9 个功能组织为 5 个标签页：
    - 学生管理（添加/删除）
    - 成绩管理（设置成绩）
    - 数据查看（成绩表）
    - 统计排名（统计 + 排名）
    - 文件操作（保存/加载/退出）

    Attributes:
        root: tkinter 根窗口。
        manager: 学生数据管理器（纯业务逻辑）。
        storage: JSON 文件持久化管理器。
        notebook: 标签页容器。
        status_var: 状态栏文本变量。
        count_var: 状态栏学生数量变量。
    """

    def __init__(self, root: tk.Tk, data_file: str | None = None) -> None:
        """初始化 GUI 组件并构建界面。

        Args:
            root: tkinter 根窗口。
            data_file: 数据文件路径，默认使用 DEFAULT_DATA_FILE。
        """
        self.root = root
        self.manager = StudentManager()
        self.storage = Storage(data_file or DEFAULT_DATA_FILE)

        # 跟踪已构建的 Treeview，用于刷新
        self._grades_tree: ttk.Treeview | None = None
        self._stats_tree: ttk.Treeview | None = None
        self._ranking_tree: ttk.Treeview | None = None

        # 状态栏变量
        self.status_var = tk.StringVar(value="就绪")
        self.count_var = tk.StringVar(value="0")

        self._build_ui()

        # 启动时检测已有数据文件
        if self.storage.file_exists():
            if messagebox.askyesno(
                "加载数据",
                "发现已有数据文件，是否加载？",
            ):
                self._handle_load_data()

        self._update_count()

    # ----------------------------------------------------------
    # 界面构建
    # ----------------------------------------------------------

    def _build_ui(self) -> None:
        """构建完整的用户界面。"""
        # --- 主内容区：Notebook 标签页 ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))

        # 创建 5 个标签页
        tab_student = self._build_student_management_tab()
        tab_grade = self._build_grade_management_tab()
        tab_view = self._build_view_tab()
        tab_stats = self._build_stats_tab()
        tab_data = self._build_data_tab()

        self.notebook.add(tab_student, text="  学生管理  ")
        self.notebook.add(tab_grade, text="  成绩管理  ")
        self.notebook.add(tab_view, text="  数据查看  ")
        self.notebook.add(tab_stats, text="  统计排名  ")
        self.notebook.add(tab_data, text="  文件  ")

        # 标签页切换时自动刷新
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # --- 底部状态栏 ---
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=8, pady=(4, 8))

        ttk.Separator(status_frame, orient=tk.HORIZONTAL).pack(fill=tk.X)

        bar = ttk.Frame(status_frame)
        bar.pack(fill=tk.X, pady=(4, 0))

        status_label = ttk.Label(
            bar, textvariable=self.status_var, anchor=tk.W
        )
        status_label.pack(side=tk.LEFT)

        count_label = ttk.Label(
            bar, textvariable=self.count_var, anchor=tk.E
        )
        count_label.pack(side=tk.RIGHT)

    # ============================================================
    # Tab 1: 学生管理
    # ============================================================

    def _build_student_management_tab(self) -> ttk.Frame:
        """构建学生管理标签页（添加学生、删除学生）。

        Returns:
            包含表单控件的 Frame。
        """
        parent = ttk.Frame(self.notebook, padding=20)

        # ---- 添加学生 ----
        add_frame = ttk.LabelFrame(parent, text=" 添加学生 ", padding=15)
        add_frame.pack(fill=tk.X, pady=(0, 15))

        row1 = ttk.Frame(add_frame)
        row1.pack(fill=tk.X)
        ttk.Label(row1, text="姓名：", width=8).pack(side=tk.LEFT)
        self._add_name_entry = ttk.Entry(row1, width=30, font=("", 11))
        self._add_name_entry.pack(side=tk.LEFT, padx=(0, 12))
        self._add_name_entry.bind("<Return>", lambda e: self._handle_add_student())
        add_btn = ttk.Button(row1, text="添加学生", command=self._handle_add_student)
        add_btn.pack(side=tk.LEFT)

        self._add_feedback = ttk.Label(add_frame, text="", foreground="green")
        self._add_feedback.pack(anchor=tk.W, pady=(8, 0))

        # ---- 删除学生 ----
        del_frame = ttk.LabelFrame(parent, text=" 删除学生 ", padding=15)
        del_frame.pack(fill=tk.X)

        row2 = ttk.Frame(del_frame)
        row2.pack(fill=tk.X)
        ttk.Label(row2, text="学号：", width=8).pack(side=tk.LEFT)
        self._del_id_entry = ttk.Entry(row2, width=30, font=("", 11))
        self._del_id_entry.pack(side=tk.LEFT, padx=(0, 12))
        self._del_id_entry.bind("<Return>", lambda e: self._handle_delete_student())
        del_btn = ttk.Button(row2, text="删除学生", command=self._handle_delete_student)
        del_btn.pack(side=tk.LEFT)

        self._del_feedback = ttk.Label(del_frame, text="", foreground="green")
        self._del_feedback.pack(anchor=tk.W, pady=(8, 0))

        return parent

    # ============================================================
    # Tab 2: 成绩管理
    # ============================================================

    def _build_grade_management_tab(self) -> ttk.Frame:
        """构建成绩管理标签页（添加/修改成绩）。

        Returns:
            包含表单控件的 Frame。
        """
        parent = ttk.Frame(self.notebook, padding=20)

        grade_frame = ttk.LabelFrame(parent, text=" 设置成绩 ", padding=15)
        grade_frame.pack(fill=tk.X)

        # 学号行
        row1 = ttk.Frame(grade_frame)
        row1.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(row1, text="学号：", width=8).pack(side=tk.LEFT)
        self._grade_id_entry = ttk.Entry(row1, width=30, font=("", 11))
        self._grade_id_entry.pack(side=tk.LEFT)

        # 课程行
        row2 = ttk.Frame(grade_frame)
        row2.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(row2, text="课程：", width=8).pack(side=tk.LEFT)
        self._grade_course_entry = ttk.Entry(row2, width=30, font=("", 11))
        self._grade_course_entry.pack(side=tk.LEFT)

        # 成绩行
        row3 = ttk.Frame(grade_frame)
        row3.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(row3, text="成绩：", width=8).pack(side=tk.LEFT)
        self._grade_score_entry = ttk.Entry(row3, width=30, font=("", 11))
        self._grade_score_entry.pack(side=tk.LEFT)
        ttk.Label(
            row3, text="(0-100)", foreground="gray"
        ).pack(side=tk.LEFT, padx=(8, 0))

        # 按钮
        btn_row = ttk.Frame(grade_frame)
        btn_row.pack(fill=tk.X)
        set_btn = ttk.Button(
            btn_row, text="设置成绩", command=self._handle_add_grade
        )
        set_btn.pack(side=tk.LEFT, padx=(68, 0))

        self._grade_feedback = ttk.Label(
            grade_frame, text="", foreground="green"
        )
        self._grade_feedback.pack(anchor=tk.W, pady=(10, 0))

        return parent

    # ============================================================
    # Tab 3: 数据查看
    # ============================================================

    def _build_view_tab(self) -> ttk.Frame:
        """构建数据查看标签页（所有学生成绩表）。

        Returns:
            包含 Treeview 表格的 Frame。
        """
        parent = ttk.Frame(self.notebook, padding=10)

        # 工具栏
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(
            toolbar, text="所有学生成绩表", font=("", 12, "bold")
        ).pack(side=tk.LEFT)
        ttk.Button(
            toolbar, text="刷新", command=self._handle_view_grades
        ).pack(side=tk.RIGHT)

        # Treeview
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("学号", "姓名", "课程", "成绩", "总分")
        tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            height=15,
        )
        self._grades_tree = tree

        # 列定义
        col_widths = {"学号": 80, "姓名": 120, "课程": 160, "成绩": 80, "总分": 80}
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=col_widths.get(col, 100), anchor=tk.CENTER)

        # 垂直滚动条
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # 初始加载
        self._populate_grades_tree()

        return parent

    # ============================================================
    # Tab 4: 统计排名
    # ============================================================

    def _build_stats_tab(self) -> ttk.Frame:
        """构建统计排名标签页（统计信息 + 总分排名）。

        Returns:
            包含两个 Treeview 的 Frame。
        """
        parent = ttk.Frame(self.notebook, padding=10)

        # ---- 上半部分：统计信息 ----
        stats_section = ttk.LabelFrame(parent, text=" 统计信息 ", padding=8)
        stats_section.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        cols_s = ("学号", "姓名", "总分", "平均分", "课程数")
        tree_s = ttk.Treeview(
            stats_section,
            columns=cols_s,
            show="headings",
            height=8,
        )
        self._stats_tree = tree_s

        widths_s = {"学号": 80, "姓名": 160, "总分": 100, "平均分": 100, "课程数": 80}
        for col in cols_s:
            tree_s.heading(col, text=col)
            tree_s.column(col, width=widths_s.get(col, 100), anchor=tk.CENTER)

        vsb_s = ttk.Scrollbar(
            stats_section, orient=tk.VERTICAL, command=tree_s.yview
        )
        tree_s.configure(yscrollcommand=vsb_s.set)

        tree_s.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb_s.pack(side=tk.RIGHT, fill=tk.Y)

        # ---- 下半部分：总分排名 ----
        rank_section = ttk.LabelFrame(parent, text=" 总分排名 ", padding=8)
        rank_section.pack(fill=tk.BOTH, expand=True)

        cols_r = ("排名", "学号", "姓名", "总分", "平均分")
        tree_r = ttk.Treeview(
            rank_section,
            columns=cols_r,
            show="headings",
            height=8,
        )
        self._ranking_tree = tree_r

        widths_r = {"排名": 60, "学号": 80, "姓名": 160, "总分": 100, "平均分": 100}
        for col in cols_r:
            tree_r.heading(col, text=col)
            tree_r.column(col, width=widths_r.get(col, 100), anchor=tk.CENTER)

        vsb_r = ttk.Scrollbar(
            rank_section, orient=tk.VERTICAL, command=tree_r.yview
        )
        tree_r.configure(yscrollcommand=vsb_r.set)

        tree_r.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb_r.pack(side=tk.RIGHT, fill=tk.Y)

        # 初始加载
        self._populate_stats_tree()
        self._populate_ranking_tree()

        return parent

    # ============================================================
    # Tab 5: 文件操作
    # ============================================================

    def _build_data_tab(self) -> ttk.Frame:
        """构建文件操作标签页（保存、加载、退出）。

        Returns:
            包含操作按钮的 Frame。
        """
        parent = ttk.Frame(self.notebook, padding=20)

        # 居中容器
        container = ttk.Frame(parent)
        container.place(relx=0.5, rely=0.4, anchor=tk.CENTER)

        ttk.Label(
            container, text="文件操作", font=("", 14, "bold")
        ).pack(pady=(0, 20))

        btn_width = 22
        ttk.Button(
            container,
            text="💾  保存数据到文件",
            width=btn_width,
            command=self._handle_save_data,
        ).pack(pady=6)

        ttk.Button(
            container,
            text="📂  从文件加载数据",
            width=btn_width,
            command=self._handle_load_data,
        ).pack(pady=6)

        ttk.Separator(container, orient=tk.HORIZONTAL).pack(
            fill=tk.X, pady=16
        )

        ttk.Button(
            container,
            text="🚪  退出系统",
            width=btn_width,
            command=self._handle_exit,
        ).pack(pady=6)

        self._file_feedback = ttk.Label(
            container, text="", foreground="green"
        )
        self._file_feedback.pack(pady=(10, 0))

        # 文件路径提示
        ttk.Label(
            container,
            text=f"数据文件: {self.storage.filepath}",
            foreground="gray",
        ).pack(pady=(16, 0))

        return parent

    # ============================================================
    # 事件处理函数
    # ============================================================

    def _handle_add_student(self) -> None:
        """处理添加学生操作。"""
        name = self._add_name_entry.get().strip()
        if not name:
            self._show_inline_feedback(
                self._add_feedback, "请输入学生姓名", error=True
            )
            return

        try:
            # 检查重复
            existing = self.manager.find_by_name(name)
            if existing:
                if not messagebox.askyesno(
                    "确认添加",
                    f"已存在学生 '{name}' (学号 {existing.student_id})。\n"
                    f"是否继续添加？",
                ):
                    return

            student = self.manager.add_student(name)
            self._add_name_entry.delete(0, tk.END)
            self._show_inline_feedback(
                self._add_feedback,
                f"添加成功 — {student.name}，学号 {student.student_id}",
            )
            self._update_status(f"已添加学生 {student.name}")
            self._update_count()
            self._refresh_all_views()
        except StudentSystemError as e:
            self._show_inline_feedback(
                self._add_feedback, str(e), error=True
            )

    def _handle_delete_student(self) -> None:
        """处理删除学生操作。"""
        sid = self._del_id_entry.get().strip()
        if not sid:
            self._show_inline_feedback(
                self._del_feedback, "请输入学号", error=True
            )
            return

        try:
            student = self.manager.get_student(sid)
        except StudentSystemError as e:
            self._show_inline_feedback(self._del_feedback, str(e), error=True)
            return

        if not messagebox.askyesno(
            "确认删除",
            f"确认删除学生 {student.name} (学号 {sid})？",
        ):
            return

        try:
            self.manager.delete_student(sid)
            self._del_id_entry.delete(0, tk.END)
            self._show_inline_feedback(
                self._del_feedback, "删除成功！"
            )
            self._update_status(f"已删除学号 {sid} 的学生")
            self._update_count()
            self._refresh_all_views()
        except StudentSystemError as e:
            self._show_inline_feedback(
                self._del_feedback, str(e), error=True
            )

    def _handle_add_grade(self) -> None:
        """处理添加/修改成绩操作。"""
        sid = self._grade_id_entry.get().strip()
        course = self._grade_course_entry.get().strip()
        score_str = self._grade_score_entry.get().strip()

        # 前端校验
        if not sid:
            self._show_inline_feedback(
                self._grade_feedback, "请输入学号", error=True
            )
            return
        if not course:
            self._show_inline_feedback(
                self._grade_feedback, "请输入课程名称", error=True
            )
            return
        if not score_str:
            self._show_inline_feedback(
                self._grade_feedback, "请输入成绩", error=True
            )
            return

        try:
            score = float(score_str)
        except ValueError:
            self._show_inline_feedback(
                self._grade_feedback,
                "成绩必须是数字",
                error=True,
            )
            return

        try:
            self.manager.set_grade(sid, course, score)
            student = self.manager.get_student(sid)
            self._grade_score_entry.delete(0, tk.END)
            self._show_inline_feedback(
                self._grade_feedback,
                f"已为 {student.name} 设置 {course} 成绩: {score}",
            )
            self._update_status(
                f"已设置 {student.name} 的 {course} 成绩"
            )
            self._refresh_all_views()
        except StudentSystemError as e:
            self._show_inline_feedback(
                self._grade_feedback, str(e), error=True
            )

    def _handle_view_grades(self) -> None:
        """刷新数据查看标签页的表格。"""
        self._populate_grades_tree()
        self._update_status("已刷新成绩表")

    def _handle_view_stats(self) -> None:
        """刷新统计信息表格。"""
        self._populate_stats_tree()
        self._update_status("已刷新统计信息")

    def _handle_view_ranking(self) -> None:
        """刷新排名表格。"""
        self._populate_ranking_tree()
        self._update_status("已刷新排名")

    def _handle_save_data(self) -> None:
        """处理保存数据到文件操作。"""
        try:
            self.storage.save(self.manager.to_dict())
            self._show_info(
                "保存成功",
                f"数据已保存到 {self.storage.filepath}",
            )
            self._file_feedback.config(
                text=f"已保存到 {self.storage.filepath}", foreground="green"
            )
            self._update_status(f"数据已保存到 {self.storage.filepath}")
        except (StorageError, StudentSystemError) as e:
            self._show_error("保存失败", str(e))
            self._file_feedback.config(text=str(e), foreground="red")

    def _handle_load_data(self) -> None:
        """处理从文件加载数据操作。"""
        if self.manager.student_count > 0:
            if not messagebox.askyesno(
                "确认加载",
                "加载数据将覆盖当前所有数据，是否继续？",
            ):
                return

        try:
            data, counter = self.storage.load()
            self.manager.load_data(data, counter)
            self._show_info(
                "加载成功",
                f"成功从 {self.storage.filepath} 加载数据，"
                f"共 {self.manager.student_count} 名学生。",
            )
            self._file_feedback.config(
                text=f"已加载 {self.manager.student_count} 名学生",
                foreground="green",
            )
            self._update_status(
                f"已从 {self.storage.filepath} 加载 {self.manager.student_count} 名学生"
            )
            self._update_count()
            self._refresh_all_views()
        except (StorageError, DataCorruptionError, StudentSystemError) as e:
            self._show_error("加载失败", str(e))
            self._file_feedback.config(text=str(e), foreground="red")

    def _handle_exit(self) -> None:
        """处理退出系统操作。"""
        if self.manager.student_count > 0:
            result = messagebox.askyesnocancel(
                "退出确认",
                "退出前是否保存数据？\n\n"
                "「是」= 保存后退出\n"
                "「否」= 不保存直接退出\n"
                "「取消」= 返回",
            )
            if result is None:  # 取消
                return
            if result:  # 是 — 保存
                try:
                    self.storage.save(self.manager.to_dict())
                except StorageError as e:
                    if not messagebox.askyesno(
                        "保存失败",
                        f"{e}\n\n确定要不保存直接退出吗？",
                    ):
                        return

        self.root.destroy()

    # ============================================================
    # Treeview 数据填充
    # ============================================================

    def _populate_grades_tree(self) -> None:
        """清空并重新填充成绩 Treeview。"""
        tree = self._grades_tree
        if tree is None:
            return
        for item in tree.get_children():
            tree.delete(item)

        for student in self.manager.get_all_students():
            if not student.grades:
                tree.insert(
                    "",
                    tk.END,
                    values=(
                        student.student_id,
                        student.name,
                        "(暂无成绩)",
                        "-",
                        "-",
                    ),
                )
            else:
                for course, score in student.grades.items():
                    tree.insert(
                        "",
                        tk.END,
                        values=(
                            student.student_id,
                            student.name,
                            course,
                            f"{score:.1f}",
                            f"{student.total_score:.1f}",
                        ),
                    )

    def _populate_stats_tree(self) -> None:
        """清空并重新填充统计信息 Treeview。"""
        tree = self._stats_tree
        if tree is None:
            return
        for item in tree.get_children():
            tree.delete(item)

        for entry in self.manager.get_stats():
            tree.insert(
                "",
                tk.END,
                values=(
                    entry["student_id"],
                    entry["name"],
                    f"{entry['total']:.2f}",
                    f"{entry['avg']:.2f}",
                    entry["course_count"],
                ),
            )

    def _populate_ranking_tree(self) -> None:
        """清空并重新填充排名 Treeview。"""
        tree = self._ranking_tree
        if tree is None:
            return
        for item in tree.get_children():
            tree.delete(item)

        for rank, entry in enumerate(self.manager.get_ranking(), start=1):
            tree.insert(
                "",
                tk.END,
                values=(
                    rank,
                    entry["student_id"],
                    entry["name"],
                    f"{entry['total']:.2f}",
                    f"{entry['avg']:.2f}",
                ),
            )

    # ============================================================
    # 工具方法
    # ============================================================

    def _show_inline_feedback(
        self, label: ttk.Label, text: str, error: bool = False
    ) -> None:
        """在指定 Label 中显示内联反馈文字。

        Args:
            label: 目标 Label 控件。
            text: 要显示的文本。
            error: True 表示错误消息（红色），False 表示成功消息（绿色）。
        """
        label.config(
            text=text,
            foreground="red" if error else "green",
        )

    def _show_error(self, title: str, message: str) -> None:
        """使用 messagebox 显示错误弹窗。

        Args:
            title: 弹窗标题。
            message: 错误详情。
        """
        messagebox.showerror(title, message)

    def _show_info(self, title: str, message: str) -> None:
        """使用 messagebox 显示信息弹窗。

        Args:
            title: 弹窗标题。
            message: 信息内容。
        """
        messagebox.showinfo(title, message)

    def _update_status(self, text: str) -> None:
        """更新状态栏文本。

        Args:
            text: 状态文本。
        """
        self.status_var.set(text)

    def _update_count(self) -> None:
        """更新状态栏学生数量显示。"""
        self.count_var.set(f"学生数: {self.manager.student_count}")

    def _refresh_all_views(self) -> None:
        """刷新所有 Treeview 表格。"""
        self._populate_grades_tree()
        self._populate_stats_tree()
        self._populate_ranking_tree()

    # ----------------------------------------------------------
    # 事件回调
    # ----------------------------------------------------------

    def _on_tab_changed(self, event: tk.Event | None = None) -> None:
        """标签页切换时自动刷新该页数据。

        Args:
            event: tkinter 事件对象（可选）。
        """
        current = self.notebook.index(self.notebook.select())
        if current == 2:  # 数据查看
            self._populate_grades_tree()
        elif current == 3:  # 统计排名
            self._populate_stats_tree()
            self._populate_ranking_tree()

    def _on_close(self) -> None:
        """窗口关闭时调用，提示保存。"""
        self._handle_exit()


__all__ = ["StudentManagerGUI", "main"]
