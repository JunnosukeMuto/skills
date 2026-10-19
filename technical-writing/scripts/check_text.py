#!/usr/bin/env python3
"""日本語技術文書の機械的チェック。

検出項目:
  long        長すぎる文（既定: 50 字超で注意、80 字超で警告）
  vague       曖昧・ぼかし表現（らしい、のような、と思われる 等）
  colloquial  口語表現（みたいな、とか、ちゃんと 等）
  style       「だ・である」調と「です・ます」調の混在
  wa          1 文中の「は」の多用
  abbr        初出時に説明のない略語（英大文字 2 文字以上）
  redundant   冗長表現（まず最初に、することができる 等）

検出は目安である。文脈上問題ないものは無視してよい。

使い方:
  python3 check_text.py FILE [--warn 50] [--error 80] [--json]
  cat FILE | python3 check_text.py -
"""

import argparse
import json
import re
import sys

VAGUE = [
    "らしい", "のような", "のように思", "みたいだ", "ようだ", "ようです",
    "と思われ", "と考えられ", "と言える", "と言ってもよい", "ではないか",
    "であろう", "でしょう", "たぶん", "多分", "おそらく", "ほぼ", "ぐらい", "くらい",
    "ほど", "等々", "かもしれ", "と見てもよい", "なるべく",
    "適宜", "適切に", "いい感じ",
]
APPROX = {"ほど", "くらい", "ぐらい"}
COLLOQUIAL = [
    "みたいな", "みたいに", "とか", "ちゃんと", "すごく", "すごい", "めっちゃ",
    "やっぱり", "やっぱ", "ちょっと", "けど", "じゃない", "っていう",
    "とゆう", "どうゆう", "いろんな",
]
REDUNDANT = [
    ("まず最初に", "最初に"), ("一番最初", "最初"), ("することができる", "できる"),
    ("することが可能", "できる"), ("という風に", "のように"), ("各々の", "各"),
    ("あらかじめ予定", "予定"), ("後で後悔", "後悔"), ("の分類に分け", "種類に分け"),
    ("を行う", "（動詞化を検討: 例『確認を行う』→『確認する』）"),
]
# 略語として扱わない一般的な語
ABBR_ALLOW = {
    "OK", "NG", "PC", "OS", "ID", "URL", "HTTP", "HTTPS", "API", "CPU", "GPU",
    "AI", "IT", "PDF", "CSV", "JSON", "HTML", "CSS", "SQL", "DB", "UI", "UX",
    "IP", "TCP", "UDP", "DNS", "USB", "AWS", "GCP", "CLI", "GUI", "SSH", "TV",
    "FAQ", "README", "TODO", "JST", "UTC", "XML", "YAML", "GB", "MB", "KB", "TB",
    "MS", "Q1", "Q2", "Q3", "Q4",
}

DEARU_RE = re.compile(r"(である|だ|した|する|ない|れる|られる|できる|いる|ある|なる|示す|いう)[。]")
DESUMASU_RE = re.compile(r"(です|ます|ました|ません|でした|ましょう|ください)[。]")
ABBR_RE = re.compile(r"(?<![A-Za-z0-9_./-])([A-Z][A-Z0-9]{1,9})(?![A-Za-z0-9_])")
SENT_SPLIT_RE = re.compile(r"(?<=[。！？!?])")


def strip_markup(text):
    """コードブロック・インラインコード・URL・表区切り等を除去し、行番号を保つ。"""
    lines = text.split("\n")
    out = []
    in_code = False
    # YAML frontmatter は対象外
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                out = [""] * (j + 1)
                lines = lines[j + 1:]
                break
    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            out.append("")
            continue
        if in_code or re.match(r"^\s*\|?\s*:?-{3,}", line):
            out.append("")
            continue
        line = re.sub(r"`[^`]*`", "", line)
        line = re.sub(r"https?://\S+", "", line)
        line = re.sub(r"\]\([^)]*\)", "]", line)
        out.append(line)
    return out


def sentences(lines):
    """(行番号, 文) を返す。見出し・箇条書き・表の行は 1 行を 1 文として扱う。"""
    buf, start = "", None
    for i, raw in enumerate(lines, 1):
        line = raw.strip()
        structural = re.match(r"^(#{1,6}\s|[-*+]\s|\d+[.)]\s|\||>)", line)
        if not line or structural:
            if buf:
                yield start, buf
                buf, start = "", None
            if structural:
                body = re.sub(r"^(#{1,6}\s|[-*+]\s|\d+[.)]\s|>\s?)", "", line)
                for cell in body.split("|"):
                    for s in SENT_SPLIT_RE.split(cell):
                        if s.strip():
                            yield i, s.strip()
            continue
        for part in SENT_SPLIT_RE.split(line):
            if not part:
                continue
            if start is None:
                start = i
            buf += part
            if re.search(r"[。！？!?]$", part):
                yield start, buf
                buf, start = "", None
    if buf:
        yield start, buf


