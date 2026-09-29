from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


WIDTH, HEIGHT = 1080, 1920
FPS, FRAME_COUNT = 15, 90
LEFT, RIGHT, TOP, ART_WIDTH = 113, 113, 113, 854
IVORY = (249, 250, 245)
INK = (18, 18, 15)
SEPARATOR_WIDTH = 2

LAYOUTS = {
    2: {
        "idiom_size": 65,
        "meta_size": 29,
        "body_max": 38,
        "body_min": 30,
        "body_offset": 80,
        "image_offset": 126,
        "image_height": 700,
        "step": 861,
    },
    3: {
        "idiom_size": 61,
        "meta_size": 25,
        "body_max": 36,
        "body_min": 29,
        "body_offset": 72,
        "image_offset": 126,
        "image_height": 417,
        "step": 566,
    },
    4: {
        "idiom_size": 49,
        "meta_size": 20,
        "body_max": 29,
        "body_min": 24,
        "body_offset": 58,
        "image_offset": 104,
        "image_height": 296,
        "step": 421,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--panel-frames", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def load_job(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items")
    if not isinstance(items, list) or len(items) not in {2, 3, 4}:
        raise ValueError("items 必须包含两至四个成语。")
    for item in items:
        if not str(item.get("idiom", "")).strip():
            raise ValueError("idiom 不能为空。")
        if not str(item.get("pinyin", "")).strip():
            raise ValueError("pinyin 不能为空。")
        if str(item.get("sentiment", "")).strip() not in {"中性", "褒义", "贬义"}:
            raise ValueError("sentiment 只能是中性、褒义或贬义。")
        if not str(item.get("meaning", "")).strip():
            raise ValueError("meaning 不能为空。")
    return data


def safe_stem(text: str) -> str:
    text = re.sub(r'[<>:"/\\|?*]+', "_", text).strip(" .")
    return text or "成语教学视频"


def choose_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def title_font(size: int) -> ImageFont.FreeTypeFont:
    return choose_font(
        [
            r"C:\Windows\Fonts\simsun.ttc",
            "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
        ],
        size,
    )


def meta_font(size: int) -> ImageFont.FreeTypeFont:
    return choose_font(
        [
            r"C:\Windows\Fonts\msyhbd.ttc",
            r"C:\Windows\Fonts\simhei.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/System/Library/Fonts/PingFang.ttc",
        ],
        size,
    )


def body_font(size: int) -> ImageFont.FreeTypeFont:
    return choose_font(
        [
            r"C:\Windows\Fonts\simsun.ttc",
            r"C:\Windows\Fonts\STSONG.TTF",
            r"C:\Windows\Fonts\msyh.ttc",
            "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
        ],
        size,
    )


def tokenize(text: str) -> list[str]:
    return re.findall(r"_{3,}|[A-Za-z0-9]+|.", text, flags=re.S)


def wrap_tokens(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    current = ""
    for token in tokenize(text):
        trial = current + token
        width = draw.textbbox((0, 0), trial, font=font)[2]
        if current and width > max_width:
            lines.append(current)
            current = token
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def fit_body(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_size: int,
    min_size: int,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    for size in range(max_size, min_size - 1, -1):
        font = body_font(size)
        lines = wrap_tokens(draw, text, font, ART_WIDTH)
        if len(lines) == 1:
            return font, lines
    font = body_font(min_size)
    return font, wrap_tokens(draw, text, font, ART_WIDTH)


def text_extent(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    stroke_width: int = 0,
) -> tuple[int, int, tuple[int, int, int, int]]:
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    return bbox[2] - bbox[0], bbox[3] - bbox[1], bbox


def draw_title_row(
    draw: ImageDraw.ImageDraw,
    item: dict,
    y: int,
    idiom_size: int,
    meta_size: int,
) -> None:
    idiom = str(item["idiom"]).strip()
    pinyin = f"（{str(item['pinyin']).strip()}）"
    sentiment = f"【{str(item['sentiment']).strip()}】"
    parts = (
        (idiom, title_font(idiom_size), 1),
        (pinyin, meta_font(meta_size), 0),
        (sentiment, meta_font(meta_size), 0),
    )
    metrics = [text_extent(draw, text, font, stroke) for text, font, stroke in parts]
    total_width = sum(metric[0] for metric in metrics) + 36
    if total_width > ART_WIDTH:
        raise ValueError(
            f"标题行超过{ART_WIDTH}px安全宽度：{idiom}（{item['pinyin']}）【{item['sentiment']}】"
        )
    line_height = max(metric[1] for metric in metrics)
    x = LEFT
    for index, ((text, font, stroke), (width, height, bbox)) in enumerate(zip(parts, metrics)):
        draw_y = y + (line_height - height) / 2 - bbox[1]
        draw.text(
            (x, draw_y),
            text,
            fill=INK,
            font=font,
            stroke_width=stroke,
            stroke_fill=INK,
        )
        x += width
        if index < 2:
            x += 18


def discover_sequence(folder: Path) -> list[Path]:
    if not folder.exists():
        raise FileNotFoundError(f"缺少画面目录：{folder}")
    paths = sorted(
        p
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    if not paths:
        raise FileNotFoundError(f"目录中没有画面文件：{folder}")
    return paths


def sequence_frame(paths: list[Path], frame_index: int) -> Image.Image:
    if len(paths) == 1:
        selected = paths[0]
    else:
        selected_index = int(round(frame_index * (len(paths) - 1) / (FRAME_COUNT - 1)))
        selected = paths[min(selected_index, len(paths) - 1)]
    with Image.open(selected) as image:
        return image.convert("RGB").copy()


def render_frame(job: dict, sequences: list[list[Path]], frame_index: int) -> Image.Image:
    canvas = Image.new("RGB", (WIDTH, HEIGHT), IVORY)
    draw = ImageDraw.Draw(canvas)
    item_count = len(job["items"])
    layout = LAYOUTS[item_count]

    for index, item in enumerate(job["items"]):
        title_y = TOP + index * layout["step"]
        body_y = title_y + layout["body_offset"]
        image_y = title_y + layout["image_offset"]
        image_height = layout["image_height"]

        draw_title_row(
            draw,
            item,
            title_y,
            layout["idiom_size"],
            layout["meta_size"],
        )
        font, lines = fit_body(
            draw,
            str(item["meaning"]),
            layout["body_max"],
            layout["body_min"],
        )
        line_height = font.size + 7
        if len(lines) > 1 and body_y + len(lines) * line_height > image_y - 4:
            raise ValueError(f"释义无法在标题与插画之间安全排入：{item['idiom']}")
        for line_index, line in enumerate(lines):
            draw.text((LEFT, body_y + line_index * line_height), line, fill=INK, font=font)

        panel = sequence_frame(sequences[index], frame_index)
        panel = ImageOps.fit(
            panel,
            (ART_WIDTH, image_height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        canvas.paste(panel, (LEFT, image_y))

        if index < item_count - 1:
            separator_y = image_y + image_height + 11
            draw.line(
                (LEFT, separator_y, LEFT + ART_WIDTH, separator_y),
                fill=INK,
                width=SEPARATOR_WIDTH,
            )
    return canvas


def video_codec(path: Path) -> str:
    capture = cv2.VideoCapture(str(path))
    value = int(capture.get(cv2.CAP_PROP_FOURCC))
    capture.release()
    return "".join(chr((value >> (8 * index)) & 0xFF) for index in range(4)).strip("\x00")


def write_video(job: dict, sequences: list[list[Path]], output: Path) -> list[Image.Image]:
    # Media Foundation can report success but fail to create files whose temporary
    # names contain CJK characters, so keep the transient names ASCII-only.
    direct_temp = output.with_name("_chengyu_h264_temp.mp4")
    fallback_temp = output.with_name("_chengyu_mpeg4_temp.mp4")
    for temp in (direct_temp, fallback_temp):
        if temp.exists():
            temp.unlink()

    # On Windows, Media Foundation provides the built-in H.264 encoder and avoids
    # OpenCV/FFmpeg builds that depend on a mismatched OpenH264 DLL.
    writer = cv2.VideoWriter(
        str(direct_temp),
        cv2.CAP_MSMF if hasattr(cv2, "CAP_MSMF") else cv2.CAP_ANY,
        cv2.VideoWriter_fourcc(*"H264"),
        FPS,
        (WIDTH, HEIGHT),
    )
    if not writer.isOpened():
        writer.release()
        writer = cv2.VideoWriter(
            str(direct_temp),
            cv2.VideoWriter_fourcc(*"avc1"),
            FPS,
            (WIDTH, HEIGHT),
        )
    direct_h264 = writer.isOpened()
    if not direct_h264:
        writer.release()
        writer = cv2.VideoWriter(
            str(fallback_temp),
            cv2.VideoWriter_fourcc(*"mp4v"),
            FPS,
            (WIDTH, HEIGHT),
        )
        if not writer.isOpened():
            raise RuntimeError("无法创建临时视频。")

    qa_frames: list[Image.Image] = []
    try:
        for frame_index in range(FRAME_COUNT):
            frame = render_frame(job, sequences, frame_index)
            if frame_index in {0, 45, 89}:
                qa_frames.append(frame.copy())
            bgr = cv2.cvtColor(np.asarray(frame), cv2.COLOR_RGB2BGR)
            writer.write(bgr)
    finally:
        writer.release()

    if output.exists():
        output.unlink()
    if direct_h264:
        direct_temp.replace(output)
    else:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("当前 OpenCV 不支持H.264，且未找到 ffmpeg；请安装 FFmpeg 并加入 PATH。")
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(fallback_temp),
                "-an",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(FPS),
                "-frames:v",
                str(FRAME_COUNT),
                "-movflags",
                "+faststart",
                str(output),
            ],
            check=True,
        )
        fallback_temp.unlink(missing_ok=True)

    codec = video_codec(output).lower()
    if codec not in {"avc1", "h264", "x264"}:
        raise RuntimeError(f"输出编码不是H.264：{codec}")
    return qa_frames


def save_contact_sheet(frames: list[Image.Image], path: Path) -> None:
    thumb_size = (270, 480)
    sheet = Image.new("RGB", (thumb_size[0] * len(frames), thumb_size[1]), (238, 238, 234))
    for index, frame in enumerate(frames):
        sheet.paste(frame.resize(thumb_size, Image.Resampling.LANCZOS), (index * thumb_size[0], 0))
    sheet.save(path, quality=94)


def main() -> None:
    args = parse_args()
    job = load_job(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sequences = [
        discover_sequence(args.panel_frames / str(index))
        for index in range(1, len(job["items"]) + 1)
    ]
    default_stem = "成语教学_" + "_".join(item["idiom"] for item in job["items"])
    stem = safe_stem(str(job.get("output_stem") or default_stem))
    output = args.output_dir / f"{stem}.mp4"
    qa_frames = write_video(job, sequences, output)
    save_contact_sheet(qa_frames, args.output_dir / f"{stem}_逐帧检查.jpg")

    capture = cv2.VideoCapture(str(output))
    result = {
        "output": str(output),
        "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": float(capture.get(cv2.CAP_PROP_FPS)),
        "frames": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
        "codec": video_codec(output),
    }
    capture.release()
    result["duration"] = result["frames"] / result["fps"]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
