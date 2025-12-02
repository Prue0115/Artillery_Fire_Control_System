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

## Qt/C++ 구현

`app.py`의 계산 로직을 그대로 사용할 수 있도록 Qt Widgets 기반의 C++ 애플리케이션을 추가했습니다. Qt Designer에서 편집 가능한 `src/MainWindow.ui`를 포함하며, 동일한 `rangeTables` CSV 데이터를 읽어 고각/저각 해를 계산하고 기록을 남깁니다.

### 빌드 방법

1. Qt 5.15+ 또는 Qt 6.x 위젯 개발 환경을 준비합니다.
2. CMake로 프로젝트를 구성하고 빌드합니다.

```bash
cmake -S . -B build-qt
cmake --build build-qt
```

생성된 실행 파일은 `build-qt/AFCSQt`에서 확인할 수 있으며, 실행 디렉터리에 `rangeTables` 폴더가 함께 있어야 합니다.
