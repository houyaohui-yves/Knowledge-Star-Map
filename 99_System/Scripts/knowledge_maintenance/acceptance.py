#!/usr/bin/env python3
"""Prepare and scan reproducible acceptance copies; semantic decisions remain pending."""
import argparse
import json
from pathlib import Path
import shutil
import check as m


def prepare(vault, config, output):
    baseline = m.snapshot(vault, config)
    selected = config["files"]
    concept, case, source, navigation = selected
    records = []
    for label in ("T01", "T02", "T03", "T04", "T05", "T06"):
        home = output / label
        home.mkdir()  # Refuse to overwrite a previous acceptance run.
        fixture = home / "vault"
        fixture.mkdir()
        for root in config["index_roots"]:
            (fixture / root).mkdir(parents=True, exist_ok=True)
        for rel in baseline["versions"]:
            original = m.bounded(vault, rel)
            if original.is_file():
                destination = m.bounded(fixture, rel)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, destination)
        change = "无内容修改"
        if label in ("T02", "T03", "T04"):
            target, old, new = {
                "T02": (navigation, "[[RAG中的Query改写]]", "[[验收专用不存在目标]]"),
                "T03": (case, "不能证明建议改写提高召回", "已经验证建议改写提高召回"),
                "T04": (case, "这些核验确认的是程序分支与解析行为", "这些离线检查验证的是程序分支和解析行为"),
            }[label]
            path = fixture / target
            text = path.read_text(encoding="utf-8")
            if old not in text:
                raise ValueError(f"{label} 的基线句已变化，请重新选择样本")
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            change = f"{target}: {old} → {new}（只替换第一处）"
        if label == "T05":
            candidates = [p for p in baseline["versions"] if p.endswith("/1-Query改写.py")]
            if len(candidates) != 1 or not (fixture / candidates[0]).is_file():
                raise ValueError("T05 需要一份基线中可达的 Query 脚本副本")
            (fixture / candidates[0]).unlink()  # Only a file just copied into this new test directory.
            change = "隔离副本移除：" + candidates[0]
        state_path = home / "state"
        with m.state_folder(state_path, fixture) as state_folder:
            checkpoint = m.scan(fixture, config, state_folder, 1 if label == "T06" else None)
            if label == "T06":
                resumed = m.scan(fixture, config, state_folder)
                repeated = m.scan(fixture, config, state_folder)
                counts = [checkpoint["last_scan"]["processed_files"], resumed["last_scan"]["processed_files"], repeated["last_scan"]["processed_files"]]
                if counts != [1, 3, 0]:
                    raise AssertionError(counts)
                change = "分批处理、恢复、重复运行；本次处理文件数为 1、3、0"
            state = m.read_json(state_folder / "state.json")
        records.append({"case": label, "change": change, "snapshot_id": state["snapshot_id"],
                        "status": state["status"], "fixture": str(fixture), "state_dir": str(state_path),
                        "findings": [f for r in state["completed"].values() for f in r["findings"]]})
    m.save_json(output / "cases.json", records)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("pilot.json"))
    parser.add_argument("--output-dir", type=Path, required=True, help="新的工具状态目录；拒绝覆盖既有验收场景")
    args = parser.parse_args()
    vault = args.vault.resolve(strict=True)
    config = m.load_manifest(args.manifest, vault)
    with m.state_folder(args.output_dir, vault) as output:
        records = prepare(vault, config, output)
        print(json.dumps([{"case": r["case"], "findings": len(r["findings"]), "state": r["status"]} for r in records], ensure_ascii=False))


if __name__ == "__main__":
    main()
