"""图形化界面的单元测试。

测试 GUI 各 handler 方法与 StudentManager/Storage 的交互逻辑。
使用真实 tk.Tk 实例但不进入事件循环，实现 headless 测试。
"""

from __future__ import annotations

import tempfile
import tkinter as tk
import unittest
from unittest import mock

from student_system.exceptions import StudentNotFoundError, ValidationError
from student_system.gui import StudentManagerGUI
from student_system.manager import StudentManager
from student_system.storage import Storage


class TestStudentManagerGUIInit(unittest.TestCase):
    """测试 GUI 初始化。"""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()  # 隐藏窗口

    def tearDown(self) -> None:
        self.root.destroy()

    def test_init_creates_gui(self) -> None:
        """验证 GUI 对象创建成功，Manager 和 Storage 初始化正确。"""
        with tempfile.TemporaryDirectory() as tmp:
            data_file = f"{tmp}/test_data.json"
            app = StudentManagerGUI(self.root, data_file=data_file)
            self.assertIsInstance(app.manager, StudentManager)
            self.assertIsInstance(app.storage, Storage)
            self.assertEqual(app.manager.student_count, 0)
            self.assertEqual(app.storage.filepath, data_file)

    def test_init_without_data_file_uses_default(self) -> None:
        """验证不指定数据文件时使用默认路径。"""
        app = StudentManagerGUI(self.root)
        from student_system.models import DEFAULT_DATA_FILE

        self.assertEqual(app.storage.filepath, DEFAULT_DATA_FILE)


class TestAddStudentHandler(unittest.TestCase):
    """测试添加学生 handler。"""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        with tempfile.TemporaryDirectory() as tmp:
            self.data_file = f"{tmp}/test_data.json"
            self.app = StudentManagerGUI(self.root, data_file=self.data_file)

    def tearDown(self) -> None:
        self.root.destroy()

    def test_add_student_success(self) -> None:
        """验证通过 Entry 添加学生成功。"""
        self.app._add_name_entry.insert(0, "张三")
        self.app._handle_add_student()
        self.assertEqual(self.app.manager.student_count, 1)
        self.assertEqual(self.app.manager.get_student("1").name, "张三")
        # 验证 Entry 已清空
        self.assertEqual(self.app._add_name_entry.get(), "")

    def test_add_student_empty_name_shows_error(self) -> None:
        """验证空姓名显示错误提示。"""
        self.app._add_name_entry.delete(0, tk.END)
        self.app._handle_add_student()
        self.assertEqual(self.app.manager.student_count, 0)

    def test_add_duplicate_student(self) -> None:
        """验证重复姓名弹出确认。"""
        self.app.manager.add_student("李四")

        with mock.patch(
            "tkinter.messagebox.askyesno", return_value=True
        ) as mock_ask:
            self.app._add_name_entry.insert(0, "李四")
            self.app._handle_add_student()
            mock_ask.assert_called_once()
            self.assertEqual(self.app.manager.student_count, 2)


class TestDeleteStudentHandler(unittest.TestCase):
    """测试删除学生 handler。"""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        with tempfile.TemporaryDirectory() as tmp:
            self.data_file = f"{tmp}/test_data.json"
            self.app = StudentManagerGUI(self.root, data_file=self.data_file)
        self.app.manager.add_student("测试学生")

    def tearDown(self) -> None:
        self.root.destroy()

    def test_delete_student_success(self) -> None:
        """验证删除已存在的学生。"""
        with mock.patch(
            "tkinter.messagebox.askyesno", return_value=True
        ) as mock_confirm:
            self.app._del_id_entry.insert(0, "1")
            self.app._handle_delete_student()
            mock_confirm.assert_called_once()
            self.assertEqual(self.app.manager.student_count, 0)

    def test_delete_nonexistent_student(self) -> None:
        """验证删除不存在的学号。"""
        self.app._del_id_entry.insert(0, "999")
        self.app._handle_delete_student()
        self.assertEqual(self.app.manager.student_count, 1)

    def test_delete_empty_id(self) -> None:
        """验证空学号不执行删除。"""
        self.app._del_id_entry.delete(0, tk.END)
        self.app._handle_delete_student()
        self.assertEqual(self.app.manager.student_count, 1)


class TestAddGradeHandler(unittest.TestCase):
    """测试设置成绩 handler。"""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        with tempfile.TemporaryDirectory() as tmp:
            self.data_file = f"{tmp}/test_data.json"
            self.app = StudentManagerGUI(self.root, data_file=self.data_file)
        self.app.manager.add_student("小明")

    def tearDown(self) -> None:
        self.root.destroy()

    def test_set_grade_success(self) -> None:
        """验证成功设置成绩。"""
        self.app._grade_id_entry.insert(0, "1")
        self.app._grade_course_entry.insert(0, "数学")
        self.app._grade_score_entry.insert(0, "95")
        self.app._handle_add_grade()

        student = self.app.manager.get_student("1")
        self.assertIn("数学", student.grades)
        self.assertEqual(student.grades["数学"], 95.0)

    def test_set_grade_invalid_score(self) -> None:
        """验证非法分数值被拒绝。"""
        self.app._grade_id_entry.insert(0, "1")
        self.app._grade_course_entry.insert(0, "语文")
        self.app._grade_score_entry.insert(0, "abc")
        self.app._handle_add_grade()

        student = self.app.manager.get_student("1")
        self.assertNotIn("语文", student.grades)

    def test_set_grade_out_of_range(self) -> None:
        """验证超出范围的分数被 Manager 拒绝。"""
        self.app._grade_id_entry.insert(0, "1")
        self.app._grade_course_entry.insert(0, "物理")
        self.app._grade_score_entry.insert(0, "150")
        self.app._handle_add_grade()

        student = self.app.manager.get_student("1")
        self.assertNotIn("物理", student.grades)

    def test_set_grade_empty_fields(self) -> None:
        """验证空字段不执行操作。"""
        for field, value in [
            ("_grade_id_entry", ""),
            ("_grade_course_entry", ""),
            ("_grade_score_entry", ""),
        ]:
            with self.subTest(field=field):
                self.app._grade_id_entry.delete(0, tk.END)
                self.app._grade_course_entry.delete(0, tk.END)
                self.app._grade_score_entry.delete(0, tk.END)
                getattr(self.app, field).insert(0, value)
                self.app._handle_add_grade()


