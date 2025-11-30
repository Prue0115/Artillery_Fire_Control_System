# 포병 계산 프로그램 (C 전용)

`rangeTables/`의 CSV를 읽어 거리/고도차를 반영한 조준각(MILL)과 ETA를 계산하는 순수 C CLI입니다. 별도 런타임이나 Python 의존성이 없습니다.

macOS 네이티브 다이얼로그(osascript)를 활용한 깔끔한 GUI 인스톨러(`installer_gui`)도 함께 제공하여 설치 경로 선택, 시작 화면/바탕화면 바로가기 생성 여부를 손쉽게 지정할 수 있습니다. 다른 OS에서는 동일 흐름을 콘솔 프롬프트로 안내합니다.

## 빌드
```bash
gcc -o cli_calculator cli_calculator.c

# GUI 인스톨러 빌드 (macOS 우선)
gcc -o installer_gui installer_gui.c gui_dialogs.c
```

## 사용 방법
```bash
# 사용 가능한 테이블 목록
./cli_calculator --system M109A6 --list

# 거리 5000m, 고도차 +50m(사수-목표), 모든 장약/궤적 결과 출력
./cli_calculator --system M109A6 --distance 5000 --altitude-delta 50

# 고각 궤적, 장약 3만 대상으로 계산
./cli_calculator --system M109A6 --trajectory high --charge 3 --distance 5000
```

### GUI 인스톨러 사용 흐름 (macOS 권장)
```bash
# 빌드
gcc -o installer_gui installer_gui.c gui_dialogs.c

# 실행: 기본값은 ~/Applications/ArtilleryCalculator
./installer_gui
```

실행 후 순서
1. 네이티브 폴더 선택 다이얼로그에서 설치 경로를 지정합니다.
2. 시작 화면/바탕화면 바로가기 생성 여부를 확인합니다.
3. 확인 시 `cli_calculator`를 자동 컴파일 후 설치 경로로 복사하고, `rangeTables/`를 함께 배포하며, 더블클릭 가능한 `.command` 런처를 만듭니다.

macOS에서 실행하면 Finder alias를 사용해 바로가기를 만들어 애플스러운 UI 흐름을 유지합니다. 다른 OS에서는 동일한 질문을 콘솔 프롬프트로 처리합니다.

### 인자 설명
- `--system <이름>`: 필수. CSV 파일명 앞부분(`M109A6`, `M1129`, `M119` 등)과 일치해야 합니다.
- `--distance <m>`: 필수. 미터 단위 거리.
- `--trajectory <low|high>`: 선택. 생략 시 해당 시스템의 모든 궤적을 로드합니다.
- `--charge <번호>`: 선택. 특정 장약만 계산하려면 지정합니다.
- `--altitude-delta <m>`: 선택, 기본 0. `사수 고도 - 목표 고도` 값으로 양수면 사수가 더 높습니다.
- `--list`: 선택. 계산 대신 로드된 레인지 테이블 목록만 표시합니다.

## 데이터 형식
- 파일명: `<SYSTEM>_rangeTable_<trajectory>_<charge>.csv`
- 컬럼 순서: `range,mill,diff100m,eta`
- 주어진 `distance`가 표 범위 밖이면 오류 메시지를 표시합니다.
