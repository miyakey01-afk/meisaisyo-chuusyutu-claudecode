import base64
import mimetypes

from google import genai
from google.genai import types

from src.prompts.ocr_prompt import SYSTEM_PROMPT


class OCRError(Exception):
    pass


async def ocr_extract(
    files: list[tuple[str, bytes]],
    api_key: str,
) -> str:
    """Gemini 2.5 Flash で PDF/画像からテキストを抽出する。

    Args:
        files: (filename, content_bytes) のリスト
        api_key: Google API Key

    Returns:
        抽出されたテキスト

    Raises:
        OCRError: OCR処理に失敗した場合
    """
    try:
        client = genai.Client(api_key=api_key)

        parts: list[types.Part] = []
        for filename, content in files:
            mime_type = _guess_mime_type(filename)
            parts.append(
                types.Part.from_bytes(data=content, mime_type=mime_type)
            )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=parts,
                ),
            ],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
            ),
        )
        return response.text or ""
    except Exception as e:
        raise OCRError(f"OCR処理に失敗しました: {e}") from e


def _guess_mime_type(filename: str) -> str:
    """ファイル名からMIMEタイプを推測する。"""
    mime, _ = mimetypes.guess_type(filename)
    if mime:
        return mime
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    mapping = {
        "pdf": "application/pdf",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
        "svg": "image/svg+xml",
    }
    return mapping.get(ext, "application/octet-stream")
