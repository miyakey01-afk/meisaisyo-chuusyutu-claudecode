from src.workflow.router import CompanyType, detect_company


class TestDetectCompany:
    # Case 1: NTT
    def test_ntt_east(self):
        assert detect_company("NTT東日本の請求書です") == CompanyType.NTT

    def test_ntt_west(self):
        assert detect_company("NTT西日本からの料金明細") == CompanyType.NTT

    def test_ntt_communications(self):
        assert detect_company("NTT Communicationsご利用料金") == CompanyType.NTT

    # Case 2: 大塚商会
    def test_otsuka(self):
        assert detect_company("株式会社 大塚商会 御請求書") == CompanyType.OTSUKA

    # Case 3: NTTドコモビジネス
    def test_ntt_docomo_biz(self):
        assert detect_company("NTTドコモビジネスの料金明細") == CompanyType.NTT_DOCOMO_BIZ

    def test_docomo_business(self):
        assert detect_company("docomo Business利用料金") == CompanyType.NTT_DOCOMO_BIZ

    def test_ocn_halfwidth(self):
        assert detect_company("OCNプロバイダ料金") == CompanyType.NTT_DOCOMO_BIZ

    def test_ocn_fullwidth(self):
        assert detect_company("ＯＣＮ光の請求書") == CompanyType.NTT_DOCOMO_BIZ

    # Case 4: SoftBank
    def test_softbank_english(self):
        assert detect_company("SoftBankの携帯料金") == CompanyType.SOFTBANK

    def test_softbank_katakana(self):
        assert detect_company("ソフトバンク固定回線") == CompanyType.SOFTBANK

    # Case 5: フォーバル
    def test_forval_katakana(self):
        assert detect_company("フォーバルテレコムの明細") == CompanyType.FORVAL

    def test_forval_english(self):
        assert detect_company("FORVAL TELECOM請求書") == CompanyType.FORVAL

    # ELSE: その他
    def test_other_unknown(self):
        assert detect_company("KDDI au 携帯料金") == CompanyType.OTHER

    def test_other_empty(self):
        assert detect_company("") == CompanyType.OTHER

    # 優先順位テスト: NTTのOCR結果にOCNが含まれる場合、NTTが先に判定される
    def test_priority_ntt_over_ocn(self):
        text = "NTT東日本 OCN光 with フレッツ利用料"
        assert detect_company(text) == CompanyType.NTT

    def test_priority_order(self):
        # NTTとSoftBank両方含む場合、NTT（Case 1）が優先
        text = "NTT西日本 SoftBank回線"
        assert detect_company(text) == CompanyType.NTT
