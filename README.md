# jianying_drafts
由Ai制作的剪映草稿导入导出工具
# 剪映草稿导入/导出工具

使用 Python 标准库管理剪映专业版草稿，提供简易桌面 GUI 和命令行。默认草稿目录为：

`%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft`

导出的 ZIP 保留整个草稿文件夹及素材相对路径；支持包含 `draft_content.json` 或 `draft_info.json` 的草稿。导入时会在草稿目录内暂存并检查压缩包路径，遇到同名草稿会自动加上 `(2)`、`(3)` 等后缀，不覆盖已有内容。

## 图形界面

可直接运行 `dist\JianyingDraftTool.exe`，无需在目标电脑安装 Python。也可以双击 `启动工具.bat`；没有 EXE 时启动脚本会尝试使用本机 Python：

```powershell
python .\jianying_gui.py
```

窗口中可以选择草稿目录并刷新列表。草稿列表支持 Ctrl/Shift 多选；导出时选择目标文件夹，每个草稿各生成一个 ZIP。导入文件框也支持一次多选多个 ZIP。

EXE 已嵌入管理员权限清单，Windows 启动时会显示 UAC 权限确认窗口。

## 命令行使用

无需安装第三方依赖。Windows 上可以在此目录打开 PowerShell：

```powershell
python .\jianying_drafts.py list
python .\jianying_drafts.py export "草稿文件夹名" "D:\备份\我的草稿.zip"
python .\jianying_drafts.py import "D:\备份\我的草稿.zip"
python .\jianying_drafts.py import "D:\备份\我的草稿.zip" --name "新名称"
```

草稿目录位置不同时，可以传入 `--draft-dir`（必须放在子命令前）：

```powershell
python .\jianying_drafts.py --draft-dir "E:\JianyingDrafts" list
```

导出目标 ZIP 已存在时，工具会停止并提示，不会覆盖。导入前建议关闭剪映，避免剪映同时读写草稿。
