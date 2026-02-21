from src.workflow.router import CompanyType

HEADER = "| 番号 | サービス | 金額(円) | 備考 |"
SEPARATOR = "| --- | --- | --- | --- |"


class EmptyResultError(Exception):
    pass


def combine_markdown_rows(results: dict[CompanyType, str]) -> str:
    """各社の分析結果を1つのMarkdownテーブルに結合する。

    DSL テンプレートノード 1764728717913 と同等の処理。
    空の結果はスキップする。
    """
    rows: list[str] = []
    # DSLと同じ順序で結合
    order = [
        CompanyType.NTT,
        CompanyType.OTSUKA,
        CompanyType.NTT_DOCOMO_BIZ,
        CompanyType.SOFTBANK,
        CompanyType.FORVAL,
        CompanyType.OTHER,
    ]
    for company in order:
        text = results.get(company, "").strip()
        if text:
            rows.append(text)

    if not rows:
        raise EmptyResultError("抽出されたデータ行がありません")

    return f"{HEADER}\n{SEPARATOR}\n" + "\n".join(rows) + "\n"
