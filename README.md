# chengyu-teaching-video

用于 Codex 的成语教学视频插件。它可以根据两至四个成语、拼音、褒贬属性、释义和侧重点，制作 1080×1920、6 秒、15 fps 的竖版成语辨析动画，并按照内置参考素材统一为中国老课本儿童教育绘本风格。

## 仓库结构

```text
.agents/plugins/marketplace.json
plugins/chengyu-teaching-video/
├── plugin.json
├── .codex-plugin/plugin.json
├── requirements.txt
└── skills/chengyu-teaching-video/
    ├── SKILL.md
    ├── agents/
    ├── assets/
    ├── references/
    └── scripts/
```

## 运行环境

- Python 3.10 或更高版本
- FFmpeg，并已加入系统 `PATH`
- Python 依赖：`numpy`、`opencv-python`、`Pillow`
- Windows 默认使用宋体和微软雅黑；Linux/macOS 建议安装 Noto CJK 字体

安装 Python 依赖：

```powershell
python -m pip install -r plugins/chengyu-teaching-video/requirements.txt
```

## 在 Codex 中安装

仓库推送到 GitHub 后，使用仓库地址添加市场：

```powershell
codex plugin marketplace add https://github.com/<你的GitHub用户名>/chengyu-teaching-video.git
```

然后在 Codex 的插件目录中安装 `chengyu-teaching-video`。安装完成后可这样调用：

```text
使用 $chengyu-teaching-video 制作一组竖版成语教学动画。
```

## 输出说明

默认写入用户指定的输出目录；未指定时写入当前工作区的 `output/`。具体输入字段与排版规则见 skill 内的 `references/`。

