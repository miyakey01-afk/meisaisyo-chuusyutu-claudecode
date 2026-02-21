# 明細抽出くん Ver2 実装計画書

## 1. 概要

### 1.1 アプリケーション名
**明細抽出くん Ver2（ノード分岐）**

### 1.2 目的
各社の電話料金明細書（PDF/画像）をアップロードすると、OCRでテキスト化した後、
会社ごとに専用の抽出ロジックで明細データを構造化し、最終的にExcel（XLSX）ファイルとして出力する。

### 1.3 元のDSLワークフロー構造（Dify）

```
[ユーザー入力] → [OCR (Gemini)] → [IF/ELSE 会社判定] → [会社別LLM明細分析 ×6] → [テンプレート結合] → [XLSX変換] → [出力]
                                                                                                        ↘ [エラー処理] → [出力2]
```

---

## 2. DSLワークフロー詳細分析

### 2.1 ノード一覧

| # | ノードID | ノード名 | タイプ | 説明 |
|---|----------|----------|--------|------|
| 1 | 1763681358412 | ユーザー入力 | start | ファイルアップロード（PDF/画像、最大10枚） |
| 2 | 1763681364596 | OCR | llm (gemini-2.5-flash) | PDF/画像→テキスト変換 |
| 3 | 1764739779573 | IF/ELSE | if-else | OCRテキストから会社名を判定し分岐 |
| 4 | 1764727102859 | NTT明細分析 | llm (gpt-4.1) | NTT東日本/西日本/コミュニケーションズ |
| 5 | 1764727111543 | 大塚商会 明細分析 | llm (gpt-4.1) | 大塚商会 |
| 6 | 1764734254088 | NTTドコモビジネス 明細分析 | llm (gpt-4.1) | NTTドコモビジネス/OCN |
| 7 | 1764734260045 | SoftBank 明細分析 | llm (gpt-4.1) | SoftBank/ソフトバンク |
| 8 | 1764734264633 | フォーバルテレコム 明細分析 | llm (gpt-4.1) | フォーバルテレコム/FORVAL |
| 9 | 1764734382655 | その他の会社 明細分析 | llm (gpt-4.1) | 上記以外の会社 |
| 10 | 1764728717913 | テンプレート結合 | template-transform | 各社の結果をMarkdown表に結合 |
| 11 | 1763682786853 | Markdown to XLSX | tool (md_exporter) | Markdown表→XLSXファイル変換 |
| 12 | 1763681480401 | 出力 | end | 正常終了（XLSXファイル） |
| 13 | 1764721294262 | エラーテンプレート | template-transform | エラーメッセージ生成 |
| 14 | 1764721117324 | 出力2 | end | エラー終了 |

### 2.2 会社判定ロジック（IF/ELSE条件）

| 分岐 | 条件（OR） | ルーティング先 |
|------|-----------|---------------|
| Case 1 | テキストに「NTT東日本」「NTT西日本」「NTT Communications」のいずれかを含む | NTT明細分析 |
| Case 2 | テキストに「大塚商会」を含む | 大塚商会 明細分析 |
| Case 3 | テキストに「NTTドコモビジネス」「docomo Business」「OCN」「ＯＣＮ」のいずれかを含む | NTTドコモビジネス 明細分析 |
| Case 4 | テキストに「SoftBank」「ソフトバンク」のいずれかを含む | SoftBank 明細分析 |
| Case 5 | テキストに「フォーバル」「FORVAL」のいずれかを含む | フォーバルテレコム 明細分析 |
| ELSE | 上記いずれにも該当しない | その他の会社 明細分析 |

### 2.3 共通出力フォーマット

各社のLLMノードは全て同じ4列Markdownテーブル行を出力する：

```
| 番号 | サービス | 金額(円) | 備考 |
```

- **番号**: 電話番号、契約番号、機種名など（会社による）
- **サービス**: 料金項目名
- **金額(円)**: カンマなし半角数字（マイナスは`-1234`形式）
- **備考**: 利用期間、設置住所など

### 2.4 テンプレート結合ロジック

Jinja2テンプレートで各社の出力行を結合し、ヘッダー行を付加：

