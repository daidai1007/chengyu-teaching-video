from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


SKILL_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_PATHS = [
    SKILL_ROOT / "assets" / "style-reference-family.png",
    SKILL_ROOT / "assets" / "style-reference-elephant.png",
    SKILL_ROOT / "assets" / "style-reference-rabbit.png",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel-frames", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def choose_font(size: int) -> ImageFont.FreeTypeFont:
    for path in [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def mid_frame(folder: Path) -> Path:
    paths = sorted(
        p
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    if not paths:
        raise FileNotFoundError(f"没有找到画面：{folder}")
    return paths[len(paths) // 2]


def metrics(image: Image.Image) -> dict[str, float]:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_32F)
    return {
        "lab_l": float(lab[:, :, 0].mean()),
        "lab_a": float(lab[:, :, 1].mean()),
        "lab_b": float(lab[:, :, 2].mean()),
        "saturation": float(hsv[:, :, 1].mean()),
        "contrast": float(gray.std()),
        "fine_texture": float(np.mean(np.abs(laplacian))),
    }


def envelope(reference_metrics: list[dict[str, float]]) -> dict[str, tuple[float, float]]:
    tolerances = {
        "lab_l": 20.0,
        "lab_a": 11.0,
        "lab_b": 14.0,
        "saturation": 30.0,
        "contrast": 18.0,
        "fine_texture": 8.0,
    }
    result = {}
    for key, tolerance in tolerances.items():
        values = [item[key] for item in reference_metrics]
        result[key] = (min(values) - tolerance, max(values) + tolerance)
    return result


def make_contact_sheet(
    references: list[Image.Image],
    candidates: list[Image.Image],
    output: Path,
) -> None:
    cell_w, cell_h = 427, 215
    label_h = 42
    sheet = Image.new("RGB", (cell_w * 3, (cell_h + label_h) * 2), (243, 242, 235))
    draw = ImageDraw.Draw(sheet)
    font = choose_font(24)
    for row, (label, images) in enumerate([("参考成品", references), ("新插画", candidates)]):
        y = row * (cell_h + label_h)
        draw.text((12, y + 7), label, fill=(25, 25, 22), font=font)
        for index, image in enumerate(images):
            thumb = ImageOps.fit(
                image.convert("RGB"),
                (cell_w, cell_h),
                method=Image.Resampling.LANCZOS,
            )
            sheet.paste(thumb, (index * cell_w, y + label_h))
    sheet.save(output, quality=95)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    references = [Image.open(path).convert("RGB") for path in REFERENCE_PATHS]
    candidate_paths = [mid_frame(args.panel_frames / str(index)) for index in (1, 2, 3)]
    candidates = [Image.open(path).convert("RGB") for path in candidate_paths]

    reference_metrics = [metrics(image) for image in references]
    candidate_metrics = [metrics(image) for image in candidates]
    bounds = envelope(reference_metrics)
    panels = []
    for index, values in enumerate(candidate_metrics):
        checks = {
            key: bounds[key][0] <= value <= bounds[key][1]
            for key, value in values.items()
        }
        panels.append(
            {
                "panel": index + 1,
                "source": str(candidate_paths[index]),
                "metrics": values,
                "checks": checks,
                "numeric_gate": all(checks.values()),
            }
        )

    report = {
        "reference_metrics": reference_metrics,
        "reference_envelope": {
            key: {"min": value[0], "max": value[1]}
            for key, value in bounds.items()
        },
        "panels": panels,
        "numeric_gate": all(panel["numeric_gate"] for panel in panels),
        "manual_review_required": True,
        "manual_review": [
            "确认造型、笔触和颗粒像同一位插画师，而非仅颜色接近。",
            "确认没有厚涂、摄影感、强烈电影光或现代数字概念艺术。",
            "确认三栏色温、饱和度、对比度和细节密度统一。",
        ],
    }
    (args.output_dir / "style-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    make_contact_sheet(
        references,
        candidates,
        args.output_dir / "style-contact-sheet.jpg",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