class TestTreeviewPopulation(unittest.TestCase):
    """测试 Treeview 数据填充逻辑。"""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        with tempfile.TemporaryDirectory() as tmp:
            self.data_file = f"{tmp}/test_data.json"
            self.app = StudentManagerGUI(self.root, data_file=self.data_file)

    def tearDown(self) -> None:
        self.root.destroy()

    def test_populate_grades_empty(self) -> None:
        """验证无学生时表格填充不报错。"""
        self.app._populate_grades_tree()
        children = self.app._grades_tree.get_children()
        self.assertEqual(len(children), 0)

    def test_populate_grades_with_data(self) -> None:
        """验证有学生和成绩时表格正确填充。"""
        self.app.manager.add_student("张三")
        self.app.manager.set_grade("1", "数学", 90)
        self.app.manager.add_student("李四")

        self.app._populate_grades_tree()
        children = self.app._grades_tree.get_children()
        # 张三: 1 行（有成绩），李四: 1 行（无成绩）
        self.assertEqual(len(children), 2)

    def test_populate_stats_and_ranking(self) -> None:
        """验证统计和排名表格的正确填充。"""
        self.app.manager.add_student("A")
        self.app.manager.add_student("B")
        self.app.manager.set_grade("1", "数学", 90)
        self.app.manager.set_grade("2", "数学", 80)

        self.app._populate_stats_tree()
        self.app._populate_ranking_tree()

        stats_children = self.app._stats_tree.get_children()
        rank_children = self.app._ranking_tree.get_children()
        self.assertEqual(len(stats_children), 2)
        self.assertEqual(len(rank_children), 2)

        # 排名第一应是学号 1（总分 90）
        first_rank_values = self.app._ranking_tree.item(
            rank_children[0], "values"
        )
        self.assertEqual(first_rank_values[1], "1")  # 学号列


class TestSaveAndLoad(unittest.TestCase):
    """测试保存和加载功能。"""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self) -> None:
        self.root.destroy()

    def test_save_creates_file(self) -> None:
        """验证保存操作创建数据文件。"""
        with tempfile.TemporaryDirectory() as tmp:
            data_file = f"{tmp}/test.json"
            app = StudentManagerGUI(self.root, data_file=data_file)
            app.manager.add_student("测试")
            app._handle_save_data()

            import os

            self.assertTrue(os.path.exists(data_file))

    def test_load_restores_data(self) -> None:
        """验证加载操作恢复数据。"""
        with tempfile.TemporaryDirectory() as tmp:
            data_file = f"{tmp}/test.json"
            # 先保存一份数据
            app1 = StudentManagerGUI(self.root, data_file=data_file)
            app1.manager.add_student("张三")
            app1.storage.save(app1.manager.to_dict())

            # 重新创建并加载（使用新 root，不触动 self.root）
            root2 = tk.Tk()
            root2.withdraw()
            try:
                app2 = StudentManagerGUI(root2, data_file=data_file)
                app2._handle_load_data()
                self.assertEqual(app2.manager.student_count, 1)
                self.assertEqual(app2.manager.get_student("1").name, "张三")
            finally:
                root2.destroy()


class TestHelperMethods(unittest.TestCase):
    """测试工具方法。"""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        with tempfile.TemporaryDirectory() as tmp:
            self.data_file = f"{tmp}/test.json"
            self.app = StudentManagerGUI(self.root, data_file=self.data_file)

    def tearDown(self) -> None:
        self.root.destroy()

    def test_update_count(self) -> None:
        """验证学生数量更新。"""
        self.app._update_count()
        self.assertIn("0", self.app.count_var.get())

        self.app.manager.add_student("测试")
        self.app._update_count()
        self.assertIn("1", self.app.count_var.get())

    def test_update_status(self) -> None:
        """验证状态栏更新。"""
        self.app._update_status("测试消息")
        self.assertEqual(self.app.status_var.get(), "测试消息")

    def test_refresh_all_views(self) -> None:
        """验证全量刷新不报错。"""
        self.app.manager.add_student("学生1")
        self.app.manager.add_student("学生2")
        self.app.manager.set_grade("1", "数学", 85)
        self.app._refresh_all_views()
        self.assertEqual(
            len(self.app._grades_tree.get_children()), 2
        )
        self.assertEqual(
            len(self.app._stats_tree.get_children()), 2
        )

    def test_on_tab_changed(self) -> None:
        """验证标签页切换刷新。"""
        self.app.manager.add_student("学生")
        # 切换到数据查看标签（index 2）
        self.app.notebook.select(2)
        self.app._on_tab_changed()
        self.assertGreaterEqual(
            len(self.app._grades_tree.get_children()), 1
        )


if __name__ == "__main__":
    unittest.main()
