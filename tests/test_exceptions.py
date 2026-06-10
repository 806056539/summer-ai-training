"""自定义异常类的单元测试。"""

import unittest

from student_system.exceptions import (
    DataCorruptionError,
    DuplicateStudentError,
    StorageError,
    StudentNotFoundError,
    StudentSystemError,
    ValidationError,
)


class TestExceptionHierarchy(unittest.TestCase):
    """验证异常类的继承关系和构造函数。"""

    def test_base_exception(self) -> None:
        """StudentSystemError 应是所有自定义异常的基类。"""
        self.assertTrue(issubclass(StudentSystemError, Exception))

    def test_validation_error_is_system_error(self) -> None:
        """ValidationError 应继承 StudentSystemError。"""
        self.assertTrue(issubclass(ValidationError, StudentSystemError))

    def test_student_not_found_is_system_error(self) -> None:
        """StudentNotFoundError 应继承 StudentSystemError。"""
        self.assertTrue(issubclass(StudentNotFoundError, StudentSystemError))

    def test_duplicate_student_is_system_error(self) -> None:
        """DuplicateStudentError 应继承 StudentSystemError。"""
        self.assertTrue(issubclass(DuplicateStudentError, StudentSystemError))

    def test_storage_error_is_system_error(self) -> None:
        """StorageError 应继承 StudentSystemError。"""
        self.assertTrue(issubclass(StorageError, StudentSystemError))

    def test_data_corruption_is_storage_error(self) -> None:
        """DataCorruptionError 应继承 StorageError。"""
        self.assertTrue(issubclass(DataCorruptionError, StorageError))

    def test_catch_all_system_errors(self) -> None:
        """所有自定义异常都应被 StudentSystemError 捕获。"""
        errors = [
            ValidationError("测试"),
            StudentNotFoundError("99"),
            DuplicateStudentError("张三", "1"),
            StorageError("文件错误"),
            DataCorruptionError("test.json"),
        ]
        for err in errors:
            with self.subTest(error_type=type(err).__name__):
                self.assertIsInstance(err, StudentSystemError)

    def test_validation_error_fields(self) -> None:
        """ValidationError 应正确设置 message 和 field。"""
        e = ValidationError("姓名不能为空", field="name")
        self.assertEqual(str(e), "姓名不能为空")
        self.assertEqual(e.field, "name")

        e2 = ValidationError("无效值")
        self.assertIsNone(e2.field)

    def test_student_not_found_error(self) -> None:
        """StudentNotFoundError 应包含学号信息。"""
        e = StudentNotFoundError("42")
        self.assertEqual(e.student_id, "42")
        self.assertIn("42", str(e))

    def test_duplicate_student_error(self) -> None:
        """DuplicateStudentError 应包含姓名和已存在学号。"""
        e = DuplicateStudentError("张三", "5")
        self.assertEqual(e.name, "张三")
        self.assertEqual(e.existing_id, "5")
        self.assertIn("张三", str(e))
        self.assertIn("5", str(e))

    def test_storage_error_fields(self) -> None:
        """StorageError 应包含文件路径。"""
        e = StorageError("保存失败", filepath="/tmp/test.json")
        self.assertEqual(e.filepath, "/tmp/test.json")

        e2 = StorageError("保存失败")
        self.assertIsNone(e2.filepath)

    def test_data_corruption_error_detail(self) -> None:
        """DataCorruptionError 应包含详细信息和文件路径。"""
        e = DataCorruptionError("data.json", "缺少 name 字段")
        self.assertEqual(e.filepath, "data.json")
        self.assertEqual(e.detail, "缺少 name 字段")
        self.assertIn("data.json", str(e))
        self.assertIn("缺少 name 字段", str(e))


if __name__ == "__main__":
    unittest.main()
