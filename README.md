# AFCS – Artillery Fire Control System


✔ 1. Range Table 기반 조준각(MILL) & ETA 계산

장비별 Range Table CSV(rangeTables/)을 읽어 다음 값을 계산합니다:

MILL (조준각)

ETA (탄착 예상 시간)

diff100m(고도 보정 계수)

CH(장약)

거리·고도차를 입력하면 프로그램이 자동으로 해당 거리 구간의 데이터를 찾고,
다음 보간 방식으로 정확한 값을 계산합니다:

2. LOW / HIGH 궤적에 따른 장약별 다중 솔루션 출력
고도차는 자동 계산됩니다.
altitude_delta = my_alt - target_alt
이를 기반으로:
MILL_final = MILL_base + (altitude_delta / 100) * diff100m

4. GUI 기반 직관적 조작 (Tkinter)
프로그램은 완전한 GUI를 제공하여 누구나 쉽게 사용할 수 있습니다.

포함 요소

장비 선택 콤보박스

입력 필드 (My ALT / Target ALT / Distance)

계산 버튼

LOW/HIGH 결과 테이블

고도차 표시

계산 기록(Log) 패널(토글 가능)

5. 계산 기록(Log) 기능

모든 계산은 자동으로 로그에 저장됩니다:

시간(HH:MM)

장비명

사수 고도 / 목표 고도 / 거리

LOW / HIGH 솔루션

최대 3개 솔루션 표시
