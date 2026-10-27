#!/usr/bin/env python3
"""Simple Tkinter interface for backing up and restoring Jianying drafts."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from jianying_drafts import DEFAULT_DRAFT_DIR, DraftError, export_draft, import_draft, list_drafts


class JianyingDraftApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("剪映草稿导入 / 导出")
        self.root.geometry("680x440")
        self.root.minsize(560, 360)

        self.draft_dir = tk.StringVar(value=str(DEFAULT_DRAFT_DIR))
        self.status = tk.StringVar(value="请选择草稿，然后导出；也可以导入 ZIP 草稿包。")
        self._build_ui()
        self.refresh_drafts()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="剪映草稿目录").pack(anchor="w")
        path_row = ttk.Frame(container)
        path_row.pack(fill="x", pady=(5, 14))
        ttk.Entry(path_row, textvariable=self.draft_dir).pack(side="left", fill="x", expand=True)
        ttk.Button(path_row, text="浏览…", command=self.choose_draft_dir).pack(side="left", padx=(8, 0))
        ttk.Button(path_row, text="刷新列表", command=self.refresh_drafts).pack(side="left", padx=(8, 0))

        ttk.Label(container, text="草稿列表（按住 Ctrl 或 Shift 可多选）").pack(anchor="w")
        list_frame = ttk.Frame(container)
        list_frame.pack(fill="both", expand=True, pady=(5, 12))
        self.draft_list = tk.Listbox(
            list_frame, height=10, exportselection=False, selectmode=tk.EXTENDED
        )
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.draft_list.yview)
        self.draft_list.configure(yscrollcommand=scrollbar.set)
        self.draft_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.draft_list.bind("<Double-Button-1>", lambda _event: self.export_selected())

        actions = ttk.Frame(container)
        actions.pack(fill="x")
        ttk.Button(actions, text="导出所选草稿…", command=self.export_selected).pack(side="left")
        ttk.Button(actions, text="导入 ZIP 草稿…", command=self.import_archive).pack(side="left", padx=(8, 0))

        ttk.Separator(container).pack(fill="x", pady=(14, 8))
        ttk.Label(container, textvariable=self.status, wraplength=640).pack(anchor="w")

    def choose_draft_dir(self) -> None:
        selected = filedialog.askdirectory(
            title="选择剪映草稿目录",
            initialdir=self.draft_dir.get() or str(Path.home()),
        )
        if selected:
            self.draft_dir.set(selected)
            self.refresh_drafts()

    def refresh_drafts(self) -> None:
        self.draft_list.delete(0, tk.END)
        try:
            drafts = list_drafts(Path(self.draft_dir.get()).expanduser())
            for draft in drafts:
                self.draft_list.insert(tk.END, draft.name)
            self.status.set(f"找到 {len(drafts)} 个草稿。草稿目录：{self.draft_dir.get()}")
        except (DraftError, OSError) as exc:
            self.status.set(str(exc))

    def _run_background(self, operation, success_text: str) -> None:
        self.status.set("正在处理，请稍候…")

        def work() -> None:
            try:
                result = operation()
            except Exception as exc:  # Pass errors to Tk's main thread for display.
                self.root.after(0, lambda error=exc: self._show_error(error))
                return
            self.root.after(0, lambda: self._show_success(success_text, result))

        threading.Thread(target=work, daemon=True).start()

    def _show_error(self, error: Exception) -> None:
        self.status.set(f"操作失败：{error}")
        messagebox.showerror("操作失败", str(error), parent=self.root)

    def _show_success(self, message: str, result: Path | list[Path]) -> None:
        paths = result if isinstance(result, list) else [result]
        summary = "\n".join(str(path) for path in paths)
        self.status.set(f"{message}：{len(paths)} 项完成")
        if message == "导入完成":
            self.refresh_drafts()
            self.status.set(f"导入完成：{len(paths)} 项")
        messagebox.showinfo("完成", f"{message}（{len(paths)} 项）：\n{summary}", parent=self.root)

    def export_selected(self) -> None:
        selection = self.draft_list.curselection()
        if not selection:
            messagebox.showwarning("请选择草稿", "请先在列表中选择要导出的草稿。", parent=self.root)
            return
        names = [self.draft_list.get(index) for index in selection]
        output_dir = filedialog.askdirectory(
            title="选择 ZIP 导出文件夹",
            initialdir=str(Path.home()),
        )
        if not output_dir:
            return
        sources = [Path(self.draft_dir.get()).expanduser() / name for name in names]
        destination = Path(output_dir)

        def export_all() -> list[Path]:
            outputs = [destination / f"{name}.zip" for name in names]
            existing = [path for path in outputs if path.exists()]
            if existing:
                paths = "\n".join(str(path) for path in existing)
                raise DraftError(f"以下 ZIP 已存在，为防止覆盖，本次未导出：\n{paths}")
            return [export_draft(source, output) for source, output in zip(sources, outputs)]

        self._run_background(export_all, "导出完成")

    def import_archive(self) -> None:
        archives = filedialog.askopenfilenames(
            title="选择要导入的草稿 ZIP（可多选）",
            initialdir=str(Path.home()),
            filetypes=[("ZIP 压缩包", "*.zip"), ("所有文件", "*.*")],
        )
        if not archives:
            return
        draft_dir = Path(self.draft_dir.get())
        self._run_background(lambda: [import_draft(Path(archive), draft_dir) for archive in archives], "导入完成")


def main() -> None:
    root = tk.Tk()
    JianyingDraftApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
