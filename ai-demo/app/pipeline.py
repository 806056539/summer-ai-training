"""Hermes → Claude Code 自动修复流水线。

运行静态检查（ruff + mypy），发现错误后调用 Claude Code 自动生成修复，
应用到源文件，循环直到全部通过或达到最大轮次。

Examples:
    >>> python app/pipeline.py          # 默认最多 3 轮
    >>> python app/pipeline.py --max 5  # 自定义最大轮次
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ----------------------------------------------------------
# 配置
# ----------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_ROOT / "app"
CLAUDE_TIMEOUT = 600  # Claude Code 调用超时（秒）
DEFAULT_MAX_ROUNDS = 3

# 错误行匹配模式
# ruff 格式 → app/main.py:25:12: F401 ...
# mypy 格式 → app/pipeline.py:2: error: ...
_ERROR_FILE_PATTERN = re.compile(r"^(app[/\\]\S+?\.py):", re.M)


# ============================================================
# 静态检查
# ============================================================


def run_hermes() -> tuple[bool, str]:
    """运行 Hermes 静态检查（ruff + mypy）。

    直接调用各工具而非通过 bash 脚本，避免 WSL 编码问题。

    Returns:
        (passed, output): passed 为 True 表示全部通过,
            output 包含所有检查输出的合并文本。
    """
    all_output: list[str] = []
    all_passed = True

    # --- ruff ---
    ruff_passed, ruff_output = _run_check(
        ["ruff", "check", str(APP_DIR)], "ruff",
    )
    all_output.append(ruff_output)
    all_passed &= ruff_passed

    # --- mypy ---
    mypy_passed, mypy_output = _run_check(
        ["mypy", str(APP_DIR)], "mypy",
    )
    all_output.append(mypy_output)
    all_passed &= mypy_passed

    return all_passed, "\n".join(all_output)


def _run_check(cmd: list[str], label: str) -> tuple[bool, str]:
    """执行单个检查命令并返回结果。

    Args:
        cmd: 要执行的命令及其参数。
        label: 检查工具名称（用于输出标记）。

    Returns:
        (passed, output): passed 为 True 表示无错误。
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            errors="replace",
            cwd=str(PROJECT_ROOT),
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output
    except FileNotFoundError:
        skip_msg = f"[SKIP] {label} not installed"
        print(f"  {skip_msg}")
        return True, skip_msg
    except Exception as e:
        err_msg = f"[ERROR] {label} failed: {e}"
        print(f"  {err_msg}")
        return False, err_msg


# ============================================================
# 文件收集
# ============================================================


def _extract_error_files(output: str) -> set[str]:
    """从静态检查输出中提取有错误的文件路径。"""
    raw = _ERROR_FILE_PATTERN.findall(output)
    return {_normalize_path(p) for p in raw}


def _read_files(filepaths: set[str]) -> str:
    """读取指定文件内容，拼接为带标记的文本块。"""
    blocks: list[str] = []
    for fp in sorted(filepaths):
        full_path = PROJECT_ROOT / fp
        if full_path.is_file():
            content = full_path.read_text(encoding="utf-8")
            blocks.append(f"\n=== {fp} ===\n{content}")
    return "\n".join(blocks)


