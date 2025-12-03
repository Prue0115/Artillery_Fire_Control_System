import importlib
import pkgutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .base import Equipment


class EquipmentRegistry:
    """패키지 내부의 장비 정의를 동적으로 탐색합니다."""

    def __init__(self):
        self._package = __package__
        self._root = Path(__file__).parent
        self._equipments: Dict[str, Equipment] = {}
        self.refresh()

    def refresh(self):
        """패키지 내 장비 모듈을 다시 스캔합니다."""
        equipments: Dict[str, Equipment] = {}
        for module_info in pkgutil.iter_modules([str(self._root)]):
            if module_info.name.startswith("__") or module_info.name in {"base", "registry"}:
                continue
            module = importlib.import_module(f"{self._package}.{module_info.name}")
            equipment = getattr(module, "EQUIPMENT", None)
            if isinstance(equipment, Equipment):
                equipments[equipment.name] = equipment
                equipment.ensure_range_table_dir()
        self._equipments = dict(sorted(equipments.items(), key=lambda item: item[0]))

    @property
    def equipments(self) -> List[Equipment]:
        return list(self._equipments.values())

    @property
    def names(self) -> List[str]:
        return list(self._equipments.keys())

    def get(self, name: str) -> Optional[Equipment]:
        return self._equipments.get(name)

    def __iter__(self) -> Iterable[Equipment]:
        return iter(self._equipments.values())
