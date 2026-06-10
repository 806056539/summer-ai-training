"""集成测试 — 验证各模块协同工作。"""

import os
import tempfile
import unittest

from student_system.exceptions import StudentNotFoundError, ValidationError
from student_system.manager import StudentManager
from student_system.storage import Storage


class TestManagerWithStorage(unittest.TestCase):
    """验证 Manager 与 Storage 的协同。"""

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.filepath = os.path.join(self.tmpdir.name, "data.json")

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_save_and_load_cycle(self) -> None:
        """完整的 保存→清空→加载→验证 循环。"""
        # 1. 创建数据
        mgr = StudentManager()
        mgr.add_student("张三")
        mgr.add_student("李四")
        mgr.set_grade("1", "语文", 90)
        mgr.set_grade("1", "数学", 80)
        mgr.set_grade("2", "语文", 70)

        # 2. 保存到文件
        storage = Storage(self.filepath)
        storage.save(mgr.to_dict())

        # 3. 创建新的管理器并加载
        mgr2 = StudentManager()
        data, counter = storage.load()
        mgr2.load_data(data, counter)

        # 4. 验证数据一致
        self.assertEqual(mgr2.student_count, 2)
        self.assertEqual(mgr2.counter, 2)
        self.assertEqual(mgr2.get_student("1").name, "张三")
        self.assertEqual(mgr2.get_student("1").grades, {"语文": 90, "数学": 80})
        self.assertEqual(mgr2.get_student("2").name, "李四")
        self.assertEqual(mgr2.get_student("2").total_score, 70.0)

    def test_counter_preserved_after_load(self) -> None:
        """加载后 counter 应正确恢复，新添加的学生不会冲突。"""
        mgr = StudentManager()
        mgr.add_student("A")
        mgr.add_student("B")
        self.assertEqual(mgr.counter, 2)

        storage = Storage(self.filepath)
        storage.save(mgr.to_dict())

        mgr2 = StudentManager()
        data, counter = storage.load()
        mgr2.load_data(data, counter)
        self.assertEqual(mgr2.counter, 2)

        # 新添加的学生学号应从 3 开始
        new_student = mgr2.add_student("C")
        self.assertEqual(new_student.student_id, "3")

    def test_ranking_after_save_load(self) -> None:
        """排名在持久化后应保持一致。"""
        mgr = StudentManager()
        mgr.add_student("高分组")
        mgr.add_student("低分组")
        mgr.set_grade("1", "数学", 95)
        mgr.set_grade("2", "数学", 35)

        storage = Storage(self.filepath)
        storage.save(mgr.to_dict())

        mgr2 = StudentManager()
        data, counter = storage.load()
        mgr2.load_data(data, counter)

        ranking = mgr2.get_ranking()
        self.assertEqual(ranking[0]["name"], "高分组")
        self.assertEqual(ranking[1]["name"], "低分组")


class TestFullWorkflow(unittest.TestCase):
    """端到端工作流测试（不依赖 UI）。"""

    def test_full_student_lifecycle(self) -> None:
        """模拟一个学生的完整生命周期。"""
        mgr = StudentManager()

        # 添加
        s = mgr.add_student("测试学生")
        sid = s.student_id
        self.assertEqual(mgr.student_count, 1)

        # 录入成绩
        mgr.set_grade(sid, "语文", 85)
        mgr.set_grade(sid, "数学", 92)
        mgr.set_grade(sid, "英语", 78)
        self.assertEqual(mgr.get_student(sid).course_count, 3)

        # 查看统计
        stats = mgr.get_stats()
        student_stats = stats[0]
        self.assertAlmostEqual(student_stats["total"], 255.0)
        self.assertAlmostEqual(student_stats["avg"], 85.0)

        # 修改成绩
        mgr.set_grade(sid, "语文", 95)
        self.assertAlmostEqual(mgr.get_student(sid).total_score, 265.0)

        # 删除
        mgr.delete_student(sid)
        self.assertEqual(mgr.student_count, 0)

    def test_duplicate_name_handling(self) -> None:
        """验证同名学生的处理逻辑。"""
        mgr = StudentManager()
        mgr.add_student("张三")

        # 查找同名
        found = mgr.find_by_name("张三")
        self.assertIsNotNone(found)
        self.assertEqual(found.student_id, "1")

        # 可以添加第二个同名
        s2 = mgr.add_student("张三")
        self.assertEqual(s2.student_id, "2")
        self.assertEqual(mgr.student_count, 2)

        # find_by_name 返回第一个
        self.assertEqual(mgr.find_by_name("张三").student_id, "1")

    def test_edge_case_scores(self) -> None:
        """边界成绩值测试。"""
        mgr = StudentManager()
        s = mgr.add_student("边界测试")

        mgr.set_grade(s.student_id, "零分", 0.0)
        mgr.set_grade(s.student_id, "满分", 100.0)
        mgr.set_grade(s.student_id, "小数分", 0.5)

        student = mgr.get_student(s.student_id)
        self.assertAlmostEqual(student.total_score, 100.5)

    def test_multiple_students_ranking(self) -> None:
        """多学生排名测试。"""
        mgr = StudentManager()
        for i, name in enumerate(["A", "B", "C", "D", "E"]):
            s = mgr.add_student(name)
            # 不同分数确保排序稳定
            mgr.set_grade(s.student_id, "统一考试", float(100 - i * 10))

        ranking = mgr.get_ranking()
        self.assertEqual(len(ranking), 5)
        self.assertEqual(ranking[0]["name"], "A")
        self.assertEqual(ranking[0]["total"], 100.0)
        self.assertEqual(ranking[-1]["name"], "E")
        self.assertEqual(ranking[-1]["total"], 60.0)


if __name__ == "__main__":
    unittest.main()