```jinja2
| 番号 | サービス | 金額(円) | 備考 |
| --- | --- | --- | --- |
{%- if ntt_rows is string and ntt_rows|trim != '' %}
{{ ntt_rows }}
{%- endif %}
{%- if otsuka_rows is string and otsuka_rows|trim != '' %}
{{ otsuka_rows }}
{%- endif %}
... (各社同様)
```

### 2.5 エラーハンドリング

全LLMノードおよびXLSX変換ツールには `fail-branch` が設定されており、
失敗時は以下のエラーメッセージを返す：

> ファイルの処理に失敗しました。
> PDFや画像の容量が大きすぎる、またはページ数が多すぎる可能性があります。
> - ファイルを圧縮する
> - PDFを数ページごとに分割してアップロード
> - 画像のファイルサイズを小さくする

---

## 3. 実装計画

### 3.1 技術スタック

| 項目 | 技術 | 理由 |
|------|------|------|
| 言語 | Python 3.11+ | LLM API連携・データ処理に適切 |
| Webフレームワーク | FastAPI | 非同期処理対応、軽量、APIファースト |
| フロントエンド | Streamlit または HTML/JS | プロトタイプにはStreamlit、本番にはHTML/JS |
| OCR用LLM | Google Gemini API (gemini-2.5-flash) | 元DSLと同じ。Vision対応、高速 |
| 明細分析用LLM | OpenAI API (gpt-4.1) | 元DSLと同じ。テキスト分析に高精度 |
| Excel出力 | openpyxl | Markdown表→XLSX変換 |
| PDF処理 | PyMuPDF (fitz) | PDF→画像変換（OCR前処理用） |

### 3.2 ディレクトリ構成

```
meisaisyo-chuusyutu-claudecode/
├── docs/
│   └── implementation-plan.md    # 本ファイル
├── src/
│   ├── __init__.py
│   ├── main.py                   # エントリポイント（FastAPI or Streamlit）
│   ├── config.py                 # 設定・環境変数管理
│   ├── workflow/
│   │   ├── __init__.py
│   │   ├── pipeline.py           # ワークフロー全体の制御
│   │   ├── ocr.py                # OCRノード（Gemini API）
│   │   ├── router.py             # IF/ELSE 会社判定ロジック
│   │   └── analyzer.py           # 会社別明細分析（OpenAI API）
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── ocr_prompt.py         # OCR用プロンプト
│   │   ├── ntt_prompt.py         # NTT東日本/西日本/コミュニケーションズ用
│   │   ├── otsuka_prompt.py      # 大塚商会用
│   │   ├── ntt_docomo_prompt.py  # NTTドコモビジネス用
│   │   ├── softbank_prompt.py    # SoftBank用
│   │   ├── forval_prompt.py      # フォーバルテレコム用
│   │   └── other_prompt.py       # その他の会社用
│   ├── templates/
│   │   ├── __init__.py
│   │   └── markdown_combiner.py  # テンプレート結合ロジック
│   └── export/
│       ├── __init__.py
│       └── xlsx_exporter.py      # Markdown表→XLSX変換
├── tests/
│   ├── __init__.py
│   ├── test_router.py            # 会社判定ロジックのテスト
│   ├── test_combiner.py          # テンプレート結合のテスト
│   └── test_xlsx_exporter.py     # XLSX変換のテスト
├── requirements.txt
├── .env.example                  # 環境変数テンプレート
└── 【1008】明細抽出くん Ver2（ノード分岐） (3).yml  # 元DSLファイル
```

### 3.3 実装ステップ

#### Phase 1: 基盤構築

**Step 1.1: プロジェクト初期設定**
- `requirements.txt` の作成
- `.env.example` の作成（API Key設定）
- `config.py` で環境変数をロード

**Step 1.2: 会社判定ロジック（`router.py`）**
- DSLの IF/ELSE 条件をPythonの関数として実装
- OCRテキストから会社名キーワードを検索
- 対応する会社タイプ（enum）を返す
- **ユニットテスト作成**

