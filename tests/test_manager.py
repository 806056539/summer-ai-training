"""StudentManager 业务逻辑的单元测试。"""

import unittest

from student_system.exceptions import (
    DataCorruptionError,
    StudentNotFoundError,
    ValidationError,
)
from student_system.manager import StudentManager
from student_system.models import Student


class TestStudentManagerInit(unittest.TestCase):
    """验证初始状态。"""

    def test_empty_on_init(self) -> None:
        mgr = StudentManager()
        self.assertEqual(mgr.student_count, 0)
        self.assertEqual(mgr.counter, 0)
        self.assertEqual(mgr.get_all_students(), [])


class TestAddStudent(unittest.TestCase):
    """验证添加学生。"""

    def setUp(self) -> None:
        self.mgr = StudentManager()

    def test_add_single_student(self) -> None:
        s = self.mgr.add_student("张三")
        self.assertIsInstance(s, Student)
        self.assertEqual(s.student_id, "1")
        self.assertEqual(s.name, "张三")
        self.assertEqual(self.mgr.student_count, 1)
        self.assertEqual(self.mgr.counter, 1)

    def test_add_multiple_students(self) -> None:
        ids = []
        for name in ("Alice", "Bob", "Charlie"):
            s = self.mgr.add_student(name)
            ids.append(s.student_id)
        self.assertEqual(ids, ["1", "2", "3"])
        self.assertEqual(self.mgr.student_count, 3)
        self.assertEqual(self.mgr.counter, 3)

    def test_add_student_empty_name_raises(self) -> None:
        with self.assertRaises(ValidationError):
            self.mgr.add_student("")

    def test_add_student_whitespace_name_raises(self) -> None:
        with self.assertRaises(ValidationError):
            self.mgr.add_student("   ")

    def test_add_student_name_stripped(self) -> None:
        s = self.mgr.add_student("  张三  ")
        self.assertEqual(s.name, "张三")


class TestDeleteStudent(unittest.TestCase):
    """验证删除学生。"""

    def setUp(self) -> None:
        self.mgr = StudentManager()
        self.mgr.add_student("张三")

    def test_delete_existing(self) -> None:
        self.mgr.delete_student("1")
        self.assertEqual(self.mgr.student_count, 0)

    def test_delete_nonexistent_raises(self) -> None:
        with self.assertRaises(StudentNotFoundError):
            self.mgr.delete_student("99")

    def test_delete_twice_raises(self) -> None:
        self.mgr.delete_student("1")
        with self.assertRaises(StudentNotFoundError):
            self.mgr.delete_student("1")


class TestGetStudent(unittest.TestCase):
    """验证查找学生。"""

    def setUp(self) -> None:
        self.mgr = StudentManager()
        self.mgr.add_student("Alice")
        self.mgr.add_student("Bob")

    def test_get_existing(self) -> None:
        s = self.mgr.get_student("1")
        self.assertEqual(s.name, "Alice")

    def test_get_nonexistent_raises(self) -> None:
        with self.assertRaises(StudentNotFoundError):
            self.mgr.get_student("99")

    def test_find_by_name_existing(self) -> None:
        s = self.mgr.find_by_name("Bob")
        self.assertIsNotNone(s)
        self.assertEqual(s.student_id, "2")

    def test_find_by_name_nonexistent(self) -> None:
        self.assertIsNone(self.mgr.find_by_name("Nobody"))

    def test_find_by_name_strict_raises(self) -> None:
        with self.assertRaises(StudentNotFoundError):
            self.mgr.find_by_name_strict("Nobody")


class TestGetAllStudents(unittest.TestCase):
    """验证获取所有学生。"""

    def test_empty_list(self) -> None:
        mgr = StudentManager()
        self.assertEqual(mgr.get_all_students(), [])

    def test_sorted_by_id(self) -> None:
        mgr = StudentManager()
        mgr.add_student("C")
        mgr.add_student("A")
        mgr.add_student("B")
        result = mgr.get_all_students()
        ids = [s.student_id for s in result]
        self.assertEqual(ids, ["1", "2", "3"])