def _read_error_context(errors: str, filepaths: set[str]) -> str:
    """只提取错误行附近的上下文（而非完整文件）。

    Args:
        errors: Hermes 错误输出。
        filepaths: 要读取的文件路径。

    Returns:
        文件错误行及上下文的文本。
    """
    parts: list[str] = []
    for fp in sorted(filepaths):
        full_path = PROJECT_ROOT / fp
        if not full_path.is_file():
            continue
        lines = full_path.read_text(encoding="utf-8").splitlines()
        # 提取该文件的错误行号
        line_nums: set[int] = set()
        escaped = re.escape(fp)
        line_pattern = re.compile(
            escaped + r":(\d+)", re.IGNORECASE,
        )
        for m in line_pattern.finditer(errors):
            line_nums.add(int(m.group(1)))

        if not line_nums:
            # 回退：包含整个文件
            parts.append(f"\n=== {fp} ===\n" + "\n".join(lines))
            continue

        # 包含错误行 ± 3 行上下文
        min_line = max(1, min(line_nums) - 3)
        max_line = min(len(lines), max(line_nums) + 3)
        context = []
        for i in range(min_line, max_line + 1):
            marker = ">>>" if i in line_nums else "   "
            context.append(f"{marker} {i}: {lines[i - 1]}")
        parts.append(
            f"\n=== {fp} (lines {min_line}-{max_line}) ===\n"
            + "\n".join(context)
        )

    return "\n".join(parts)


# ============================================================
# Claude Code 修复
# ============================================================


def _build_fix_prompt(errors: str, file_contents: str) -> str:
    """构建发送给 Claude Code 的修复提示词。"""
    return (
        "Fix these errors. Output the corrected file(s) like this:\n\n"
        "===FILE: app/path/to/file.py===\n"
        "[full corrected file content here]\n"
        "===END===\n\n"
        "RULES:\n"
        "- Output ===FILE: / ===END=== blocks ONLY.\n"
        "- No other text.\n\n"
        f"{errors}\n\n"
        f"{file_contents}"
    )


def _find_claude() -> str | None:
    """查找 claude CLI 可执行文件路径。"""
    claude_path = shutil.which("claude")
    if claude_path is None:
        candidates = [
            Path.home() / ".local" / "bin" / "claude",
            Path("/usr/local/bin/claude"),
            Path("/opt/homebrew/bin/claude"),
        ]
        for p in candidates:
            if p.is_file():
                return str(p)
    return claude_path