def char_len(s):
    return len(re.sub(r"\s", "", s))


def check(text, warn, error):
    lines = strip_markup(text)
    sents = list(sentences(lines))
    issues = []

    def add(line, kind, level, msg, snippet):
        issues.append({"line": line, "kind": kind, "level": level,
                       "message": msg, "text": snippet[:60] + ("…" if len(snippet) > 60 else "")})

    dearu, desumasu = [], []
    for ln, s in sents:
        n = char_len(s)
        if n > error:
            add(ln, "long", "warning", f"一文が {n} 字（{error} 字超）。文を分けることを検討", s)
        elif n > warn:
            add(ln, "long", "info", f"一文が {n} 字（{warn} 字超）", s)

        # 「」内は語の言及（例示・引用）とみなし、語彙チェックの対象外にする
        body = re.sub(r"「[^」]*」", "", s)
        if re.match(r"^(なので|だから|でも)、", body):
            add(ln, "colloquial", "warning", "文頭の接続語が口語（→「そのため」「しかし」）", s)
        for w in VAGUE:
            if w not in body:
                continue
            # 「ほど」「くらい」は比較（「A ほど速い」）にも使うため、数値の直後のみ対象
            if w in APPROX and not re.search(r"\d\s*[%％件個秒分時日人台回倍]?\s*" + w, s):
                continue
            add(ln, "vague", "info", f"曖昧・ぼかし表現「{w}」。言い切れるか、根拠を示せるか確認", s)
        for w in COLLOQUIAL:
            if w in body:
                add(ln, "colloquial", "warning", f"口語表現「{w}」", s)
        for w, fix in REDUNDANT:
            if w in body:
                add(ln, "redundant", "info", f"冗長表現「{w}」→「{fix}」", s)

        # 「では」「には」「とは」を除いた係助詞「は」の概数
        wa = len(re.findall(r"[^でにとはわ]は(?![ずじ])", s))
        if wa >= 3:
            add(ln, "wa", "info", f"「は」が {wa} 回。主題が重なっていないか確認", s)

        if DEARU_RE.search(s):
            dearu.append((ln, s))
        if DESUMASU_RE.search(s):
            desumasu.append((ln, s))

    if dearu and desumasu:
        minority, label = (desumasu, "です・ます") if len(desumasu) < len(dearu) else (dearu, "だ・である")
        major = "だ・である" if label == "です・ます" else "です・ます"
        for ln, s in minority:
            add(ln, "style", "warning",
                f"文体の混在: 多数派は「{major}」調（{max(len(dearu), len(desumasu))} 文）、この文は「{label}」調", s)

    # 略語: 初出の直後（または直前）に括弧書きの説明があるか
    full = "\n".join(lines)
    seen = set()
    for m in ABBR_RE.finditer(full):
        abbr = m.group(1)
        if abbr in seen or abbr in ABBR_ALLOW or abbr.isdigit():
            continue
        seen.add(abbr)
        after = full[m.end():m.end() + 3]
        before = full[max(0, m.start() - 2):m.start()]
        explained = re.match(r"\s?[（(]", after) or re.search(r"[（(:：]\s?$", before)
        if not explained:
            ln = full.count("\n", 0, m.start()) + 1
            add(ln, "abbr", "info", f"略語「{abbr}」の初出に説明がない（例: {abbr}（正式名称））",
                lines[ln - 1].strip())

    issues.sort(key=lambda x: (x["line"], x["kind"]))
    return issues, len(sents)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file", help="対象ファイル（- で標準入力）")
    p.add_argument("--warn", type=int, default=50, help="注意とする文字数（既定 50）")
    p.add_argument("--error", type=int, default=80, help="警告とする文字数（既定 80）")
    p.add_argument("--json", action="store_true", help="JSON で出力")
    a = p.parse_args()

    text = sys.stdin.read() if a.file == "-" else open(a.file, encoding="utf-8").read()
    issues, n = check(text, a.warn, a.error)

    if a.json:
        print(json.dumps({"sentences": n, "issues": issues}, ensure_ascii=False, indent=2))
        return

    counts = {}
    for it in issues:
        counts[it["kind"]] = counts.get(it["kind"], 0) + 1
        mark = "!" if it["level"] == "warning" else "-"
        print(f"{mark} L{it['line']} [{it['kind']}] {it['message']}\n    {it['text']}")
    summary = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "なし"
    print(f"\n文の数: {n} / 指摘: {len(issues)}（{summary}）")


if __name__ == "__main__":
    main()