class TestSetGrade(unittest.TestCase):
    """验证成绩设置。"""

    def setUp(self) -> None:
        self.mgr = StudentManager()
        self.mgr.add_student("张三")

    def test_set_valid_grade(self) -> None:
        self.mgr.set_grade("1", "语文", 85)
        s = self.mgr.get_student("1")
        self.assertEqual(s.grades["语文"], 85)

    def test_set_grade_nonexistent_student_raises(self) -> None:
        with self.assertRaises(StudentNotFoundError):
            self.mgr.set_grade("99", "语文", 85)

    def test_set_grade_invalid_score_raises(self) -> None:
        with self.assertRaises(ValidationError):
            self.mgr.set_grade("1", "语文", 150)

    def test_set_multiple_grades(self) -> None:
        self.mgr.set_grade("1", "语文", 90)
        self.mgr.set_grade("1", "数学", 80)
        self.mgr.set_grade("1", "英语", 70)
        s = self.mgr.get_student("1")
        self.assertEqual(s.course_count, 3)

    def test_overwrite_grade(self) -> None:
        self.mgr.set_grade("1", "数学", 80)
        self.mgr.set_grade("1", "数学", 95)
        s = self.mgr.get_student("1")
        self.assertEqual(s.grades["数学"], 95)

    def test_boundary_scores(self) -> None:
        self.mgr.set_grade("1", "零分", 0)
        self.mgr.set_grade("1", "满分", 100)
        s = self.mgr.get_student("1")
        self.assertEqual(s.grades["零分"], 0)
        self.assertEqual(s.grades["满分"], 100)


class TestGetGrades(unittest.TestCase):
    """验证 get_grades 方法。"""

    def setUp(self) -> None:
        self.mgr = StudentManager()
        self.mgr.add_student("张三")

    def test_empty_grades(self) -> None:
        grades = self.mgr.get_grades("1")
        self.assertEqual(grades, {})

    def test_with_grades(self) -> None:
        self.mgr.set_grade("1", "数学", 90)
        grades = self.mgr.get_grades("1")
        self.assertEqual(grades, {"数学": 90})

    def test_nonexistent_student_raises(self) -> None:
        with self.assertRaises(StudentNotFoundError):
            self.mgr.get_grades("99")


class TestStats(unittest.TestCase):
    """验证统计功能。"""

    def setUp(self) -> None:
        self.mgr = StudentManager()
        self.mgr.add_student("张三")
        self.mgr.add_student("李四")
        self.mgr.set_grade("1", "语文", 90)
        self.mgr.set_grade("1", "数学", 80)
        self.mgr.set_grade("2", "语文", 70)

    def test_stats_count(self) -> None:
        stats = self.mgr.get_stats()
        self.assertEqual(len(stats), 2)

    def test_stats_values(self) -> None:
        stats = self.mgr.get_stats()
        zs = next(s for s in stats if s["name"] == "张三")
        self.assertEqual(zs["total"], 170.0)
        self.assertEqual(zs["avg"], 85.0)
        self.assertEqual(zs["course_count"], 2)

    def test_stats_empty_manager(self) -> None:
        mgr = StudentManager()
        self.assertEqual(mgr.get_stats(), [])

    def test_stats_typed_dict_keys(self) -> None:
        stats = self.mgr.get_stats()
        for s in stats:
            self.assertIn("student_id", s)
            self.assertIn("name", s)
            self.assertIn("total", s)
            self.assertIn("avg", s)
            self.assertIn("course_count", s)


class TestRanking(unittest.TestCase):
    """验证排名功能。"""

    def setUp(self) -> None:
        self.mgr = StudentManager()
        self.mgr.add_student("第一名")
        self.mgr.add_student("第二名")
        self.mgr.add_student("第三名")
        self.mgr.set_grade("1", "数学", 100)
        self.mgr.set_grade("2", "数学", 80)
        # 第三名无成绩

    def test_ranking_order(self) -> None:
        ranking = self.mgr.get_ranking()
        self.assertEqual(ranking[0]["name"], "第一名")
        self.assertEqual(ranking[1]["name"], "第二名")
        self.assertEqual(ranking[2]["name"], "第三名")
        self.assertEqual(ranking[0]["total"], 100.0)
        self.assertEqual(ranking[1]["total"], 80.0)
        self.assertEqual(ranking[2]["total"], 0.0)

    def test_ranking_empty(self) -> None:
        mgr = StudentManager()
        self.assertEqual(mgr.get_ranking(), [])

    def test_ranking_same_score(self) -> None:
        """同分情况——不要求特定顺序，但两条都在"""
        mgr = StudentManager()
        mgr.add_student("A")
        mgr.add_student("B")
        mgr.set_grade("1", "数学", 50)
        mgr.set_grade("2", "数学", 50)
        ranking = mgr.get_ranking()
        self.assertEqual(len(ranking), 2)
        totals = [r["total"] for r in ranking]
        self.assertEqual(totals, [50.0, 50.0])


