# 프로젝트 계획: C 기반 포병 계산기

Python 의존성 없이 C만으로 계산기를 제공한다. CLI 단일 바이너리를 중심으로 구축하고, 필요한 경우 나중에 C GUI/네이티브 런처를 추가한다.

## 1. 목표 기능과 대상 환경
- **핵심 기능**: 시스템/궤적/장약별 레인지 테이블을 읽어 거리, 고도차를 반영한 조준각(MILL)과 ETA를 계산.
- **대상 환경**: GCC로 빌드 가능한 리눅스/윈도우 CLI. 별도 런타임 필요 없음.

## 2. 입력값과 출력값
- 입력: system, trajectory(optional), charge(optional), distance, altitude_delta(optional).
- 출력: 선택된 테이블별 base mill, diff100m, 보정 적용 mill, ETA. 지원 범위 밖이면 오류 메시지.

## 3. 데이터 사용
- `rangeTables/*.csv` 파일명 규칙 `<SYSTEM>_rangeTable_<trajectory>_<charge>.csv` 를 그대로 사용.
- CSV 컬럼 순서는 `range,mill,diff100m,eta`로 가정.

## 4. UI 방식
- **CLI**: 인자 기반 호출. `--list`로 사용 가능한 테이블을 안내하고, trajectory/charge 생략 시 가능한 모든 결과를 표시.
- 출력은 텍스트(표 형식)이며 스크립트 연계를 고려해 단순 라인 포맷 유지.

## 5. 구조 및 테스트 초안
- 단일 소스 `cli_calculator.c`에 로직을 두되, 함수로 분리(파일 로딩, 보간, 출력)해 유닛 테스트/확장 용이성 확보.
- 테스트 예시
  - 특정 거리/고도차에서 보간 값이 기대 범위인지 확인(샘플 CSV로).
  - 지원 범위 밖 요청 시 오류 코드 1 반환.
  - `--list`, charge/trajectory 필터링이 올바르게 동작하는지 확인.