def call_claude_fix(errors: str) -> str | None:
    """调用 Claude Code 获取修复方案。

    Args:
        errors: Hermes 输出的错误文本。

    Returns:
        Claude 的响应文本，调用失败返回 None。
    """
    claude_bin = _find_claude()
    if claude_bin is None:
        print("  [ERROR] 未找到 claude CLI，请确认已安装 Claude Code")
        return None

    error_files = _extract_error_files(errors)
    if not error_files:
        preview = errors.strip()[-400:]
        print("  [INFO] 未能从输出中解析出错误文件路径")
        print(f"  [DEBUG] 错误输出尾部:\n{preview}")
        return None

    file_contents = _read_error_context(errors, error_files)
    prompt = _build_fix_prompt(errors, file_contents)

    print(f"  → 正在调用 Claude Code 修复 {len(error_files)} 个文件...")

    try:
        result = subprocess.run(
            [
                claude_bin, "-p", prompt,
                "--output-format", "text",
                "--dangerously-skip-permissions",
                "--system-prompt",
                (
                    "You are a code fixer. "
                    "Output ONLY ===FILE: / ===END=== blocks. "
                    "No explanations. No markdown outside blocks."
                ),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=CLAUDE_TIMEOUT,
            cwd=str(PROJECT_ROOT),
        )
        return result.stdout or ""
    except subprocess.TimeoutExpired:
        print("  [ERROR] Claude Code 调用超时")
        return None
    except FileNotFoundError:
        print("  [ERROR] 未找到 claude CLI，请确认已安装 Claude Code")
        return None
    except Exception as e:
        print(f"  [ERROR] Claude Code 调用失败: {e}")
        return None


# ============================================================
# 修复应用
# ============================================================


def _parse_fixes(response: str, allowed_files: set[str]) -> dict[str, str]:
    """从 Claude 响应中解析文件修复。

    支持三种格式:
    1. 结构化: ===FILE: path=== content ===END===
    2. 完整代码块: filepath + ```python ... ```
    3. Diff 片段: - old line / + new line

    只接受 allowed_files 中列出的文件路径，防止意外覆盖。

    Args:
        response: Claude Code 返回的修复文本。
        allowed_files: 允许修复的文件路径集合。

    Returns:
        {filepath: corrected_content} 字典。
    """
    fixes: dict[str, str] = {}

    # 格式 1: 结构化 ===FILE: / ===END===
    block_pattern = re.compile(
        r"===FILE:\s*(.+?)===\s*\n(.*?)===END===", re.DOTALL,
    )
    for match in block_pattern.finditer(response):
        filepath = _normalize_path(match.group(1).strip())
        if filepath not in allowed_files:
            print(f"  [SKIP] 忽略非错误文件: {filepath}")
            continue
        content = _strip_code_fences(match.group(2).strip())
        fixes[filepath] = content

    if fixes:
        return fixes

    # 格式 2: 完整代码块（文件路径 + markdown 代码块）
    for filepath in sorted(allowed_files):
        escaped = re.escape(filepath)
        file_pattern = re.compile(
            escaped + r".*?```(?:python|py)?\s*\n(.*?)```", re.DOTALL,
        )
        found = file_pattern.search(response)
        if found:
            content = found.group(1).strip()
            if content and len(content) > 100:
                fixes[filepath] = content

    if fixes:
        return fixes

    # 格式 3: Diff 片段（Claude 对话式回复的典型格式）
    fixes = _parse_diff_fragments(response, allowed_files)
    return fixes


def _parse_diff_fragments(
    response: str, allowed_files: set[str],
) -> dict[str, str]:
    """从 Claude 对话式回复中解析 diff 片段。

    识别模式:
    ```
    -    def delete_user(self, user_id: int) -> int:
    +    def delete_user(self, user_id: int) -> None:
    ```

    Args:
        response: Claude 的对话式回复。
        allowed_files: 允许修复的文件路径集合。

    Returns:
        {filepath: corrected_content} 字典。
    """
    fixes: dict[str, str] = {}

    # 收集所有 -(minus) / +(plus) 行对
    diff_pairs: list[tuple[str, str]] = []
    current_minus: str | None = None

    for line in response.splitlines():
        # 匹配以 "- " 或 "-" 开头的行（保留后续缩进）
        if re.match(r"^-\s", line):
            current_minus = re.sub(r"^- ?", "", line)
        # 匹配以 "+ " 或 "+" 开头的行
        elif re.match(r"^\+\s", line):
            if current_minus is not None:
                plus_line = re.sub(r"^\+ ?", "", line)
                diff_pairs.append((current_minus, plus_line))
                current_minus = None

    if not diff_pairs:
        return fixes

    # 对每个 allowed_file 应用 diff
    for filepath in sorted(allowed_files):
        full_path = PROJECT_ROOT / filepath
        if not full_path.is_file():
            continue
        content = full_path.read_text(encoding="utf-8")
        modified = content
        applied_count = 0

        for old_line, new_line in diff_pairs:
            if old_line in modified:
                modified = modified.replace(old_line, new_line)
                applied_count += 1

        if applied_count > 0:
            fixes[filepath] = modified
            print(f"  [DIFF] 从对话回复中解析出 {applied_count} 处修改")

    return fixes


def _normalize_path(path: str) -> str:
    """标准化文件路径（正斜杠，去除前缀）。"""
    return path.replace("\\", "/").lstrip("/")


def _strip_code_fences(content: str) -> str:
    """去除 markdown 代码围栏。"""
    content = re.sub(r"^```(?:python|py)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content)
    return content.strip()


def apply_fixes(response: str, allowed_files: set[str]) -> int:
    """解析 Claude 响应并写回源文件。

    Args:
        response: Claude Code 返回的修复文本。
        allowed_files: 允许修复的文件路径集合（安全过滤）。

    Returns:
        成功应用修复的文件数量。
    """
    fixes = _parse_fixes(response, allowed_files)

    if not fixes:
        print("  [WARN] 未找到可解析的修复块")

    applied = 0
    for filepath, content in fixes.items():
        full_path = PROJECT_ROOT / filepath
        if not full_path.exists():
            print(f"  [WARN] 跳过不存在的文件: {filepath}")
            continue
        full_path.write_text(content + "\n", encoding="utf-8")
        print(f"  ✓ 已修复: {filepath}")
        applied += 1

    return applied


# ============================================================
# 自动修复（ruff --fix）
# ============================================================


def _ruff_auto_fix() -> None:
    """运行 ruff --fix 自动修复可修复的问题。"""
    try:
        subprocess.run(
            ["ruff", "check", "--fix", str(APP_DIR)],
            capture_output=True,
            text=True,
            errors="replace",
            cwd=str(PROJECT_ROOT),
        )
        print("  → ruff --fix 已完成")
    except FileNotFoundError:
        print("  [SKIP] ruff 未安装")
    except Exception as e:
        print(f"  [WARN] ruff --fix 失败: {e}")


# ============================================================
# 主循环
# ============================================================


def fix_loop(max_rounds: int = DEFAULT_MAX_ROUNDS) -> bool:
    """Hermes → Claude Code 自动修复主循环。

    Args:
        max_rounds: 最大修复轮次。

    Returns:
        True 表示全部检查通过，False 表示仍有问题。
    """
    for round_num in range(1, max_rounds + 1):
        print(f"\n{'=' * 60}")
        print(f"  Round {round_num}/{max_rounds}")
        print(f"{'=' * 60}")

        # 首轮先尝试 ruff 自动修复
        if round_num == 1:
            _ruff_auto_fix()

        # 运行 Hermes
        passed, output = run_hermes()

        if passed:
            print("\n✅ 所有静态检查已通过！")
            return True

        # 显示错误摘要
        error_summary = _summarize_errors(output)
        print(f"\n❌ Hermes 发现 {error_summary} 个问题")

        if round_num == max_rounds:
            print(f"\n⚠ 已达到最大轮次 ({max_rounds})，仍有未修复的问题：")
            print(output[-1500:])
            return False

        # 调用 Claude Code 修复（只修复 Hermes 报告的文件）
        print("\n→ 调用 Claude Code 自动修复...")
        response = call_claude_fix(output)

        if response is None:
            print("  [ERROR] 无法获取 Claude Code 修复方案，流水线终止")
            return False

        error_files = _extract_error_files(output)
        applied = apply_fixes(response, error_files)

        if applied == 0:
            debug_path = PROJECT_ROOT / "fix_debug_output.txt"
            debug_path.write_text(response, encoding="utf-8")
            print("  [WARN] 未能解析出修复内容，")
            print(f"         原始响应已保存至 {debug_path}")
            print("         请人工检查并修复后重新运行。")
            return False

        print(f"\n  → 已应用 {applied} 个文件的修复，进入下一轮...")

    return False


def _summarize_errors(output: str) -> str:
    """从输出中提取错误计数摘要。"""
    # ruff: "Found N errors."
    # mypy: "Found N errors in M files"
    parts: list[str] = []
    for line in output.splitlines():
        if "Found" in line and "error" in line.lower():
            parts.append(line.strip())
    if parts:
        return " / ".join(parts)
    # 回退：显示错误输出最后 3 行有效内容
    last_lines = [ln.strip() for ln in output.splitlines() if ln.strip()][-3:]
    if last_lines:
        return " / ".join(last_lines)
    return "未知"


# ============================================================
# 入口
# ============================================================


def main() -> None:
    # Windows 控制台默认使用 gbk，重配置为 utf-8 以支持 emoji
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

    parser = argparse.ArgumentParser(
        description="Hermes → Claude Code 自动修复流水线",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=DEFAULT_MAX_ROUNDS,
        help=f"最大修复轮次（默认: {DEFAULT_MAX_ROUNDS}）",
    )
    args = parser.parse_args()

    success = fix_loop(max_rounds=args.max)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
