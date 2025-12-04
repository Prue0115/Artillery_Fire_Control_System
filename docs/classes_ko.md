# 클래스 설명 (한국어)

이 문서는 AFCS 코드베이스에 정의된 핵심 클래스들을 한국어로 설명합니다. 각 클래스는 위치, 역할, 주요 속성과 메서드를 함께 정리하여 장비 추가나 유지보수 시 참고할 수 있도록 구성했습니다.

## afcs/equipment/base.py

### `Equipment`
* **개요**: 장비별 메타데이터와 사격 표(CSV) 경로를 관리하는 데이터 클래스.
* **주요 속성**
  | 이름 | 유형 | 설명 |
  | --- | --- | --- |
  | `name` | `str` | 내부 식별자(예: `M109A6`). |
  | `prefix` | `str` | 사격 표 파일명과 디렉터리 명 앞에 붙는 짧은 접두어. |
  | `display_name` | `Optional[str]` | UI에 노출할 이름. 지정하지 않으면 `name`을 사용. |
  | `charges_override` | `Dict[str, Optional[List[int]]]` | 특정 탄도(`trajectory`)별로 허용하는 장약 목록을 덮어쓸 때 사용. |
* **주요 메서드**
  | 이름 | 설명 |
  | --- | --- |
  | `label` | `display_name`이 있으면 이를, 없으면 `name`을 반환하여 화면 표시용 문자열을 제공합니다. |
  | `range_table_dir` | 해당 장비의 사격 표 CSV를 보관할 기본 디렉터리 경로를 반환합니다. |
  | `ensure_range_table_dir` | 사격 표 디렉터리를 생성(없으면)하고 경로를 반환합니다. 장비가 발견될 때마다 호출되어 폴더 구조를 자동으로 준비합니다. |

## afcs/equipment/registry.py

### `EquipmentRegistry`
* **개요**: `afcs.equipment` 패키지 내부의 장비 모듈을 동적으로 스캔하여 `Equipment` 인스턴스를 수집·정렬하고, 장비 목록을 조회할 수 있게 합니다.
* **주요 속성**
  | 이름 | 유형 | 설명 |
  | --- | --- | --- |
  | `_package` | `str` | 장비 모듈을 import할 때 사용할 패키지 경로(`afcs.equipment`). |
  | `_root` | `Path` | 장비 모듈이 위치한 실제 디렉터리 경로. |
  | `_equipments` | `Dict[str, Equipment]` | 장비 이름을 키로 한 등록된 장비 사전. 항상 이름 기준으로 정렬된 상태를 유지합니다. |
* **주요 메서드**
  | 이름 | 설명 |
  | --- | --- |
  | `refresh()` | 패키지를 다시 스캔하여 새로 추가되거나 삭제된 장비 모듈을 반영합니다. 장비가 발견되면 `ensure_range_table_dir`를 호출해 폴더를 준비합니다. |
  | `equipments` | 등록된 모든 `Equipment` 객체 리스트를 반환합니다. |
  | `names` | 장비 이름 목록만 반환합니다. |
  | `get(name)` | 이름으로 특정 장비를 선택적으로 반환합니다. 없으면 `None`. |
  | `__iter__()` | 레지스트리를 반복(iterate)할 수 있게 해 등록된 장비들을 순회 가능하게 합니다. |

## afcs/range_tables.py

### `RangeTable`
* **개요**: 특정 장비, 포탄 궤적(`trajectory`), 장약(`charge`) 조합에 대한 사격 표 CSV를 읽어 보간 계산을 제공하는 클래스.
* **주요 속성**
  | 이름 | 유형 | 설명 |
  | --- | --- | --- |
  | `equipment` | `Equipment` | 사격 표가 연결된 장비 객체. |
  | `trajectory` | `str` | 탄도 유형(예: `high`, `low`). |
  | `charge` | `int` | 장약 번호. |
  | `path` | `Path` | 조합에 해당하는 CSV 파일 경로(`{prefix}_rangeTable_{trajectory}_{charge}.csv`). |
  | `rows` | `List[Dict[str, float]]` | CSV에서 읽어 들인 거리, 밀, diff100m, ETA 행 목록. |
* **주요 메서드**
  | 이름 | 설명 |
  | --- | --- |
  | `_load_rows()` | CSV를 열어 유효한 수치 데이터만 정제해 `rows`에 채웁니다. |
  | `supports_range(distance)` | 입력 거리가 CSV 데이터 범위 안에 있는지 확인합니다. |
  | `calculate(distance, altitude_delta)` | 주어진 거리와 고도 차로 필요한 `mill`, `eta`, `charge` 값을 계산합니다. 고도 보정은 `diff100m`을 활용한 선형 보간으로 적용합니다. |
  | `_neighbor_rows(distance)` | 거리에 가장 가까운 행을 최대 3개 선택해 보간에 사용할 이웃점을 구성합니다. |
  | `_interpolate(key, distance)` | 선택된 이웃점을 이용해 선형 또는 2차 보간으로 `mill`, `diff100m`, `eta` 등의 값을 계산합니다. |

### 관련 함수
* `available_charges(equipment, trajectory)`: 해당 장비·탄도 조합으로 존재하는 CSV 파일을 스캔해 사용 가능한 장약 번호 목록을 반환합니다.
* `find_solutions(...)`: 주어진 거리/고도 차/탄도에 대해 최대 `limit`개까지 계산 결과를 찾습니다. CSV가 없거나 범위 밖이면 건너뜁니다.
* `find_solution(...)`: `find_solutions`를 1개만 요청해 단일 해를 반환하는 편의 함수입니다.