```python
class CompanyType(Enum):
    NTT = "ntt"                   # NTT東日本/西日本/コミュニケーションズ
    OTSUKA = "otsuka"             # 大塚商会
    NTT_DOCOMO_BIZ = "ntt_docomo" # NTTドコモビジネス/OCN
    SOFTBANK = "softbank"         # SoftBank
    FORVAL = "forval"             # フォーバルテレコム
    OTHER = "other"               # その他

def detect_company(ocr_text: str) -> CompanyType:
    """OCRテキストから会社を判定する"""
    ...
```

#### Phase 2: LLM連携

**Step 2.1: OCRノード（`ocr.py`）**
- Gemini API (gemini-2.5-flash) を使用
- PDF/画像ファイルをAPI に送信
- Vision機能でテキスト抽出
- エラー時はfail-branch相当の例外を送出

```python
async def ocr_extract(files: list[UploadFile]) -> str:
    """ファイルリストからOCRテキストを抽出"""
    ...
```

**Step 2.2: 会社別明細分析（`analyzer.py`）**
- OpenAI API (gpt-4.1) を使用
- 会社タイプに応じたプロンプトを選択
- Markdownテーブル行を返却
- エラー時はfail-branch相当の例外を送出

```python
async def analyze_bill(ocr_text: str, company: CompanyType) -> str:
    """会社別プロンプトで明細を分析し、Markdown行を返す"""
    ...
```

**Step 2.3: プロンプト定義（`prompts/`）**
- DSL内の各LLMノードのsystemプロンプトをそのままPythonファイルに転記
- 6社分 + OCR用 = 計7ファイル

#### Phase 3: 出力処理

**Step 3.1: テンプレート結合（`markdown_combiner.py`）**
- 各社の分析結果（Markdown行）を結合
- ヘッダー行を付加
- 空の結果はスキップ

```python
def combine_markdown_rows(results: dict[CompanyType, str]) -> str:
    """各社の結果をMarkdownテーブルに結合"""
    ...
```

**Step 3.2: XLSX変換（`xlsx_exporter.py`）**
- Markdownテーブル文字列をパース
- openpyxlでXLSXファイルを生成
- 出力ファイル名: 「明細書EXCEL出力.xlsx」

```python
def markdown_to_xlsx(markdown_table: str, filename: str = "明細書EXCEL出力") -> bytes:
    """Markdownテーブルを受け取り、XLSXバイナリを返す"""
    ...
```

#### Phase 4: ワークフロー統合

**Step 4.1: パイプライン構築（`pipeline.py`）**
- 全ノードを順番に呼び出すパイプラインを構築
- エラーハンドリング（fail-branch相当）を実装
- 処理フロー:

```
1. ファイル受信
2. OCR実行（Gemini）
3. 会社判定（IF/ELSE）
4. 明細分析（会社別LLM）
5. テンプレート結合
6. XLSX変換
7. ファイル返却 or エラーメッセージ返却
```

**Step 4.2: エラーハンドリング**
- 各ステップで例外が発生した場合、DSLと同じエラーメッセージを返す
- リトライ機構は必要に応じて追加（元DSLではmax_retries: 3）

#### Phase 5: UI/API

**Step 5.1: APIエンドポイント（FastAPI）**
```python
@app.post("/extract")
async def extract_bill(files: list[UploadFile]):
    """明細書ファイルを受け取り、XLSXファイルを返す"""
    ...
```

**Step 5.2: Streamlit UI（オプション）**
- ファイルアップロード画面
- 処理状況の表示
- XLSXダウンロードボタン

#### Phase 6: テスト

- `test_router.py`: 会社判定ロジックのテスト（キーワードマッチング）
- `test_combiner.py`: テンプレート結合のテスト（空行除外、ヘッダー付加）
- `test_xlsx_exporter.py`: XLSX変換のテスト（Markdown→Excel変換の正確性）

---

## 4. 会社別プロンプト要約

### 4.1 NTT東日本/西日本/コミュニケーションズ
- **対象**: 電話基本料、オプション（ナンバーディスプレイ、転送電話等）、フレッツ光関連
- **番号**: `0X-XXXX-XXXX` 形式の電話番号
- **除外**: 消費税、ユニバーサルサービス料、小計、合計
- **備考**: 利用期間

