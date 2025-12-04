# AFCS – Artillery Fire Control System
AFCS GUI 화면

<img width="588" height="615" alt="image" src="https://github.com/user-attachments/assets/47126343-9d69-4648-a524-c5edc146eaf2" />

장비 목록

<img width="135" height="142" alt="image" src="https://github.com/user-attachments/assets/4f04aeea-7500-4cae-b725-156ab37d273c" />

AFCS GUI 전체
<img width="1139" height="612" alt="image" src="https://github.com/user-attachments/assets/ebf58f19-56c1-467b-8ddf-92297cf7a9bc" />

기록 GUI

<img width="609" height="636" alt="image" src="https://github.com/user-attachments/assets/aae2e894-3169-4d89-8bca-58d9340d0c0d" />

계산 GUI

<img width="569" height="624" alt="image" src="https://github.com/user-attachments/assets/55be4d84-3715-431c-8c77-323bc4bff0cc" />

## 클래스 안내 (한국어)
프로젝트의 주요 클래스 설명은 `docs/classes_ko.md`에서 확인할 수 있습니다.

## 버전 관리
애플리케이션 버전 문자열은 `afcs/versioning.py`에 선언된 기본값(`INITIAL_VERSION`)에서 시작해 메모리에 저장됩니다.
* `get_version()`은 현재 메모리에 기록된 버전(초기값은 `1.25.4`)을 반환합니다.
* `update_version()`은 전달받은 문자열을 정규화한 뒤 런타임 버전을 갱신합니다. 별도의 파일을 생성하지 않으므로 배포 아티팩트가 단순합니다.
* `fetch_latest_release()`는 GitHub 릴리스 API를 조회해 최신 태그 이름과 릴리스 URL을 반환하므로, 외부 업데이트 확인 기능을 구현할 때 활용할 수 있습니다.
  * 릴리스 제목이 `AFCS 1.25.3`, 태그가 `v1.25.3`처럼 접두 텍스트를 포함해도 버전 숫자(`1.25.3`)만 추출해 비교합니다.
