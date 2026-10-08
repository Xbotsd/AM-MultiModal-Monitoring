# -*- coding: utf-8 -*-
"""
图片自动编号 + 合并 + 导出 TIFF
调用口令：SCP111
运行: py -3.12 run_figure_pipeline.py
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import shutil

SRC_DIR = Path("data/figures")
DST_DIR = Path("data/figures_tif")
DST_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 图号映射（方案B：合并双面板）
# ============================================================
SINGLE_FIGS = {
    4:  "fig1_fusion_baseline.png",
    5:  "fig2_fusion_combinations.png",
    6:  "fig3_unwrap_baseline.png",
    7:  "fig4_control_baseline.png",
    8:  "fig5_acoustic_ablation.png",
    9:  "fig6_cross_subset.png",
    10: "fig7_noise_sensitivity.png",
    11: "fig8_auc.png",
}

# 双面板图：(图号, 左图文件名, 右图文件名, 左标签, 右标签)
DOUBLE_FIGS = [
    (12, "fig_confusion_acoustic.png", "fig_confusion_lu.png",
     "(a)", "(b)"),
    (13, "fig_corr_acoustic.png", "fig_corr_lu.png",
     "(a)", "(b)"),
    (14, "fig_tsne_acoustic.png", "fig_tsne_lu.png",
     "(a)", "(b)"),
]

# ============================================================
# 图题（用于生成 captions 文本）
# ============================================================
CAPTIONS = {
    4:  "Multi-modal fusion baseline comparison.",
    5:  "Multi-modal combination comparison.",
    6:  "Phase unwrapping baseline comparison.",
    7:  "Closed-loop control baseline comparison.",
    8:  "Ablation study for the acoustic module.",
    9:  "Cross-subset validation on EPFL D1-D4.",
    10: "Noise sensitivity analysis of the fusion framework.",
    11: "ROC/AUC comparison for laser ultrasound and acoustic modules.",
    12: "Normalized confusion matrices for (a) the acoustic module and (b) the laser ultrasound module.",
    13: "Pearson correlation matrices of the 14-dimensional feature set for (a) the acoustic module and (b) the laser ultrasound module.",
    14: "t-SNE visualization of the 14-dimensional feature space for (a) the acoustic module and (b) the laser ultrasound module.",
}


def try_get_font(size=40):
    """尝试加载一个可用字体，找不到就用默认"""
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def convert_single(fig_num, src_name):
    """单图：直接转 TIFF"""
    src = SRC_DIR / src_name
    if not src.exists():
        print(f"  ⚠️ 缺少: {src_name}，跳过 Figure {fig_num}")
        return False
    dst = DST_DIR / f"Fig{fig_num}.tif"
    img = Image.open(src).convert("RGB")
    img.save(dst, format="TIFF", dpi=(600, 600))
    print(f"  ✅ Figure {fig_num}  →  {dst.name}  ({img.width}×{img.height})")
    return True


def merge_double(fig_num, left_name, right_name, left_label, right_label):
    """双面板图：左右拼接 + (a)/(b) 标注"""
    left_path = SRC_DIR / left_name
    right_path = SRC_DIR / right_name
    if not left_path.exists() or not right_path.exists():
        print(f"  ⚠️ 缺少: {left_name} 或 {right_name}，跳过 Figure {fig_num}")
        return False

    left = Image.open(left_path).convert("RGB")
    right = Image.open(right_path).convert("RGB")

    # 统一高度
    target_h = max(left.height, right.height)
    def resize_keep_ratio(img, target_h):
        ratio = target_h / img.height
        return img.resize((int(img.width * ratio), target_h), Image.LANCZOS)

    left = resize_keep_ratio(left, target_h)
    right = resize_keep_ratio(right, target_h)

    gap = 60
    label_h = 80
    canvas_w = left.width + right.width + gap + 40
    canvas_h = target_h + label_h + 40

    canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
    canvas.paste(left, (20, label_h))
    canvas.paste(right, (left.width + gap + 20, label_h))

    draw = ImageDraw.Draw(canvas)
    font = try_get_font(44)

    # 标注 (a) / (b)
    draw.text((left.width // 2 - 10, 10), left_label, fill="black", font=font)
    draw.text((left.width + gap + right.width // 2 - 10, 10),
              right_label, fill="black", font=font)

    dst = DST_DIR / f"Fig{fig_num}.tif"
    canvas.save(dst, format="TIFF", dpi=(600, 600))
    print(f"  ✅ Figure {fig_num}  →  {dst.name}  ({canvas.width}×{canvas.height})")
    return True


def generate_captions():
    """生成 Figure Captions 文本文件"""
    lines = ["Figure Captions", ""]
    for num in sorted(CAPTIONS.keys()):
        lines.append(f"Figure {num}. {CAPTIONS[num]}")
    text = "\n".join(lines)
    out_path = DST_DIR / "Figure_Captions.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"\n  ✅ 图题已保存: {out_path}")
    return text


def main():
    print("=" * 60)
    print("图片自动编号 + 合并 + 导出 TIFF")
    print("=" * 60)

    print(f"\n源目录: {SRC_DIR}")
    print(f"输出目录: {DST_DIR}\n")

    # ---- 单图 ----
    print("[单图]")
    ok_single = 0
    for num, name in sorted(SINGLE_FIGS.items()):
        if convert_single(num, name):
            ok_single += 1

    # ---- 双面板图 ----
    print("\n[双面板图]")
    ok_double = 0
    for num, lname, rname, llab, rlab in DOUBLE_FIGS:
        if merge_double(num, lname, rname, llab, rlab):
            ok_double += 1

    # ---- 图题 ----
    print("\n[图题]")
    generate_captions()

    # ---- 汇总 ----
    print(f"\n{'=' * 60}")
    print(f"完成：单图 {ok_single}/8，双面板 {ok_double}/3")
    print(f"所有 TIFF 文件位于: {DST_DIR}")
    print(f"{'=' * 60}")

    # ---- 列出最终文件 ----
    print("\n最终文件清单:")
    files = sorted(DST_DIR.glob("Fig*.tif"),
                   key=lambda p: int(p.stem.replace("Fig", "")))
    for f in files:
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"  {f.name:<12s}  {size_mb:.2f} MB")


if __name__ == "__main__":
    main()