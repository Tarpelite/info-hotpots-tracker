import sys
from typing import TextIO


class ProgressBar:
    """在终端标准错误输出上更新单行进度条。"""

    def __init__(
        self,
        total: int,
        label: str = "进度",
        width: int = 30,
        stream: TextIO | None = None,
    ) -> None:
        if not isinstance(total, int) or isinstance(total, bool) or total < 0:
            raise ValueError("total 必须是非负整数")
        if not isinstance(width, int) or isinstance(width, bool) or width < 1:
            raise ValueError("width 必须是正整数")

        self.total = total
        self.label = label
        self.width = width
        self.stream = stream if stream is not None else sys.stderr
        self.enabled = total > 0 and self.stream.isatty()
        self.closed = False

        if self.enabled:
            self.update(0)

    def update(self, completed: int) -> None:
        """显示当前完成数量，并在达到总量时换行。"""
        if (
            not isinstance(completed, int)
            or isinstance(completed, bool)
            or completed < 0
            or completed > self.total
        ):
            raise ValueError("completed 必须是 0 到 total 之间的整数")
        if not self.enabled or self.closed:
            return

        filled = self.width * completed // self.total
        percent = 100 * completed // self.total
        bar = "=" * filled + " " * (self.width - filled)
        self.stream.write(
            f"\r{self.label} [{bar}] {percent:3d}% ({completed}/{self.total})"
        )
        self.stream.flush()
        if completed == self.total:
            self.close()

    def close(self) -> None:
        """结束当前进度行；可在异常退出时调用。"""
        if self.enabled and not self.closed:
            self.stream.write("\n")
            self.stream.flush()
            self.closed = True

    def __enter__(self) -> "ProgressBar":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
