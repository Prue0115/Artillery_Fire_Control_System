# 포병 계산 프로그램 (C 전용)

`rangeTables/`에 **사용자가 직접 준비한** CSV를 읽어 거리/고도차를 반영한 조준각(MILL)과 ETA를 계산하는 순수 C CLI입니다. 프로그램은 CSV를 만들어 주지 않으므로 데이터를 먼저 채워 넣어야 합니다. 별도 런타임이나 Python 의존성이 없습니다. 모든 CSV를 정렬·검증해 보간하므로 범위만 맞으면 새로 채워 넣은 실측 데이터를 그대로 활용할 수 있습니다.

macOS 네이티브 다이얼로그(osascript)를 활용한 깔끔한 GUI 인스톨러(`installer_gui`)도 함께 제공하여 설치 경로 선택, 시작 화면/바탕화면 바로가기 생성 여부를 손쉽게 지정할 수 있습니다. 다른 OS에서는 동일 흐름을 콘솔 프롬프트로 안내합니다.

## 빌드
### 리눅스/맥 (기본)
```bash
# CLI + 업데이트 도구 + GUI 인스톨러
make

# 각 실행 파일을 개별로 빌드하려면 필요한 소스만 지정
gcc -o cli_calculator cli_calculator.c
gcc -o auto_updater auto_updater.c gui_dialogs.c
gcc -o installer_gui installer_gui.c gui_dialogs.c
```

### 윈도우 EXE (MinGW-w64 크로스 컴파일)
```bash
# MinGW 툴체인이 설치돼 있다면 다음으로 Windows용 exe 3종을 dist/windows/ 아래 생성합니다.
make windows MINGW_PREFIX=x86_64-w64-mingw32

# GitHub Release에 바로 업로드할 zip까지 묶으려면
make zip-windows MINGW_PREFIX=x86_64-w64-mingw32
```
`dist/windows/` 안에는 `cli_calculator.exe`, `auto_updater.exe`, `installer_gui.exe`와 `rangeTables/` 폴더가 함께 담겨
즉시 배포 가능한 상태가 됩니다.

#### `make` 명령이 없을 때 (PowerShell/CMD)
- 기본 Windows 셸에서는 `make`가 없으니 **MSYS2 MinGW64 터미널**에서 실행하거나 `mingw32-make`를 PATH에 추가합니다.
- MSYS2 설치 후: 시작 메뉴에서 "MSYS2 MinGW x64" 터미널을 열고 위의 명령을 그대로 실행하면 됩니다.
- `mingw32-make`만 있는 경우:
  ```bash
  mingw32-make -f Makefile windows MINGW_PREFIX=x86_64-w64-mingw32
  mingw32-make -f Makefile zip-windows MINGW_PREFIX=x86_64-w64-mingw32
  ```
- Chocolatey 등을 통해 `make`를 설치해도 동일하게 동작합니다.

## 사용 방법
```bash
# 사용 가능한 테이블 목록
./cli_calculator --system M109A6 --list

# 거리 5000m, 고도차 +50m(사수-목표), 모든 장약/궤적 결과 출력
./cli_calculator --system M109A6 --distance 5000 --altitude-delta 50

# 현재 빌드 버전 확인
./cli_calculator --version

# 고각 궤적, 장약 3만 대상으로 계산
./cli_calculator --system M109A6 --trajectory high --charge 3 --distance 5000

# 새로 추가된 장비 예시 (Siala, RH-70)
./cli_calculator --system Siala --distance 900
./cli_calculator --system RH-70 --trajectory low --distance 1000

# 업데이트 매니페스트를 받아 새 실행 파일로 교체
./auto_updater --manifest https://example.com/update.json --binary ./cli_calculator

# GUI 인스톨러로 설치한 경우 설치 경로에 auto_updater도 함께 배포되므로 다음처럼 호출할 수 있습니다.
~/Applications/ArtilleryCalculator/auto_updater --manifest https://example.com/update.json --binary ~/Applications/ArtilleryCalculator/cli_calculator

# (Windows) 설치 경로에서 업데이트 실행
C:\\Users\\you\\ArtilleryCalculator\\auto_updater.exe --manifest https://example.com/update.json --binary C:\\Users\\you\\ArtilleryCalculator\\cli_calculator.exe
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
3. 확인 시 `cli_calculator`를 자동 컴파일 후 설치 경로로 복사하고, `rangeTables/`를 함께 배포하며, 더블클릭 가능한 `.command` 런처를 만듭니다. 이미 설치 경로에 동일한 CSV가 있다면 덮어쓰지 않고 건너뜁니다.

macOS에서 실행하면 Finder alias를 사용해 바로가기를 만들어 애플스러운 UI 흐름을 유지합니다. 다른 OS에서는 동일한 질문을 콘솔 프롬프트로 처리합니다.

### 인자 설명
- `--system <이름>`: 필수. CSV 파일명 앞부분(`M109A6`, `M1129`, `M119` 등)과 일치해야 합니다.
- `--distance <m>`: 필수. 미터 단위 거리. 테이블 범위를 벗어나면 가능한 최소·최대 거리를 함께 안내합니다.
- `--trajectory <low|high>`: 선택. 생략 시 해당 시스템의 모든 궤적을 로드합니다.
- `--charge <번호>`: 선택. 특정 장약만 계산하려면 지정합니다.
- `--altitude-delta <m>`: 선택, 기본 0. `사수 고도 - 목표 고도` 값으로 양수면 사수가 더 높습니다.
- `--list`: 선택. 계산 대신 로드된 레인지 테이블 목록만 표시합니다.

## 데이터 형식
- 파일명: `<SYSTEM>_rangeTable_<trajectory>_<charge>.csv`
- 컬럼 순서: `range,mill,diff100m,eta`
- 주어진 `distance`가 표 범위 밖이면 오류 메시지를 표시합니다.

### 지원 장비(예시)
- M109A6: 고각/저각, 장약 0~4
- M1129: 고각, 장약 0~2
- M119: 고각/저각, 장약 0~2
- Siala: 고각/저각, 장약 0
- RH-70: 고각/저각, 장약 0
