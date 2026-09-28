#!/usr/bin/env python3
"""Local PDF text/OCR prototype. No document content is sent to a service."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
import tempfile
import time

VERSION = "0.1.2"
HERE = Path(__file__).resolve().parent
MODELS = HERE / ".models"
PACKAGES = ("pypdf", "pdfplumber", "pypdfium2", "rapidocr", "onnxruntime", "Pillow")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def page_range(value, total):
    if not value:
        return list(range(1, total + 1))
    pages = set()
    for part in value.split(","):
        match = re.fullmatch(r"\s*(\d+)(?:-(\d+))?\s*", part)
        if not match:
            raise ValueError(f"无效页段：{part}；示例 1-3,5")
        start, end = int(match[1]), int(match[2] or match[1])
        if not 1 <= start <= end <= total:
            raise ValueError(f"页段 {part} 超出 1–{total} 或顺序错误")
        pages.update(range(start, end + 1))
    return sorted(pages)


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".pdftext-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def save_json(path, value):
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def model_fingerprint():
    return {str(p.relative_to(MODELS)): digest(p)
            for p in sorted(MODELS.rglob("*")) if p.is_file()}


def make_engine(download=False):
    import onnxruntime
    onnxruntime.disable_telemetry_events()
    from rapidocr import RapidOCR
    params = {
        "Global.model_root_dir": str(MODELS),
        "Global.log_level": "error",
        "Global.text_score": 0.15,  # Preserve uncertain text, flag instead of discard.
        "Global.max_side_len": 3600,
        "Det.limit_side_len": 1600,
        "Det.limit_type": "max",
        "EngineConfig.onnxruntime.intra_op_num_threads": 4,
        "EngineConfig.onnxruntime.inter_op_num_threads": 1,
    }
    if not download:
        # Explicit local paths prevent automatic downloads during conversion.
        manifest = json.loads((HERE / "models.lock.json").read_text(encoding="utf-8"))
        for stage, entry in manifest.items():
            path = MODELS / entry["file"]
            if not path.is_file() or digest(path) != entry["sha256"]:
                raise RuntimeError(f"OCR 模型缺失或校验失败：{path.name}；请运行 doctor --download-models")
            params[f"{stage}.model_path"] = str(path)
    return RapidOCR(params=params)


class OCR:
    def __init__(self):
        self.engine = None

    def run(self, image):
        if self.engine is None:
            if len(list(MODELS.rglob("*.onnx"))) < 3:
                raise RuntimeError("缺少 OCR 模型，请联网运行 pdftext doctor --download-models")
            self.engine = make_engine()
        result = self.engine(image)
        if result.boxes is None or result.txts is None:
            return []
        lines = []
        for box, text, score in zip(result.boxes, result.txts, result.scores):
            if text.strip():
                lines.append({"text": text.strip(), "score": round(float(score), 4),
                              "x0": float(min(box[:, 0])), "x1": float(max(box[:, 0])),
                              "y0": float(min(box[:, 1])), "y1": float(max(box[:, 1]))})
        return lines


def find_gutter(lines, width, height):
    """Search a gap between text boxes; do not cut a box merely at the midpoint."""
    body = [r for r in lines if .10 * height < (r["y0"] + r["y1"]) / 2 < .92 * height]
    candidates = []
    for step in range(40, 61):
        x = width * step / 100
        left = [r for r in body if r["x1"] < x]
        right = [r for r in body if r["x0"] > x]
        crossing = len(body) - len(left) - len(right)
        if min(len(left), len(right)) < 6 or crossing:
            continue
        edge_l = max(r["x1"] for r in left)
        edge_r = min(r["x0"] for r in right)
        gap = edge_r - edge_l
        if gap >= width * .025:
            candidates.append((gap, -abs(x - width / 2), (edge_l + edge_r) / 2))
    return max(candidates)[2] if candidates else None


def select_layout(lines, width, height, mode):
    if mode == "single":
        return "single", None, []
    gutter = find_gutter(lines, width, height)
    if mode == "spread":
        return "spread", gutter or width / 2, [] if gutter else ["未找到可靠中缝，手动双页模式使用页面中线；请核对"]
    if width / height > 1.10 and gutter is not None:
        return "spread", gutter, ["自动识别为左右双页；双栏文章也可能具有相同特征，请核对"]
    if width / height > 1.10:
        return "single", None, ["横向页未找到可靠双页证据，保留单页；特殊排版请核对"]
    if gutter is not None:
        return "single", None, ["可能为单页多栏，样品未自动重排为多栏阅读顺序"]
    return "single", None, []


def partition_lines(lines, width, height, mode):
    layout, gutter, warnings = select_layout(lines, width, height, mode)
    if layout == "single":
        return layout, [{"side": "whole", "bounds": [0, 0, width, height], "lines": lines}], warnings
    # Crossing boxes are kept whole, assigned by their center, and explicitly reported.
    if any(r["x0"] < gutter < r["x1"] for r in lines):
        warnings.append("有文字框跨越分割线，已整框保留；请核对分区")
    left = [r for r in lines if (r["x0"] + r["x1"]) / 2 < gutter]
    right = [r for r in lines if (r["x0"] + r["x1"]) / 2 >= gutter]
    return layout, [
        {"side": "left", "bounds": [0, 0, gutter, height], "lines": left},
        {"side": "right", "bounds": [gutter, 0, width, height], "lines": right},
    ], warnings


def join_words(a, b):
    if not a:
        return b
    space = bool(re.search(r"[A-Za-z0-9]$", a) and re.match(r"[A-Za-z0-9]", b))
    return a + (" " if space else "") + b


def paragraphs(lines):
    if not lines:
        return ""
    # Merge fragments on the same baseline, preserving within-line left-to-right order.
    median_h = statistics.median(max(1, r["y1"] - r["y0"]) for r in lines)
    rows = []
    for line in sorted(lines, key=lambda r: ((r["y0"] + r["y1"]) / 2, r["x0"])):
        center = (line["y0"] + line["y1"]) / 2
        if rows and abs(center - rows[-1][0]) < median_h * .45:
            rows[-1][1].append(line)
        else:
            rows.append((center, [line]))
    merged = []
    for _, group in rows:
        group.sort(key=lambda r: r["x0"])
        text = ""
        for r in group:
            text = join_words(text, r["text"])
        merged.append({"text": text, "x0": min(r["x0"] for r in group),
                       "y0": min(r["y0"] for r in group), "y1": max(r["y1"] for r in group)})
    left_edge = min(r["x0"] for r in merged)
    gaps = [max(0, b["y0"] - a["y1"]) for a, b in zip(merged, merged[1:])]
    regular_gap = statistics.median(gaps) if gaps else median_h
    output, text = [], ""
    previous = None
    for row in merged:
        new_para = previous is not None and (
            row["y0"] - previous["y1"] > max(median_h * .9, regular_gap * 1.65)
            or row["x0"] - left_edge > median_h * .9
        )
        if new_para and text:
            output.append(text)
            text = ""
        text = join_words(text, row["text"])
        previous = row
    if text:
        output.append(text)
    return "\n\n".join(output)


def margin_key(line, height):
    text = re.sub(r"\s+", "", line["text"])
    if line["y1"] < height * .105:
        return "top", text
    if line["y0"] > height * .90:
        return "bottom", text
    return None


def clean_pages(pages, keep_margins):
    occurrences = defaultdict(set)
    for page in pages:
        for region in page.get("regions", []):
            for line in region["lines"]:
                key = margin_key(line, page["height"])
                if key and len(key[1]) <= 30:
                    occurrences[key].add(page["page"])
    threshold = max(3, math.ceil(len(pages) * .4))
    repeated = {key for key, seen in occurrences.items() if len(seen) >= threshold}
    for page in pages:
        for region in page.get("regions", []):
            kept, removed = [], []
            for line in region["lines"]:
                key = margin_key(line, page["height"])
                number = key and key[0] == "bottom" and re.fullmatch(r"[-—–·•－―一]*\d{1,4}[-—–·•－―一]*", key[1])
                if not keep_margins and (key in repeated or number):
                    removed.append(line)
                else:
                    kept.append(line)
            region["removed_margins"] = removed
            region["text"] = paragraphs(kept)
        if page.get("regions") and not any(r["text"] for r in page["regions"]):
            page["warnings"].append("未得到正文；可能为空白、图片或识别失败，请核对原页")


def render_page(doc, index, dpi):
    page = doc[index]
    try:
        w, h = page.get_size()
        scale = min(dpi / 72, math.sqrt(24_000_000 / (w * h)))
        bitmap = page.render(scale=scale)
        try:
            return bitmap.to_pil().convert("RGB")
        finally:
            bitmap.close()
    finally:
        page.close()


def process_page(pdf, rendered, index, args, ocr, mode):
    page = pdf.pages[index]
    started = time.monotonic()
    record = {"page": index + 1, "warnings": [], "regions": []}
    try:
        chars = page.chars
        text = "".join(c.get("text", "") for c in chars)
        area = page.width * page.height
        image_area = sum(max(0, i["x1"] - i["x0"]) * max(0, i["bottom"] - i["top"]) for i in page.images)
        bad = sum(c == "\ufffd" or (ord(c) < 32 and not c.isspace()) for c in text)
        needs_ocr = len(text.strip()) < 40 or bad > len(text) * .03 or "(cid:" in text or image_area > area * .2
        if args.ocr == "always":
            needs_ocr = True
        elif args.ocr == "never":
            needs_ocr = False
            if image_area > area * .2 or len(text.strip()) < 40:
                record["warnings"].append("已禁用 OCR；图片内文字可能遗漏")
        if needs_ocr:
            image = render_page(rendered, index, args.dpi)
            width, height = image.size
            try:
                lines = ocr.run(image)
            finally:
                image.close()
            method = "ocr"
            uncertain = [r for r in lines if r["score"] < .85]
            record["low_confidence_lines"] = len(uncertain)
            if uncertain:
                record["warnings"].append(f"{len(uncertain)} 个文字框置信度低于 0.85，内容保留；请核对")
            if any(r["y1"] - r["y0"] > 2 * max(1, r["x1"] - r["x0"]) for r in lines):
                record["warnings"].append("存在竖向文字或特殊装饰，阅读顺序可能不可靠")
        else:
            width, height = page.width, page.height
            words = page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False)
            lines = [{"text": w["text"], "score": 1.0, "x0": w["x0"], "x1": w["x1"],
                      "y0": w["top"], "y1": w["bottom"]} for w in words]
            method = "text"
        layout, regions, warnings = partition_lines(lines, width, height, mode)
        record.update(width=width, height=height, method=method, layout=layout, regions=regions)
        record["warnings"].extend(warnings)
        record["status"] = "review" if record["warnings"] else "ok"
    except Exception as error:
        record.update(status="failed", error=f"{type(error).__name__}: {error}")
    finally:
        page.close()
    record["seconds"] = round(time.monotonic() - started, 3)
    return record


def documents(pages):
    blocks = []
    for page in pages:
        if page["status"] == "failed":
            blocks.append("[本页转换失败，详见 report.json]")
            continue
        for region in page["regions"]:
            body = region["text"] or "[未识别到正文，请核对原页]"
            blocks.append(body)
    text = "\n\n".join(blocks) + "\n"
    return text, text


def cache_valid(out, identity):
    try:
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        return (report["identity"] == identity and report["status"] not in ("failed", "partial")
                and bool(report["files"]) and all(digest(out / name) == h for name, h in report["files"].items()))
    except (OSError, KeyError, ValueError):
        return False


def convert_one(source, args, ocr):
    import pdfplumber
    import pypdfium2
    source = source.resolve()
    started = time.monotonic()
    if source.stat().st_size > 512 * 1024 * 1024:
        raise ValueError("样品暂不处理超过 512 MiB 的 PDF")
    with pdfplumber.open(source) as pdf:
        total = len(pdf.pages)
        selected = page_range(args.pages, total)
        singles = set(page_range(args.single_pages, total)) if args.single_pages else set()
        spreads = set(page_range(args.spread_pages, total)) if args.spread_pages else set()
        if singles & spreads:
            raise ValueError("--single-pages 与 --spread-pages 页段不能重叠")
        versions = {p: importlib.metadata.version(p) for p in PACKAGES}
        identity = {"version": VERSION, "source_sha256": digest(source), "packages": versions,
                    "models": model_fingerprint(), "pages": selected, "layout": args.layout,
                    "single_pages": sorted(singles), "spread_pages": sorted(spreads),
                    "ocr": args.ocr, "dpi": args.dpi, "keep_margins": args.keep_margins, "format": args.format}
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:12]
        parent = Path(args.output_dir).resolve() if args.output_dir else source.parent / "_extracted"
        out = parent / f"{source.stem}-{key}"
        if not args.force and cache_valid(out, identity):
            # Source location is not part of the key, but provenance must stay current.
            report = json.loads((out / "report.json").read_text(encoding="utf-8"))
            report["source"] = str(source)
            save_json(out / "report.json", report)
            print(json.dumps({"status": "cached", "output": str(out)}, ensure_ascii=False))
            return 0
        rendered = pypdfium2.PdfDocument(source)
        try:
            pages = []
            for n in selected:
                mode = "single" if n in singles else "spread" if n in spreads else args.layout
                result = process_page(pdf, rendered, n - 1, args, ocr, mode)
                pages.append(result)
                print(f"[{source.name}] {n}/{total}: {result.get('method', '-')} / {result.get('layout', '-')} / {result['status']}", file=sys.stderr, flush=True)
        finally:
            rendered.close()
    clean_pages(pages, args.keep_margins)
    for p in pages:
        if p["status"] != "failed" and p["warnings"]:
            p["status"] = "review"
    failures = sum(p["status"] == "failed" for p in pages)
    status = "failed" if failures == len(pages) else "partial" if failures else "review" if any(p["warnings"] for p in pages) else "ok"
    md, txt = documents(pages)
    out.mkdir(parents=True, exist_ok=True)
    # Invalidate old manifest before replacing payloads; interrupted writes cannot hit cache.
    save_json(out / "report.json", {"status": "incomplete"})
    files = ["pages.json"]
    save_json(out / "pages.json", pages)
    for fmt, body in (("md", md), ("txt", txt)):
        if args.format in (fmt, "both"):
            name = f"document.{fmt}"
            atomic_text(out / name, body)
            files.append(name)
    report = {"version": VERSION, "status": status, "source": str(source), "identity": identity,
              "pdf_pages": total, "selected_pages": selected, "failed_pages": failures,
              "seconds": round(time.monotonic() - started, 3),
              "characters": sum(len(r["text"]) for p in pages for r in p.get("regions", [])),
              "notice": "OCR 可能错字或漏字；置信度不是准确率。装饰、水印、遮挡和复杂排版不能保证完整识别。",
              "pages": [{k: v for k, v in p.items() if k not in ("regions", "width", "height")} for p in pages],
              "files": {name: digest(out / name) for name in files}}
    save_json(out / "report.json", report)
    print(json.dumps({k: report[k] for k in ("status", "seconds", "characters", "failed_pages")} | {"output": str(out)}, ensure_ascii=False))
    return 1 if status == "failed" else 2 if status == "partial" else 0


def read_result(args):
    root = Path(args.result)
    report = json.loads((root / "report.json").read_text(encoding="utf-8"))
    if report.get("status") == "incomplete":
        raise ValueError("该结果写入未完成，请重新转换")
    if digest(root / "pages.json") != report["files"]["pages.json"]:
        raise ValueError("pages.json 已变化或损坏，请重新转换")
    pages = json.loads((root / "pages.json").read_text(encoding="utf-8"))
    selected = set(page_range(args.pages, report["pdf_pages"])) if args.pages else {p["page"] for p in pages}
    missing = selected - {p["page"] for p in pages}
    if missing:
        raise ValueError(f"缓存没有这些页，请先转换：{sorted(missing)}")
    text = documents([p for p in pages if p["page"] in selected])[0]
    if args.offset > len(text):
        raise ValueError("offset 超出选中正文长度")
    end = min(len(text), args.offset + args.max_chars)
    print(text[args.offset:end])
    if end < len(text):
        print(f"\n[已截断；保持相同页段，使用 --offset {end} 接续]")


def doctor(download=False):
    result = {"python": sys.version.split()[0], "tool": VERSION, "packages": {}}
    ok = True
    for name in PACKAGES:
        try:
            result["packages"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result["packages"][name] = "missing"
            ok = False
    if download and ok:
        make_engine(download=True)
    result["models"] = model_fingerprint()
    manifest = json.loads((HERE / "models.lock.json").read_text(encoding="utf-8"))
    result["ocr_ready"] = all(result["models"].get(m["file"]) == m["sha256"] for m in manifest.values())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if ok and result["ocr_ready"] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="本地 PDF 转文字样品：单页、双页、文字层与中文 OCR")
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    convert = commands.add_parser("convert", help="转换文件或目录，默认不打印全文")
    convert.add_argument("source", type=Path)
    convert.add_argument("--format", choices=("md", "txt", "both"), default="md")
    convert.add_argument("--pages", help="PDF 物理页码，从 1 起，例如 1-3,5")
    convert.add_argument("--layout", choices=("auto", "single", "spread"), default="auto")
    convert.add_argument("--single-pages")
    convert.add_argument("--spread-pages")
    convert.add_argument("--ocr", choices=("auto", "always", "never"), default="auto")
    convert.add_argument("--dpi", type=int, default=260)
    convert.add_argument("--keep-margins", action="store_true", help="保留重复页眉页脚")
    convert.add_argument("--output-dir", help="结果父目录，默认 PDF 同级 _extracted")
    convert.add_argument("--recursive", action="store_true")
    convert.add_argument("--force", action="store_true")
    read = commands.add_parser("read", help="按页读取已有结果")
    read.add_argument("result")
    read.add_argument("--pages")
    read.add_argument("--max-chars", type=int, default=12000)
    read.add_argument("--offset", type=int, default=0)
    check = commands.add_parser("doctor", help="检查依赖和模型")
    check.add_argument("--download-models", action="store_true", help="联网下载模型并验证可加载")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            return doctor(args.download_models)
        if args.command == "read":
            if args.max_chars <= 0 or args.offset < 0:
                raise ValueError("max-chars 必须为正，offset 不能为负")
            read_result(args)
            return 0
        if not 72 <= args.dpi <= 400:
            raise ValueError("dpi 需在 72–400 之间")
        if args.source.is_dir():
            pattern = "**/*" if args.recursive else "*"
            sources = sorted(p for p in args.source.glob(pattern) if p.is_file() and p.suffix.lower() == ".pdf" and "_extracted" not in p.parts)
        else:
            sources = [args.source]
        if not sources:
            raise ValueError("没有找到 PDF 文件")
        code, ocr = 0, OCR()
        for source in sources:
            try:
                if not source.is_file() or source.suffix.lower() != ".pdf":
                    raise ValueError(f"不是 PDF 文件：{source}")
                code = max(code, convert_one(source, args, ocr))
            except Exception as error:
                print(f"转换失败 [{source.name}]：{type(error).__name__}: {error}", file=sys.stderr)
                code = max(code, 1)
        return code
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已中断；原 PDF 未修改。", file=sys.stderr)
        sys.exit(130)
