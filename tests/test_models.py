"""Student 数据模型、常量和枚举的单元测试。"""

import unittest

from student_system.exceptions import ValidationError
from student_system.models import (
    MAX_SCORE,
    MIN_SCORE,
    MenuAction,
    Student,
    validate_name,
    validate_score,
)


class TestConstants(unittest.TestCase):
    """验证系统常量值。"""

    def test_score_bounds(self) -> None:
        self.assertEqual(MIN_SCORE, 0.0)
        self.assertEqual(MAX_SCORE, 100.0)
        self.assertLess(MIN_SCORE, MAX_SCORE)

    def test_default_data_file(self) -> None:
        from student_system.models import DEFAULT_DATA_FILE
        self.assertIsInstance(DEFAULT_DATA_FILE, str)
        self.assertTrue(DEFAULT_DATA_FILE.endswith(".json"))


class TestValidateScore(unittest.TestCase):
    """验证 validate_score 函数。"""

    def test_valid_scores(self) -> None:
        """边界和中间值均应通过。"""
        for score in (0, 0.0, 50, 50.5, 100, 100.0):
            with self.subTest(score=score):
                self.assertEqual(validate_score(score), float(score))

    def test_below_min_raises(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            validate_score(-1)
        self.assertIn("0", str(ctx.exception))
        self.assertEqual(ctx.exception.field, "score")

    def test_above_max_raises(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            validate_score(101)
        self.assertIn("100", str(ctx.exception))

    def test_infinity_raises(self) -> None:
        with self.assertRaises(ValidationError):
            validate_score(float("inf"))

    def test_nan_raises(self) -> None:
        import math
        with self.assertRaises(ValidationError):
            validate_score(float("nan"))


class TestValidateName(unittest.TestCase):
    """验证 validate_name 函数。"""

    def test_valid_names(self) -> None:
        for name in ("张三", "Alice", "A B", "  李四  "):
            with self.subTest(name=name):
                result = validate_name(name)
                self.assertIsInstance(result, str)
                self.assertTrue(len(result) > 0)
                # 去除空白后不应有前后空白
                self.assertEqual(result, name.strip())

    def test_empty_name_raises(self) -> None:
        for name in ("", "   ", "\t", "\n"):
            with self.subTest(name=repr(name)):
                with self.assertRaises(ValidationError) as ctx:
                    validate_name(name)
                self.assertEqual(ctx.exception.field, "name")


class TestStudentCreation(unittest.TestCase):
    """验证 Student 对象的创建和验证。"""

    def test_create_student_basic(self) -> None:
        s = Student("1", "张三")
        self.assertEqual(s.student_id, "1")
        self.assertEqual(s.name, "张三")
        self.assertEqual(s.grades, {})

    def test_create_student_with_grades(self) -> None:
        s = Student("2", "李四", {"语文": 85.0})
        self.assertEqual(s.grades, {"语文": 85.0})

    def test_empty_name_raises_in_post_init(self) -> None:
        with self.assertRaises(ValidationError):
            Student("1", "")

    def test_whitespace_name_stripped(self) -> None:
        s = Student("1", "  张三  ")
        self.assertEqual(s.name, "张三")

    def test_invalid_grade_raises_in_post_init(self) -> None:
        with self.assertRaises(ValidationError):
            Student("1", "张三", {"语文": 999})


class TestStudentProperties(unittest.TestCase):
    """验证 Student 的计算属性。"""

    def setUp(self) -> None:
        self.student = Student("1", "测试")

    def test_empty_grades(self) -> None:
        self.assertEqual(self.student.total_score, 0.0)
        self.assertEqual(self.student.average_score, 0.0)
        self.assertEqual(self.student.course_count, 0)

    def test_single_grade(self) -> None:
        self.student.set_grade("数学", 80)
        self.assertEqual(self.student.total_score, 80.0)
        self.assertEqual(self.student.average_score, 80.0)
        self.assertEqual(self.student.course_count, 1)

    def test_multiple_grades(self) -> None:
        self.student.set_grade("语文", 90)
        self.student.set_grade("数学", 80)
        self.student.set_grade("英语", 70)
        self.assertEqual(self.student.total_score, 240.0)
        self.assertEqual(self.student.average_score, 80.0)
        self.assertEqual(self.student.course_count, 3)

    def test_grade_overwrite(self) -> None:
        self.student.set_grade("数学", 80)
        self.student.set_grade("数学", 95)
        self.assertEqual(self.student.total_score, 95.0)
        self.assertEqual(self.student.course_count, 1)

    def test_zero_score(self) -> None:
        self.student.set_grade("数学", 0)
        self.assertEqual(self.student.total_score, 0.0)
        self.assertEqual(self.student.average_score, 0.0)


class TestStudentSetGrade(unittest.TestCase):
    """验证 set_grade 方法。"""

    def setUp(self) -> None:
        self.student = Student("1", "测试")

    def test_set_valid_grade(self) -> None:
        self.student.set_grade("英语", 88.5)
        self.assertIn("英语", self.student.grades)
        self.assertEqual(self.student.grades["英语"], 88.5)

    def test_empty_course_raises(self) -> None:
        with self.assertRaises(ValidationError):
            self.student.set_grade("", 80)

    def test_whitespace_course_raises(self) -> None:
        with self.assertRaises(ValidationError):
            self.student.set_grade("   ", 80)

    def test_invalid_score_raises(self) -> None:
        with self.assertRaises(ValidationError):
            self.student.set_grade("数学", -1)

    def test_boundary_scores(self) -> None:
        """边界值 0 和 100 应通过。"""
        self.student.set_grade("数学", 0)
        self.student.set_grade("语文", 100)
        self.assertEqual(self.student.grades["数学"], 0.0)
        self.assertEqual(self.student.grades["语文"], 100.0)


class TestStudentRemoveGrade(unittest.TestCase):
    """验证 remove_grade 方法。"""

    def setUp(self) -> None:
        self.student = Student("1", "测试", {"语文": 80, "数学": 90})

    def test_remove_existing_grade(self) -> None:
        self.assertTrue(self.student.remove_grade("语文"))
        self.assertNotIn("语文", self.student.grades)
        self.assertEqual(self.student.course_count, 1)

    def test_remove_nonexistent_grade(self) -> None:
        self.assertFalse(self.student.remove_grade("物理"))
        self.assertEqual(self.student.course_count, 2)


class TestStudentSerialization(unittest.TestCase):
    """验证 Student 的序列化和反序列化。"""

    def test_to_dict_basic(self) -> None:
        s = Student("1", "张三")
        self.assertEqual(s.to_dict(), {"name": "张三", "grades": {}})

    def test_to_dict_with_grades(self) -> None:
        s = Student("1", "张三", {"语文": 90, "数学": 80})
        d = s.to_dict()
        self.assertEqual(d["name"], "张三")
        self.assertEqual(d["grades"], {"语文": 90, "数学": 80})

    def test_to_dict_returns_copy(self) -> None:
        """to_dict 返回的 grades 不应影响原对象。"""
        s = Student("1", "张三", {"语文": 90})
        d = s.to_dict()
        d["grades"]["语文"] = 0
        self.assertEqual(s.grades["语文"], 90)

    def test_from_dict_basic(self) -> None:
        s = Student.from_dict("5", {"name": "王五"})
        self.assertEqual(s.student_id, "5")
        self.assertEqual(s.name, "王五")
        self.assertEqual(s.grades, {})

    def test_from_dict_with_grades(self) -> None:
        s = Student.from_dict("5", {"name": "王五", "grades": {"物理": 88}})
        self.assertEqual(s.grades["物理"], 88)

    def test_from_dict_missing_name_raises(self) -> None:
        with self.assertRaises(ValidationError):
            Student.from_dict("1", {})

    def test_from_dict_invalid_grades_type_raises(self) -> None:
        with self.assertRaises(ValidationError):
            Student.from_dict("1", {"name": "张三", "grades": "invalid"})

    def test_roundtrip(self) -> None:
        """to_dict → from_dict 应保持数据一致。"""
        original = Student("10", "赵六", {"化学": 76, "生物": 82})
        restored = Student.from_dict("10", original.to_dict())
        self.assertEqual(restored.name, original.name)
        self.assertEqual(restored.grades, original.grades)
        self.assertEqual(restored.total_score, original.total_score)


class TestStudentRepr(unittest.TestCase):
    """验证 __repr__ 输出。"""

    def test_repr_basic(self) -> None:
        s = Student("1", "张三")
        r = repr(s)
        self.assertIn("Student", r)
        self.assertIn("1", r)
        self.assertIn("张三", r)

    def test_repr_with_grades(self) -> None:
        s = Student("2", "李四", {"数学": 85})
        r = repr(s)
        self.assertIn("course_count=1", r)


class TestMenuActionEnum(unittest.TestCase):
    """验证 MenuAction 枚举。"""

    def test_all_nine_actions_exist(self) -> None:
        self.assertEqual(len(list(MenuAction)), 9)

    def test_keys_are_sequential(self) -> None:
        keys = [a.key for a in MenuAction]
        self.assertEqual(keys, [str(i) for i in range(1, 10)])

    def test_from_key_valid(self) -> None:
        for i in range(1, 10):
            with self.subTest(key=str(i)):
                action = MenuAction.from_key(str(i))
                self.assertIsNotNone(action)
                self.assertEqual(action.key, str(i))

    def test_from_key_invalid(self) -> None:
        for key in ("0", "10", "a", "", "abc"):
            with self.subTest(key=key):
                self.assertIsNone(MenuAction.from_key(key))

    def test_labels_are_non_empty(self) -> None:
        for action in MenuAction:
            with self.subTest(action=action.name):
                self.assertIsInstance(action.label, str)
                self.assertTrue(len(action.label) > 0)

    def test_key_label_consistency(self) -> None:
        """验证每个枚举成员的 key 和 label 配对正确。"""
        expected = {
            "1": "添加学生",
            "2": "删除学生",
            "3": "添加/修改成绩",
            "4": "查看所有学生成绩",
            "5": "查看学生统计（平均分/总分/排名）",
            "6": "按总分排名显示",
            "7": "保存数据到文件",
            "8": "从文件加载数据",
            "9": "退出系统",
        }
        for key, label in expected.items():
            action = MenuAction.from_key(key)
            self.assertEqual(action.label, label)


if __name__ == "__main__":
    unittest.main()
