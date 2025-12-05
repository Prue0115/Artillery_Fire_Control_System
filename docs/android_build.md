# Android APK 빌드 실전 가이드(Buildozer)

모바일에서 EXE를 실행할 수 없으므로, 이 저장소의 **탄도 계산 로직(afcs 패키지)**은 그대로 재사용하고 UI는 Kivy로 교체해 APK를 빌드합니다. 아래 단계만 따라 하면 `bin/*.apk`가 생성됩니다.

## 0) 사전 준비
- **권장 환경**: Ubuntu 22.04+ (WSL2 포함) — macOS에서도 가능하지만 Android SDK 설치 시간이 길어집니다.
- **필수 시스템 패키지**
  ```bash
  sudo apt update
  sudo apt install -y git zip unzip openjdk-17-jdk python3-pip python3-venv \
      build-essential libssl-dev libffi-dev libsqlite3-dev zlib1g-dev \
      libncurses5-dev libbz2-dev libreadline-dev liblzma-dev
  ```
- **Python 의존성**: 가상환경을 만들고 Buildozer/Kivy를 설치합니다.
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install --upgrade buildozer Cython kivy
  ```
  > Buildozer는 Android SDK/NDK를 자동으로 내려받습니다. 내부 캐시가 `~/.buildozer`에 쌓이므로 10GB 이상 여유 공간을 확보하세요.

## 1) 샘플 Kivy 엔트리 배치
- 리포지토리 루트에 있는 `mobile/kivy_main.py`는 `afcs` 로직을 사용하는 단순 Kivy UI 예시입니다.
- 스피너에서 장비(M109A6 등)와 탄도 궤적(`high`/`low`)을 고르고, 거리·고도 차이를 입력 후 **계산**을 누르면 `rangeTables` 기반으로 사격 제원을 계산합니다.
- 필요에 맞게 UI를 수정해도 되지만, APK를 빠르게 만들려면 그대로 사용해도 됩니다.

## 2) buildozer.spec 작성
`buildozer init`을 실행하면 기본 `buildozer.spec`가 생성됩니다. 핵심 설정만 아래처럼 수정하세요.
```ini
[app]
title = AFCS
package.name = afcs
package.domain = org.example
# Kivy 엔트리 파일을 지정 (저장소에 포함된 예시 경로)
source.dir = .
source.main = mobile/kivy_main.py
requirements = python3,kivy,requests
# rangeTables/아이콘/코드 확장자를 포함
source.include_exts = py,json,csv,png,ico
# 앱 실행 시 사용할 아이콘이 있다면 경로 지정
icon.filename = icons/AFCS_ICON.ico

[buildozer]
log_level = 2
warn_on_root = 1
```
> **중요:** `rangeTables` 디렉터리가 그대로 포함되어야 계산이 동작합니다. 위 `source.include_exts`가 있으면 Buildozer가 `.csv`를 자동으로 패키징합니다.

## 3) APK 빌드
```bash
# 가상환경이 켜져 있는 상태에서
buildozer -v android debug
```
- 처음 실행 시 Android SDK/NDK, 플랫폼 도구를 다운로드합니다(시간이 오래 걸립니다).
- 빌드가 끝나면 `bin/afcs-*-debug.apk`가 생성됩니다. 실제 파일명은 앱/버전에 따라 달라질 수 있습니다.

## 4) 단말에 설치/테스트
```bash
# USB 디버깅이 켜진 실제 안드로이드 기기가 연결되어 있을 때
buildozer android deploy run
```
- 에뮬레이터를 쓰려면 `adb devices`로 인식되는 상태여야 합니다.

## 5) FAQ
- **서명된 릴리스 APK가 필요하면?** `buildozer android release` 후 `jarsigner`/`apksigner`로 서명하거나, Buildozer의 `android.release_keystore` 설정을 추가합니다.
- **다른 파이썬 패키지가 필요할 때?** `requirements` 줄에 쉼표로 추가하세요. 네이티브 종속성이 있는 경우 Buildozer 문서의 레시피를 참고합니다.
- **아이콘/스플래시 변경**: `icon.filename`, `presplash.filename`에 원하는 이미지를 넣고 `.png`를 권장합니다.
- **템플릿 커스터마이즈**: 더 복잡한 UI가 필요하면 `mobile/kivy_main.py`를 분할하거나 Kivy KV 레이아웃 파일을 추가한 뒤 `source.include_exts`에 `kv`를 넣어 주세요.
