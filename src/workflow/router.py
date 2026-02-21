from enum import Enum


class CompanyType(Enum):
    NTT = "ntt"
    OTSUKA = "otsuka"
    NTT_DOCOMO_BIZ = "ntt_docomo_biz"
    SOFTBANK = "softbank"
    FORVAL = "forval"
    OTHER = "other"


# DSL IF/ELSE node 1764739779573 の条件を忠実に再現
# 順序が重要: Case 1 (NTT) → Case 2 (大塚商会) → Case 3 (NTTドコモBiz) → Case 4 (SoftBank) → Case 5 (フォーバル) → ELSE
COMPANY_RULES: list[tuple[CompanyType, list[str]]] = [
    (CompanyType.NTT, ["NTT東日本", "NTT西日本", "NTT Communications"]),
    (CompanyType.OTSUKA, ["大塚商会"]),
    (CompanyType.NTT_DOCOMO_BIZ, ["NTTドコモビジネス", "docomo Business", "OCN", "ＯＣＮ"]),
    (CompanyType.SOFTBANK, ["SoftBank", "ソフトバンク"]),
    (CompanyType.FORVAL, ["フォーバル", "FORVAL"]),
]


def detect_company(ocr_text: str) -> CompanyType:
    """OCRテキストからキーワードマッチで会社を判定する。

    DSL IF/ELSE ノードと同じ順序で評価し、最初にマッチした会社を返す。
    どの条件にもマッチしない場合は OTHER を返す。
    """
    for company_type, keywords in COMPANY_RULES:
        if any(keyword in ocr_text for keyword in keywords):
            return company_type
    return CompanyType.OTHER
