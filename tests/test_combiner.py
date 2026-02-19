import pytest

from src.combiner.markdown_combiner import (
    HEADER,
    SEPARATOR,
    EmptyResultError,
    combine_markdown_rows,
)
from src.workflow.router import CompanyType


class TestCombineMarkdownRows:
    def test_single_company(self):
        results = {
            CompanyType.NTT: "| 03-1234-5678 | 基本料 | 1800 | 2025年7月分 |",
        }
        output = combine_markdown_rows(results)
        assert output.startswith(f"{HEADER}\n{SEPARATOR}\n")
        assert "| 03-1234-5678 | 基本料 | 1800 | 2025年7月分 |" in output

    def test_multiple_companies(self):
        results = {
            CompanyType.NTT: "| 03-1234-5678 | 基本料 | 1800 |  |",
            CompanyType.SOFTBANK: "| 090-1111-2222 | 通話料 | 500 |  |",
        }
        output = combine_markdown_rows(results)
        lines = output.strip().splitlines()
        # Header + separator + 2 data lines
        assert len(lines) == 4
        # NTT comes before SoftBank (order preserved)
        assert "03-1234-5678" in lines[2]
        assert "090-1111-2222" in lines[3]

    def test_empty_results_skipped(self):
        results = {
            CompanyType.NTT: "",
            CompanyType.OTSUKA: "  ",
            CompanyType.SOFTBANK: "| 090-0000-0000 | 基本料 | 1000 |  |",
        }
        output = combine_markdown_rows(results)
        lines = output.strip().splitlines()
        assert len(lines) == 3  # Header + separator + 1 data line

    def test_all_empty_raises(self):
        with pytest.raises(EmptyResultError):
            combine_markdown_rows({})

    def test_all_whitespace_raises(self):
        with pytest.raises(EmptyResultError):
            combine_markdown_rows({CompanyType.NTT: "  ", CompanyType.OTHER: ""})
