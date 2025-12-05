# PC/모바일 빌드 가이드

PC(Windows)용 EXE와 Android APK를 나눠 배포할 때 참고할 수 있는 최소 단계입니다.

> ⚠️ 현재 UI는 Tkinter 기반입니다. Tkinter는 Android에서 기본 지원되지 않으므로, APK를 만들려면 Kivy/Briefcase 등 모바일 런타임으로 포팅해야 합니다. 아래 절차는 "핵심 탄도 계산 로직(afcs 모듈) 재사용 + 모바일 런타임에서 UI 재구성"을 전제로 합니다.

## 공통 준비
- Python 3.10 이상 권장
- 의존성 설치: `pip install -r requirements.txt` (없다면 `pip install pyinstaller requests` 정도면 EXE 빌드는 가능)
- rangeTables, icons, afcs 폴더가 프로젝트 루트에 그대로 있어야 합니다.
- **버전 관리**: `afcs/versioning.py`의 `INITIAL_VERSION` 값을 한 번 수정하면 PC/모바일 빌드가 모두 동일한 버전을 표시합니다.

## 1) Windows EXE 빌드(PyInstaller)
1. PyInstaller 설치: `pip install pyinstaller`
2. 루트 경로에서 실행: `pyinstaller --clean --noconfirm AFCS.spec`
3. 결과물:
   - `dist/AFCS/AFCS.exe` (실행 파일)
   - `dist/AFCS/` 폴더 전체를 배포 패키지로 사용하세요.
4. 빌드 시 테마·폰트·리소스가 포함되도록 `AFCS.spec`에 `datas`가 이미 지정되어 있습니다. 추가 리소스가 생기면 `datas` 섹션에 경로를 더해 주세요.

## 2) Android APK 빌드 개요
Tkinter는 Android에서 직접 구동되지 않아, 모바일 런타임을 사용하는 포팅이 필요합니다. **가장 쉬운 방법은 Kivy + Buildozer**이며, 실제 실행 가능한 예제와 단계는 [`docs/android_build.md`](android_build.md)에 정리했습니다.

### A. Kivy + Buildozer (python-for-android)
- 저장소에 포함된 `mobile/kivy_main.py` 예제를 `buildozer.spec`의 `source.main`에 지정하면 바로 APK를 만들 수 있습니다.
- 핵심 설정: `requirements = python3,kivy,requests`, `source.include_exts = py,json,csv,png,ico` (rangeTables/아이콘 포함).
- 빌드 명령: `buildozer -v android debug` → `bin/*.apk` 생성. **자세한 준비물·설정은 [`docs/android_build.md`](android_build.md) 참고**.

### B. BeeWare Briefcase (Android용 WebView/Toga UI)
1. **Toga UI 포팅**: Tkinter 레이아웃을 Toga 위젯으로 옮기고, 로직 호출은 동일하게 `afcs` 모듈을 사용합니다.
2. **Briefcase 프로젝트 초기화**: `briefcase new --template https://github.com/beeware/briefcase-template.git` 후, 소스에 `afcs`를 포함시키고 Toga 앱 엔트리를 작성합니다.
3. **APK 빌드**: `briefcase create android` → `briefcase build android` → `briefcase run android`로 에뮬레이터/단말 테스트.
4. **장점**: 패키징/서명까지 일괄 처리. **주의**: Toga UI로 재작성 필요.

## 3) PC/모바일 동시 유지 팁
- **공용 로직 분리**: 이미 `afcs` 패키지에 계산·데이터 로직이 들어 있으므로, UI 프레임워크에 의존하지 않도록 신규 모바일 UI에서도 `afcs`만 임포트하여 사용합니다.
- **프로필 재사용**: 모바일 UI에서도 `afcs.device_profile`을 통해 폰트/여백 스케일 값을 재사용할 수 있습니다.
  Android 등 모바일 런타임에서 실행될 때는 별도 설정 없이 자동으로 모바일 프로필을 사용합니다.
- **릴리스 관리**: Windows는 PyInstaller로 빌드한 EXE를, Android는 Kivy/Briefcase로 만든 APK를 각각 GitHub Releases에 업로드하면 됩니다.

필요에 따라 Kivy/Toga용 샘플 엔트리를 추가로 제공해 드릴 수 있습니다. 현재 저장소 상태에서는 위 단계에 따라 UI 포팅 후 빌드를 진행하면 됩니다.
