"""
学生成绩管理系统 - 重构练习版
功能：管理学生、录入成绩、统计平均分/总分/排名、保存/加载数据
坏味道：重复代码、全局变量、过长函数、魔法数字、差命名、硬编码、缺少异常处理等
"""

import json
import os

# 全局数据存储
all_students = {}
student_counter = 0
data_file_name = "students_data.json"

def show_menu():
    print("\n========== 学生成绩管理系统 ==========")
    print("1. 添加学生")
    print("2. 删除学生")
    print("3. 添加/修改成绩")
    print("4. 查看所有学生成绩")
    print("5. 查看学生统计（平均分/总分/排名）")
    print("6. 按总分排名显示")
    print("7. 保存数据到文件")
    print("8. 从文件加载数据")
    print("9. 退出系统")
    print("=====================================")

def add_student():
    global student_counter
    name = input("请输入学生姓名: ").strip()
    if not name:
        print("姓名不能为空！")
        return
    # 检查是否存在同名（允许重名但提示）
    for sid, info in all_students.items():
        if info["name"] == name:
            print(f"警告：已存在学生 '{name}' (学号 {sid})，是否继续添加？(y/n)")
            if input().lower() != 'y':
                return
            break
    student_counter += 1
    student_id = str(student_counter)
    all_students[student_id] = {"name": name, "grades": {}}
    print(f"成功添加学生 {name}，学号 {student_id}")

def delete_student():
    sid = input("请输入要删除的学生学号: ").strip()
    if sid not in all_students:
        print("学号不存在！")
        return
    confirm = input(f"确认删除学生 {all_students[sid]['name']} (学号{sid})? (y/n): ")
    if confirm.lower() == 'y':
        del all_students[sid]
        print("删除成功！")
    else:
        print("取消删除。")

def add_or_update_grade():
    sid = input("请输入学生学号: ").strip()
    if sid not in all_students:
        print("学号不存在！")
        return
    course = input("请输入课程名称: ").strip()
    if not course:
        print("课程名不能为空")
        return
    try:
        score = float(input("请输入成绩(0-100): "))
        if score < 0 or score > 100:
            print("成绩范围应在0-100之间！")
            return
    except ValueError:
        print("成绩必须是数字！")
        return
    all_students[sid]["grades"][course] = score
    print(f"已为学生 {all_students[sid]['name']} 设置 {course} 成绩: {score}")

def view_all_grades():
    if not all_students:
        print("暂无学生数据。")
        return
    print("\n================ 所有学生成绩表 ================")
    for sid, info in all_students.items():
        print(f"学号: {sid} | 姓名: {info['name']}")
        if not info["grades"]:
            print("  暂无成绩")
        else:
            for course, score in info["grades"].items():
                print(f"  {course}: {score}")
        print("-" * 40)

def calculate_student_stats():
    """为每个学生计算总分和平均分，返回 dict: {sid: {'total':..., 'avg':..., 'name':...}}"""
    stats = {}
    for sid, info in all_students.items():
        grades = info["grades"]
        if not grades:
            total = 0
            avg = 0
        else:
            total = sum(grades.values())
            avg = total / len(grades)
        stats[sid] = {"name": info["name"], "total": total, "avg": avg}
    return stats

def show_student_stats():
    if not all_students:
        print("暂无学生数据。")
        return
    stats = calculate_student_stats()
    print("\n================ 学生统计信息 ================")
    print("学号\t姓名\t总分\t平均分\t课程数")
    for sid, data in stats.items():
        course_count = len(all_students[sid]["grades"])
        print(f"{sid}\t{data['name']}\t{data['total']:.2f}\t{data['avg']:.2f}\t{course_count}")

def show_ranking():
    if not all_students:
        print("暂无学生数据。")
        return
    stats = calculate_student_stats()
    # 按总分降序排序
    sorted_list = sorted(stats.items(), key=lambda x: x[1]['total'], reverse=True)
    print("\n================ 总分排名 ================")
    print("排名\t学号\t姓名\t总分\t平均分")
    for rank, (sid, data) in enumerate(sorted_list, start=1):
        print(f"{rank}\t{sid}\t{data['name']}\t{data['total']:.2f}\t{data['avg']:.2f}")

def save_data_to_file():
    try:
        # 将字典转换为可序列化的格式（成绩中的float没问题）
        with open(data_file_name, 'w', encoding='utf-8') as f:
            json.dump(all_students, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到 {data_file_name}")
    except Exception as e:
        print(f"保存失败: {e}")

def load_data_from_file():
    global all_students, student_counter
    if not os.path.exists(data_file_name):
        print("文件不存在，无法加载。")
        return
    try:
        with open(data_file_name, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        all_students = loaded
        # 重新计算 student_counter
        max_id = 0
        for sid in all_students.keys():
            if sid.isdigit():
                max_id = max(max_id, int(sid))
        student_counter = max_id
        print(f"成功从 {data_file_name} 加载数据，共 {len(all_students)} 名学生。")
    except Exception as e:
        print(f"加载失败: {e}")

def exit_system():
    print("感谢使用，再见！")
    exit(0)

# 主程序 - 这是个典型的“过长函数”，包含了所有菜单逻辑和重复代码
def main():
    # 自动尝试加载已有数据
    if os.path.exists(data_file_name):
        print("发现已有数据文件，是否加载？(y/n)")
        if input().lower() == 'y':
            load_data_from_file()

    while True:
        show_menu()
        choice = input("请选择操作 (1-9): ").strip()
        if choice == '1':
            add_student()
        elif choice == '2':
            delete_student()
        elif choice == '3':
            add_or_update_grade()
        elif choice == '4':
            view_all_grades()
        elif choice == '5':
            show_student_stats()
        elif choice == '6':
            show_ranking()
        elif choice == '7':
            save_data_to_file()
        elif choice == '8':
            load_data_from_file()
        elif choice == '9':
            exit_system()
        else:
            print("无效选择，请输入1-9之间的数字。")

if __name__ == "__main__":
    main()