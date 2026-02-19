import io
import re

from openpyxl import Workbook


def _parse_markdown_table(markdown: str) -> list[list[str]]:
    """Markdownテーブルをパースして2次元リストに変換する。"""
    rows: list[list[str]] = []
    for line in markdown.strip().splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        # セパレータ行 (| --- | --- | ...) をスキップ
        if re.match(r"^\|[\s\-:]+\|", line):
            continue
        cells = [cell.strip() for cell in line.split("|")]
        # 先頭と末尾の空文字を除去 (| で split すると先頭末尾が空になる)
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]
        if cells:
            rows.append(cells)
    return rows


def markdown_to_xlsx(markdown: str) -> bytes:
    """MarkdownテーブルをXLSXバイト列に変換する。

    DSL の md_to_xlsx ツール (force_text_value=false) と同等。
    ファイル名は呼び出し側で制御する。
    """
    rows = _parse_markdown_table(markdown)
    if not rows:
        raise ValueError("変換するデータがありません")

    wb = Workbook()
    ws = wb.active

    for row_data in rows:
        ws.append(row_data)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
