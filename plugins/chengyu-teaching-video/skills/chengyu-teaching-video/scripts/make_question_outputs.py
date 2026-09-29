from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1080, 1920
MARGIN = 114
RIGHT = WIDTH - MARGIN
IVORY = (250, 250, 247)
INK = (20, 20, 18)
LINE = (58, 58, 54)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def choose_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        [
            r"C:\Windows\Fonts\msyhbd.ttc",
            r"C:\Windows\Fonts\simhei.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/System/Library/Fonts/PingFang.ttc",
        ]
        if bold
        else [
            r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\simsun.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
            "/System/Library/Fonts/PingFang.ttc",
        ]
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size=size)


def safe_stem(text: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", text).strip(" .")


def load_job(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items")
    questions = data.get("questions")
    if not isinstance(items, list) or len(items) not in {2, 3, 4}:
        raise ValueError("items 必须包含两至四个词项。")
    if not isinstance(questions, list) or not questions:
        raise ValueError("questions 至少包含一道题目。")
    return data


def tokenize(text: str) -> list[str]:
    return re.findall(r"_{3,}|[A-Za-z0-9]+|.", text, flags=re.S)


def wrap_text(
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


def build_copyable_text(job: dict) -> str:
    options = "　".join(
        f"{chr(65 + index)}. {item['idiom']}"
        for index, item in enumerate(job["items"])
    )
    lines = [f"【{options}】", ""]
    for index, question in enumerate(job["questions"], start=1):
        lines.append(f"{index}. {str(question.get('text', '')).strip()}")
        lines.append("")
    answers = [
        f"{index}. {str(question.get('answer', '')).strip()}"
        for index, question in enumerate(job["questions"], start=1)
        if str(question.get("answer", "")).strip()
    ]
    if answers:
        lines.extend(["参考答案：", *answers])
    return "\n".join(lines).rstrip() + "\n"


def draw_question_card(job: dict) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), IVORY)
    draw = ImageDraw.Draw(image)
    item_count = len(job["items"])
    option_font = choose_font({2: 38, 3: 34, 4: 27}[item_count], bold=False)
    question_font = choose_font(42, bold=False)

    gap = 18 if item_count <= 3 else 12
    box_width = (RIGHT - MARGIN - gap * (item_count - 1)) // item_count
    top, bottom = MARGIN, MARGIN + 92
    for index, item in enumerate(job["items"]):
        left = MARGIN + index * (box_width + gap)
        right = left + box_width
        draw.rounded_rectangle(
            (left, top, right, bottom),
            radius=18,
            outline=LINE,
            width=3,
        )
        label = f"{chr(65 + index)}. {item['idiom']}"
        box = draw.textbbox((0, 0), label, font=option_font)
        x = left + (box_width - (box[2] - box[0])) // 2
        y = top + (bottom - top - (box[3] - box[1])) // 2 - box[1]
        draw.text((x, y), label, fill=INK, font=option_font)

    questions = job["questions"]
    content_top = 270
    content_bottom = HEIGHT - 150
    section_height = (content_bottom - content_top) // len(questions)
    max_width = RIGHT - MARGIN
    for index, question in enumerate(questions):
        y0 = content_top + index * section_height
        text = f"{index + 1}. {str(question.get('text', '')).strip()}"
        lines = wrap_text(draw, text, question_font, max_width)
        line_height = 67
        for line_index, line in enumerate(lines):
            draw.text(
                (MARGIN, y0 + line_index * line_height),
                line,
                fill=INK,
                font=question_font,
            )
        if index < len(questions) - 1:
            separator_y = content_top + (index + 1) * section_height - 38
            draw.line((MARGIN, separator_y, RIGHT, separator_y), fill=(120, 120, 114), width=2)
    return image


def main() -> None:
    args = parse_args()
    job = load_job(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    idiom_stem = safe_stem("_".join(str(item["idiom"]) for item in job["items"]))
    text = build_copyable_text(job)
    txt_path = args.output_dir / f"题目可复制_{idiom_stem}.txt"
    md_path = args.output_dir / f"题目可复制_{idiom_stem}.md"
    png_path = args.output_dir / f"选择题_{idiom_stem}.png"
    jpg_path = args.output_dir / f"选择题_{idiom_stem}.jpg"

    txt_path.write_text(text, encoding="utf-8-sig")
    md_path.write_text(text, encoding="utf-8")
    card = draw_question_card(job)
    card.save(png_path)
    card.save(jpg_path, quality=95, subsampling=0)
    print(
        json.dumps(
            {
                "txt": str(txt_path),
                "markdown": str(md_path),
                "png": str(png_path),
                "jpg": str(jpg_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
