from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


# 프로젝트 루트의 rangeTables 디렉터리(장비별 서브폴더 보관)를 가리킨다.
RANGE_TABLE_ROOT = Path(__file__).resolve().parent.parent.parent / "rangeTables"


@dataclass
class Equipment:
    """데이터 파일 경로와 사격 설정을 보유하는 장비 모델."""

    name: str
    prefix: str
    display_name: Optional[str] = None
    charges_override: Dict[str, Optional[List[int]]] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return self.display_name or self.name

    @property
    def range_table_dir(self) -> Path:
        return RANGE_TABLE_ROOT / self.prefix

    def ensure_range_table_dir(self) -> Path:
        path = self.range_table_dir
        path.mkdir(parents=True, exist_ok=True)
        return path
