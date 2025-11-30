# 포병 계산 프로그램 (C 전용)

`rangeTables/`의 CSV를 읽어 거리/고도차를 반영한 조준각(MILL)과 ETA를 계산하는 순수 C CLI입니다. 별도 런타임이나 Python 의존성이 없습니다.

## 빌드
```bash
gcc -o cli_calculator cli_calculator.c
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
