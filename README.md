# 포병 계산 프로그램

M109A6, M1129, M119 레인지 테이블(`rangeTables/`)을 읽어 저각/고각 포각, ETA, 장약을 자동으로 계산하는 간단한 GUI 도구입니다. 타격지점과 사수의 고도 차이를 고려한 보정도 함께 적용합니다.

## 실행 방법

```bash
python app.py
```

## 사용 방법
1. **나의 고도**, **타격 지점 고도**, **거리(미터)**를 입력합니다. 고도 차이는 `사수 고도 - 타격 지점 고도`로 자동 계산됩니다 (목표가 더 높으면 음수).
2. 상단 장비 선택에서 **M109A6**, **M1129**, **M119**, **RH-70**, **siala** 중 하나를 고릅니다.
3. `계산` 버튼을 누르면 고도 차이를 반영한 저각/고각 포각, ETA, 선택된 장약이 각각 최대 3가지 방법으로 표시됩니다.

## 데이터
- `rangeTables/` 폴더의 `M109A6_rangeTable_low_*.csv`, `M109A6_rangeTable_high_*.csv`를 자동으로 불러와 거리에 맞는 장약을 선택합니다.
- `rangeTables/` 폴더의 `M1129_rangeTable_high_0.csv`, `M1129_rangeTable_high_1.csv`, `M1129_rangeTable_high_2.csv`로 M1129 고각 사격을 지원합니다. (M1129 지원은 기존 데이터와 동일하게 동작합니다.)
- `rangeTables/` 폴더의 `M119_rangeTable_low_*.csv`, `M119_rangeTable_high_*.csv`를 사용자 제공 데이터로 추가하면 M119 저각/고각 계산을 지원합니다. 파일명을 기준으로 장약 번호를 자동 감지하므로 필요한 데이터만 넣으면 됩니다.
- `rangeTables/` 폴더의 `RM70_rangeTable_low_*.csv`, `RM70_rangeTable_high_*.csv`를 사용해 **RH-70** 장비를 지원합니다. 파일명에서 장약 번호를 자동으로 감지합니다.
- `rangeTables/` 폴더의 `siala_rangeTable_low_*.csv`, `siala_rangeTable_high_*.csv`를 사용해 **siala** 장비를 지원합니다. 파일명에서 장약 번호를 자동으로 감지합니다.
