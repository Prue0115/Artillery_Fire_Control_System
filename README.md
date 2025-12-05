# 📝소개
AFCS는 복잡한 탄도 계산을 누구나 쉽게 다룰 수 있도록 설계된 사격 제원 계산 프로그램입니다.
직관적인 인터페이스에서 장비를 선택하고 값을 입력하면, 필요한 각종 제원이 자동 계산되어 바로 확인할 수 있습니다.
<img width="567" height="608" alt="image" src="https://github.com/user-attachments/assets/c3a35b88-c849-433c-a538-495d129dd512" />

# 🎯 주요 애플리케이션 시나리오
1) 사격 제원 산출을 위한 탄도 계산
사용자는 목표 지점까지의 거리·고도·풍향 등 필요한 데이터를 입력하면,
AFCS는 rangeTables 기반의 탄도 데이터를 참조해 최적의 포각·장약·예상 등을 즉시 계산합니다.

2) 장비(포) 목록을 기반으로 한 즉각적 설정 전환
장비를 선택하기만 하면 해당 장비에 맞는 파라미터로 자동 전환됩니다.

3) 작업 기록(Log) 관리 및 반복 계산 지원
AFCS는 입력값·계산 결과 자동으로 기록 UI에 저장합니다.
이를 통해 사용자는 다음과 같은 작업을 수행할 수 있습니다:
- 이전 계산 결과 재확인
- 동일 조건 반복 작업 시 빠른 재사용
- 임무 별 기록 관리
기록은 UI 테마와 통일된 형태로 보여져 가독성이 좋고, 빠르게 스크롤·검색할 수 있습니다.

4) 사거리표(rangeTables) 기반의 데이터 연동 계산
AFCS는 정적 파일로 제공되는 rangeTables 디렉토리 내 데이터를 자동 불러와 사용합니다.
이를 통해 다음을 수행할 수 있습니다
- 탄종 및 장약별 사거리 데이터 자동 매칭

5) 테마(라이트/다크) 변경을 통한 가시성 향상
작업 환경이 실내·야간 등 시시각각 변화할 수 있는 점을 고려해
AFCS는 라이트/다크 테마를 즉시 전환할 수 있습니다.
- 밝은 환경 → 라이트 테마로 시인성 확보
- 야간 또는 어두운 환경 → 다크 테마로 눈부심 최소화

6) 데스크톱·모바일 레이아웃 자동 적용
PC에서는 데스크톱 프로필이 기본 적용되고, Android 등 모바일 런타임에서는 자동으로 모바일 프로필이 적용됩니다. 별도의 선택 코드는 더 이상 필요 없습니다.

7) GitHub Releases 기반 업데이트 확인
프로그램 실행 시 자동으로 GitHub API를 조회하여 최신 버전이 있는지 확인합니다.
사용자는 다음을 즉시 알 수 있습니다
- 최신 릴리스 버전
- 다운로드 링크
- 업데이트 필요 여부
 - 데스크톱(Tkinter)과 모바일(Kivy) 진입점 모두 같은 `afcs/versioning.py`의 버전 문자열을 참조하므로,
   빌드 타겟을 나눠도 동일한 버전이 표시됩니다. 버전을 올릴 때는 `afcs/versioning.py`의 `INITIAL_VERSION`
   값을 한 번만 수정하면 PC/모바일 빌드가 모두 같은 값을 읽습니다.

# 🔧 설치 및 사용
**다운로드 및 설치**
1. [릴리스 페이지](https://github.com/Prue0115/Artillery_Fire_Control_System/releases)
2. AFCS.exe 실행하세요

**사용 방법**
1. 프로그램을 실행하면 메인 화면이 표시됩니다.
2. 장비 목록에서 사용할 장비를 선택합니다.
3. My ALT(m) 사수고도, Target ALT(m) 목표의 고도, Distance (m) 사수-목표물 거리 입력을 합니다.
4. 계산 버튼을 누르면 사격 제원이 즉시 출력됩니다.
5. 계산 결과는 장비 기준으로 자동 분류되어 기록(Log) 탭에 저장됩니다.

<img width="1092" height="612" alt="image" src="https://github.com/user-attachments/assets/36aab6f0-13b2-4e2e-899d-03277b0189f8" />

# 🛠️ PC/모바일 빌드 가이드

모바일(예: Android)에서는 Windows용 EXE를 바로 실행할 수 없습니다. PC용(EXE)과 모바일용(APK)을 나눠 배포하려면 다음 문서를 참고하세요.

- **데스크톱 EXE**: PyInstaller로 패키징하는 방법을 포함.
- **모바일 APK**: Tkinter는 Android에서 기본 미지원이므로, `afcs` 핵심 로직을 재사용하면서 Kivy/Briefcase 등 모바일 런타임으로 포팅해 APK를 만드는 절차 요약.
- **Android 빌드 상세**: Buildozer용 예제 엔트리(`mobile/kivy_main.py`)와 `buildozer.spec` 설정 예시는 [`docs/android_build.md`](docs/android_build.md) 참고.

## 📱 Android APK 빌드 빠른 요약
1. **준비**: Ubuntu/WSL2에서 가상환경 생성 후 `pip install --upgrade buildozer Cython kivy` 실행.
2. **엔트리 지정**: 루트에 있는 `mobile/kivy_main.py`를 `buildozer.spec`의 `source.main`으로 설정하고, `requirements = python3,kivy,requests`와 `source.include_exts = py,json,csv,png,ico`로 리소스를 포함.
3. **빌드**: 가상환경을 활성화한 상태에서 `buildozer -v android debug` 실행 → 완료되면 `bin/*.apk`가 생성됩니다.
4. **배포/테스트**: `buildozer android deploy run`으로 USB 디버깅된 기기에 설치하거나, 생성된 APK를 직접 배포하세요.

자세한 설정 옵션과 문제 해결 방법은 [`docs/android_build.md`](docs/android_build.md)에서 단계별로 확인할 수 있습니다.

➡️ 자세한 단계는 [`docs/build_targets.md`](docs/build_targets.md)에서 확인하세요.

## 🧪 코드 검사
프로젝트 전체를 빠르게 문법 검사하려면 아래 스크립트를 실행하세요.

```bash
./scripts/run_checks.sh
```

`python -m compileall`을 통해 데스크톱/모바일 엔트리포인트와 공용 로직이 모두 컴파일되는지 확인합니다.

