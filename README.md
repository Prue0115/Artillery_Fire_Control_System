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

## 버전 관리 파일
애플리케이션 버전 문자열은 `afcs/VERSION` 파일에 저장되며, `afcs/versioning.py` 모듈이 이 값을 읽고 갱신합니다.
* `get_version()`은 `afcs/VERSION`이 존재하면 내용을 반환하고, 없을 경우 기본 버전(`1.25.3`)을 기록합니다.
* `update_version()`은 사용자가 입력한 새 버전을 정규화한 뒤 `afcs/VERSION`에 저장하여 GUI 타이틀과 버전 확인 기능에서 활용합니다.
