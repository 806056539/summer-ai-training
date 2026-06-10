"""Storage 持久化模块的单元测试。"""

import json
import os
import tempfile
import unittest

from student_system.exceptions import DataCorruptionError, StorageError
from student_system.storage import Storage


class TestStorageInit(unittest.TestCase):
    """验证 Storage 初始化。"""

    def test_default_filepath(self) -> None:
        storage = Storage()
        self.assertEqual(storage.filepath, "students_data.json")

    def test_custom_filepath(self) -> None:
        storage = Storage("/custom/path/data.json")
        self.assertEqual(storage.filepath, "/custom/path/data.json")


class TestFileExists(unittest.TestCase):
    """验证 file_exists 方法。"""

    def test_file_does_not_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "nonexistent.json")
            storage = Storage(filepath)
            self.assertFalse(storage.file_exists())

    def test_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "existing.json")
            with open(filepath, "w") as f:
                f.write("{}")
            storage = Storage(filepath)
            self.assertTrue(storage.file_exists())


class TestFileSize(unittest.TestCase):
    """验证 file_size 属性。"""

    def test_nonexistent_file(self) -> None:
        storage = Storage("/nonexistent/path.json")
        self.assertIsNone(storage.file_size)

    def test_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.json")
            data = '{"test": "data"}'
            with open(filepath, "w") as f:
                f.write(data)
            storage = Storage(filepath)
            self.assertGreater(storage.file_size, 0)


class TestSave(unittest.TestCase):
    """验证保存操作。"""

    def test_save_basic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "output.json")
            storage = Storage(filepath)
            data = {"1": {"name": "张三", "grades": {"语文": 90}}}
            storage.save(data)
            self.assertTrue(os.path.exists(filepath))

    def test_save_and_verify_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "output.json")
            storage = Storage(filepath)
            data = {"1": {"name": "张三", "grades": {"语文": 90}}}
            storage.save(data)

            with open(filepath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(loaded, data)

    def test_save_overwrites_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "output.json")
            # 创建已有文件
            with open(filepath, "w") as f:
                f.write('{"old": "data"}')

            storage = Storage(filepath)
            data = {"new": "data"}
            storage.save({"new": "data"})

            with open(filepath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # 注意: save 期望的格式是 dict[str, dict], 这里只是一个占位
            self.assertIn("new", loaded)

    def test_save_empty_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "empty.json")
            storage = Storage(filepath)
            storage.save({})
            self.assertTrue(os.path.exists(filepath))

    def test_save_unicode_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "unicode.json")
            storage = Storage(filepath)
            data = {"1": {"name": "张三🎓", "grades": {"语文": 95}}}
            storage.save(data)

            with open(filepath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(loaded["1"]["name"], "张三🎓")


class TestLoad(unittest.TestCase):
    """验证加载操作。"""

    def test_load_valid_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "input.json")
            data = {"1": {"name": "张三", "grades": {"语文": 90}}}
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f)

            storage = Storage(filepath)
            loaded, counter = storage.load()
            self.assertEqual(loaded, data)
            self.assertEqual(counter, 1)

    def test_load_nonexistent_raises(self) -> None:
        storage = Storage("/nonexistent/file.json")
        with self.assertRaises(StorageError):
            storage.load()

    def test_load_invalid_json_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "bad.json")
            with open(filepath, "w") as f:
                f.write("this is not json{")

            storage = Storage(filepath)
            with self.assertRaises(DataCorruptionError):
                storage.load()

    def test_load_not_a_dict_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "array.json")
            with open(filepath, "w") as f:
                json.dump([1, 2, 3], f)

            storage = Storage(filepath)
            with self.assertRaises(DataCorruptionError):
                storage.load()

    def test_load_missing_name_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "noname.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"1": {"grades": {}}}, f)

            storage = Storage(filepath)
            with self.assertRaises(DataCorruptionError):
                storage.load()

    def test_load_non_dict_student_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "badtype.json")
            with open(filepath, "w") as f:
                json.dump({"1": "just a string"}, f)

            storage = Storage(filepath)
            with self.assertRaises(DataCorruptionError):
                storage.load()

    def test_load_counter_with_mixed_ids(self) -> None:
        """测试计算包含非数字学号的 counter。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "mixed.json")
            data = {
                "1": {"name": "A", "grades": {}},
                "abc": {"name": "B", "grades": {}},  # 非数字学号
                "3": {"name": "C", "grades": {}},
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f)

            storage = Storage(filepath)
            loaded, counter = storage.load()
            self.assertEqual(counter, 3)  # max(1, 3) = 3


class TestSaveLoadRoundtrip(unittest.TestCase):
    """验证保存→加载的完整往返流程。"""

    def test_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "roundtrip.json")
            storage = Storage(filepath)

            original = {
                "1": {"name": "张三", "grades": {"语文": 90, "数学": 85}},
                "2": {"name": "李四", "grades": {}},
                "3": {"name": "王五", "grades": {"英语": 78.5}},
            }
            storage.save(original)
            loaded, counter = storage.load()
            self.assertEqual(loaded, original)
            self.assertEqual(counter, 3)

    def test_empty_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "empty_rt.json")
            storage = Storage(filepath)
            storage.save({})
            loaded, counter = storage.load()
            self.assertEqual(loaded, {})
            self.assertEqual(counter, 0)


if __name__ == "__main__":
    unittest.main()
