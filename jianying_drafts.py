#!/usr/bin/env python3
"""Back up and restore Jianying Pro draft folders."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


DRAFT_MARKERS = ("draft_content.json", "draft_info.json")
META_MARKER = "draft_meta_info.json"
DEFAULT_DRAFT_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "JianyingPro" / "User Data" / "Projects" / "com.lveditor.draft"


class DraftError(Exception):
    """An expected user-facing draft operation error."""


def is_draft_folder(path: Path) -> bool:
    return path.is_dir() and any((path / marker).is_file() for marker in DRAFT_MARKERS)


def find_draft_root(path: Path) -> Path:
    """Find a draft folder, allowing a single wrapper directory in an archive."""
    if is_draft_folder(path):
        return path
    matches = [p for p in path.rglob("*") if p.is_dir() and is_draft_folder(p)]
    if len(matches) != 1:
        raise DraftError("压缩包中必须恰好包含一个剪映草稿目录（含 draft_content.json 或 draft_info.json）。")
    return matches[0]


def safe_name(value: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    if not name or name in {".", ".."}:
        raise DraftError("草稿名称无效。")
    return name[:120]


def unique_destination(parent: Path, name: str) -> Path:
    candidate = parent / name
    index = 2
    while candidate.exists():
        candidate = parent / f"{name} ({index})"
        index += 1
    return candidate


def list_drafts(root: Path) -> list[Path]:
    if not root.is_dir():
        raise DraftError(f"草稿目录不存在：{root}")
    return sorted((child for child in root.iterdir() if is_draft_folder(child)), key=lambda p: p.name.casefold())


def export_draft(source: Path, output: Path) -> Path:
    source = source.expanduser().resolve()
    if not is_draft_folder(source):
        raise DraftError(f"不是可识别的剪映草稿目录：{source}")
    output = output.expanduser()
    if output.suffix.lower() != ".zip":
        output = output.with_suffix(".zip")
    output = output.resolve()
    if output.exists():
        raise DraftError(f"导出文件已存在，为防止覆盖已停止：{output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            for item in source.rglob("*"):
                if item.is_file():
                    archive.write(item, Path(source.name) / item.relative_to(source))
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return output


def _safe_zip_target(stage: Path, member: zipfile.ZipInfo) -> Path:
    raw = member.filename.replace("\\", "/")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or any(part in {"..", ""} for part in pure.parts):
        raise DraftError(f"压缩包包含不安全路径：{member.filename}")
    target = (stage / Path(*pure.parts)).resolve()
    if not target.is_relative_to(stage.resolve()):
        raise DraftError(f"压缩包包含越界路径：{member.filename}")
    # Reject Unix symlink entries rather than materializing links during import.
    if (member.external_attr >> 16) & 0o170000 == 0o120000:
        raise DraftError(f"压缩包包含符号链接：{member.filename}")
    return target


def import_draft(archive_path: Path, draft_dir: Path, name: str | None = None) -> Path:
    archive_path = archive_path.expanduser().resolve()
    draft_dir = draft_dir.expanduser().resolve()
    if not archive_path.is_file():
        raise DraftError(f"找不到压缩包：{archive_path}")
    draft_dir.mkdir(parents=True, exist_ok=True)
    stage_parent = Path(tempfile.mkdtemp(prefix=".jianying-import-", dir=draft_dir))
    try:
        stage = stage_parent / "contents"
        stage.mkdir()
        try:
            with zipfile.ZipFile(archive_path) as archive:
                for member in archive.infolist():
                    target = _safe_zip_target(stage, member)
                    if member.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(member) as src, target.open("wb") as dst:
                            shutil.copyfileobj(src, dst)
        except zipfile.BadZipFile as exc:
            raise DraftError("文件不是有效的 ZIP 压缩包。") from exc
        draft_source = find_draft_root(stage)
        project_name = safe_name(name or draft_source.name)
        destination = unique_destination(draft_dir, project_name)
        shutil.move(str(draft_source), str(destination))
        return destination
    finally:
        shutil.rmtree(stage_parent, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="剪映专业版草稿导入/导出工具")
    parser.add_argument("--draft-dir", type=Path, default=DEFAULT_DRAFT_DIR,
                        help=f"草稿根目录（默认：{DEFAULT_DRAFT_DIR}）")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="列出草稿")
    export_parser = subparsers.add_parser("export", help="将草稿目录打包为 ZIP")
    export_parser.add_argument("draft", help="草稿名称或草稿文件夹路径")
    export_parser.add_argument("output", type=Path, help="ZIP 输出路径")
    import_parser = subparsers.add_parser("import", help="从 ZIP 导入草稿")
    import_parser.add_argument("archive", type=Path, help="草稿 ZIP 文件")
    import_parser.add_argument("--name", help="导入后的草稿名称")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.draft_dir.expanduser()
    try:
        if args.command == "list":
            drafts = list_drafts(root)
            if not drafts:
                print(f"没有找到草稿：{root}")
            for draft in drafts:
                print(draft.name)
            return 0
        if args.command == "export":
            candidate = Path(args.draft).expanduser()
            source = candidate if candidate.is_dir() else root / args.draft
            output = export_draft(source, args.output)
            print(f"已导出：{output}")
            return 0
        imported = import_draft(args.archive, root, args.name)
        print(f"已导入：{imported}")
        return 0
    except (DraftError, OSError, zipfile.BadZipFile) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