### 4.2 大塚商会
- **対象**: 3パターン — A.電話料金明細、B.保守サービス（たよれーる等）、C.複合機（カウンタ料金等）
- **番号**: A=電話番号、B=伝票番号、C=機種名
- **特殊**: B は1行に集約可能、C は単価・カウント情報を備考に記載

### 4.3 NTTドコモビジネス
- **対象**: OCN回線、光フレッツ基本料、メールウイルスチェック等
- **番号**: OCN契約番号（例: N170090928）
- **備考**: 設置住所優先、なければ請求月

### 4.4 SoftBank
- **対象**: 基本料、定額料、データ定額、通話料、オプションサービス
- **番号**: 回線番号/携帯電話番号
- **除外**: ポイント調整行

### 4.5 フォーバルテレコム
- **対象**: 【会社名】で囲まれたグループ単位で抽出
- **番号**: グループ見出しの【】内テキスト
- **特殊**: 値引き・調整金はマイナス表記

### 4.6 その他の会社
- **対象**: 汎用的な抽出ルール
- **番号**: 特定できない場合は空欄可

---

## 5. データフロー図

```
┌─────────────┐
│ ユーザー入力  │  PDF/画像ファイル（最大10枚）
│ (file-list) │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   OCR       │  gemini-2.5-flash (Vision)
│ (Gemini)    │  → テキスト出力
└──────┬──────┘
       │ OCRテキスト
       ▼
┌─────────────┐
│  IF/ELSE    │  会社名キーワードで分岐
│  会社判定    │
└──┬──┬──┬──┬──┬──┬──┘
   │  │  │  │  │  │
   ▼  ▼  ▼  ▼  ▼  ▼
┌────┐┌────┐┌────┐┌────┐┌────┐┌────┐
│NTT ││大塚││ドコ││Soft││フォ ││その│  各社 gpt-4.1
│    ││商会││モBiz││Bank││ーバル││他  │  → Markdown行
└─┬──┘└─┬──┘└─┬──┘└─┬──┘└─┬──┘└─┬──┘
  │     │     │     │     │     │
  └──┬──┴──┬──┴──┬──┴──┬──┴──┬──┘
     │     │     │     │     │
     ▼─────▼─────▼─────▼─────▼
┌──────────────────────┐
│  テンプレート結合      │  Jinja2テンプレートで
│  (Markdown Table)    │  ヘッダー + 各社行結合
└──────────┬───────────┘
           │ Markdown Table
           ▼
┌──────────────────────┐
│  XLSX変換             │  openpyxl
│  (md_to_xlsx)        │  → 明細書EXCEL出力.xlsx
└──────────┬───────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌────────┐  ┌────────┐
│ 出力   │  │ 出力2  │
│(XLSX)  │  │(エラー) │
└────────┘  └────────┘
```

---

## 6. API Key / 環境変数

```env
# .env.example
GOOGLE_API_KEY=your_google_api_key_here      # Gemini API用
OPENAI_API_KEY=your_openai_api_key_here      # GPT-4.1用
OUTPUT_FILENAME=明細書EXCEL出力                # デフォルト出力ファイル名
MAX_FILE_COUNT=10                             # 最大アップロードファイル数
```

---

## 7. 注意事項（元DSLのメモより）

1. **OCR後にIF/ELSEで分岐**: 会社ごとにノードを分けることでエラーを削減
2. **NTT明細とOCNの重複対策**: NTTの明細にOCNが含まれている場合、NTT側では「光 with フレッツ」のみ抽出するようプロンプトで制御
3. **モデル選定**: gpt-4.1が最速だが100Kトークンまでのためページ数が多いとエラーになる可能性あり
4. **画像容量**: 特にiPhoneの高画質画像はエラーが出やすいため、圧縮を推奨

---

## 8. 今後の拡張候補

- [ ] 新しい会社のテンプレートを追加するプラグイン機構
- [ ] バッチ処理（複数ファイルの一括処理）
- [ ] 処理結果のプレビュー画面（Markdown表のプレビュー）
- [ ] 履歴管理・結果のDB保存
- [ ] 認証機能の追加
