"""Статическая проверка исходников расширения до загрузки в базу.

Проверяет, что BSL и XML выгрузки остаются в UTF-8 с BOM и CRLF, и прогоняет
BSL Language Server. Синтаксические ошибки BSL (ParseError) и нарушения кодировки
дают код возврата 1; остальные замечания выводятся сводкой и не блокируют.
Это не проверка в базе: ошибки времени выполнения видны только после загрузки.

  python3 tools/bsl-check.py          проверить
  python3 tools/bsl-check.py --fix    привести BOM и CRLF, затем проверить
"""
import collections
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "extensions"
JAR = os.environ.get("BSL_LS_JAR", str(pathlib.Path.home() / "tools/bsl-ls/bsl-language-server-1.0.7-exec.jar"))
BOM = b"\xef\xbb\xbf"
BLOCKING = {"ParseError"}
SHOWN = {"Error", "Warning"}
IGNORED = {"CommonModuleInvalidType", "InvalidCharacterInFile", "QueryParseError",
           "CognitiveComplexity", "CyclomaticComplexity", "IfElseIfEndsWithElse"}


def check_encoding(fix):
    problems = []
    for path in sorted(SRC.rglob("*")):
        if path.suffix not in (".bsl", ".xml"):
            continue
        data = path.read_bytes()
        body = data[len(BOM):] if data.startswith(BOM) else data
        normalized = BOM + body.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        if normalized != data:
            if fix:
                path.write_bytes(normalized)
            else:
                problems.append(str(path.relative_to(ROOT)))
    return problems


def run_bsl_ls():
    with tempfile.TemporaryDirectory() as out:
        subprocess.run(["java", "-jar", JAR, "analyze", "-s", str(SRC), "-r", "json", "-o", out, "-q"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        report = pathlib.Path(out) / "bsl-json.json"
        if not report.exists():
            sys.exit("BSL Language Server не сформировал отчёт; проверьте java и путь BSL_LS_JAR")
        return json.loads(report.read_text(encoding="utf-8"))


def main():
    fix = "--fix" in sys.argv[1:]
    bad_encoding = check_encoding(fix)
    for name in bad_encoding:
        print(f"КОДИРОВКА: {name}: нужен UTF-8 с BOM и CRLF (запустите с --fix)")
    blocking = 0
    summary = collections.Counter()
    for info in run_bsl_ls()["fileinfos"]:
        path = urllib.parse.unquote(info["path"]).split("/src/extensions/", 1)[-1]
        for d in info["diagnostics"]:
            summary[d["code"]] += 1
            line = d["range"]["start"]["line"] + 1
            if d["code"] in BLOCKING:
                blocking += 1
                print(f"ОШИБКА {path}:{line} {d['code']}: {d['message']}")
            elif d["severity"] in SHOWN and d["code"] not in IGNORED:
                print(f"{d['severity']} {path}:{line} {d['code']}: {d['message']}")
    print("Сводка замечаний:", ", ".join(f"{k}={v}" for k, v in sorted(summary.items())) or "нет")
    if blocking or bad_encoding:
        print(f"ПРОВАЛ: синтаксических ошибок {blocking}, файлов с неверной кодировкой {len(bad_encoding)}")
        sys.exit(1)
    print("OK: синтаксических ошибок нет, кодировка и переводы строк в порядке")


if __name__ == "__main__":
    main()