class TestGetStudentRank(unittest.TestCase):
    """验证 get_student_rank 方法。"""

    def setUp(self) -> None:
        self.mgr = StudentManager()
        self.mgr.add_student("A")
        self.mgr.add_student("B")
        self.mgr.set_grade("1", "数学", 90)
        self.mgr.set_grade("2", "数学", 60)

    def test_rank_first(self) -> None:
        self.assertEqual(self.mgr.get_student_rank("1"), 1)

    def test_rank_second(self) -> None:
        self.assertEqual(self.mgr.get_student_rank("2"), 2)

    def test_nonexistent_raises(self) -> None:
        with self.assertRaises(StudentNotFoundError):
            self.mgr.get_student_rank("99")


class TestLoadData(unittest.TestCase):
    """验证批量加载数据。"""

    def test_load_valid_data(self) -> None:
        mgr = StudentManager()
        data = {
            "1": {"name": "张三", "grades": {"语文": 88}},
            "2": {"name": "李四", "grades": {}},
        }
        mgr.load_data(data, 2)
        self.assertEqual(mgr.student_count, 2)
        self.assertEqual(mgr.counter, 2)
        self.assertEqual(mgr.get_student("1").name, "张三")
        self.assertEqual(mgr.get_student("2").name, "李四")

    def test_load_replaces_existing(self) -> None:
        mgr = StudentManager()
        mgr.add_student("旧数据")
        data = {"5": {"name": "新数据", "grades": {}}}
        mgr.load_data(data, 5)
        self.assertEqual(mgr.student_count, 1)
        self.assertEqual(mgr.get_student("5").name, "新数据")

    def test_load_invalid_data_type_raises(self) -> None:
        mgr = StudentManager()
        with self.assertRaises(DataCorruptionError):
            mgr.load_data("not a dict", 0)  # type: ignore

    def test_load_invalid_student_data_raises(self) -> None:
        mgr = StudentManager()
        with self.assertRaises(DataCorruptionError):
            mgr.load_data({"1": "not a dict"}, 0)  # type: ignore

    def test_load_missing_name_raises(self) -> None:
        mgr = StudentManager()
        with self.assertRaises(DataCorruptionError):
            mgr.load_data({"1": {"grades": {}}}, 0)


class TestToDict(unittest.TestCase):
    """验证数据导出。"""

    def test_empty_manager(self) -> None:
        mgr = StudentManager()
        self.assertEqual(mgr.to_dict(), {})

    def test_with_students(self) -> None:
        mgr = StudentManager()
        mgr.add_student("张三")
        mgr.set_grade("1", "语文", 90)
        data = mgr.to_dict()
        self.assertIn("1", data)
        self.assertEqual(data["1"]["name"], "张三")
        self.assertEqual(data["1"]["grades"], {"语文": 90})

    def test_roundtrip(self) -> None:
        """to_dict → load_data 应保持数据一致。"""
        mgr = StudentManager()
        mgr.add_student("张三")
        mgr.add_student("李四")
        mgr.set_grade("1", "语文", 90)
        mgr.set_grade("2", "数学", 80)

        data = mgr.to_dict()
        counter = mgr.counter

        mgr2 = StudentManager()
        mgr2.load_data(data, counter)
        self.assertEqual(mgr2.student_count, mgr.student_count)
        self.assertEqual(mgr2.counter, mgr.counter)
        for sid in ("1", "2"):
            self.assertEqual(
                mgr2.get_student(sid).name,
                mgr.get_student(sid).name,
            )
            self.assertEqual(
                mgr2.get_student(sid).grades,
                mgr.get_student(sid).grades,
            )


if __name__ == "__main__":
    unittest.main()
