from openai import AsyncOpenAI

from src.workflow.router import CompanyType
from src.prompts.ntt_prompt import SYSTEM_PROMPT as NTT_PROMPT
from src.prompts.otsuka_prompt import SYSTEM_PROMPT as OTSUKA_PROMPT
from src.prompts.ntt_docomo_prompt import SYSTEM_PROMPT as NTT_DOCOMO_PROMPT
from src.prompts.softbank_prompt import SYSTEM_PROMPT as SOFTBANK_PROMPT
from src.prompts.forval_prompt import SYSTEM_PROMPT as FORVAL_PROMPT
from src.prompts.other_prompt import SYSTEM_PROMPT as OTHER_PROMPT


class AnalysisError(Exception):
    pass


PROMPT_MAP: dict[CompanyType, str] = {
    CompanyType.NTT: NTT_PROMPT,
    CompanyType.OTSUKA: OTSUKA_PROMPT,
    CompanyType.NTT_DOCOMO_BIZ: NTT_DOCOMO_PROMPT,
    CompanyType.SOFTBANK: SOFTBANK_PROMPT,
    CompanyType.FORVAL: FORVAL_PROMPT,
    CompanyType.OTHER: OTHER_PROMPT,
}


async def analyze_bill(
    ocr_text: str,
    company: CompanyType,
    api_key: str,
) -> str:
    """GPT-4.1 で会社別のプロンプトを使い明細を構造化Markdown行に変換する。

    Args:
        ocr_text: OCRで抽出されたテキスト
        company: 判定された会社タイプ
        api_key: OpenAI API Key

    Returns:
        Markdownテーブルのデータ行（ヘッダーなし）

    Raises:
        AnalysisError: 分析処理に失敗した場合
    """
    prompt = PROMPT_MAP[company]

    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": ocr_text},
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        raise AnalysisError(f"明細分析に失敗しました ({company.value}): {e}") from e
