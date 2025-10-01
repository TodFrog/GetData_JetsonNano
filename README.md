
# Jetson Orin 기반 YOLO 데이터셋 이미지 수집기

이 프로젝트는 NVIDIA Jetson Orin/Nano 보드에 연결된 카메라를 사용하여, YOLO와 같은 객체 탐지 모델 학습에 필요한 이미지 데이터셋을 효율적으로 수집하기 위한 Python 스크립트를 제공합니다.

스크립트는 카메라의 라이브 영상을 실시간으로 보여주며, 사용자가 키보드(Enter) 입력을 통해 원하는 시점에 이미지 저장을 시작하고 종료할 수 있는 대화형 인터페이스를 제공합니다.

## ✨ 주요 기능

  * **실시간 영상 확인:** 데이터 수집 중 카메라가 무엇을 보고 있는지 실시간으로 확인할 수 있습니다.
  * **대화형 제어:** 엔터 키를 이용해 이미지 저장을 시작하고, 다시 엔터를 눌러 전체 프로그램을 종료합니다.
  * **자동 폴더 생성:** 스크립트를 실행할 때마다 현재 시간 기준으로 세션 폴더(`image_recordings/YYYYMMDD_HHMMSS/`)를 자동으로 생성하여 데이터를 체계적으로 관리합니다.
  * **사용자 설정:** 카메라 종류(CSI/USB), 해상도, 초당 저장 이미지 수(FPS), Crop 영역 등 주요 파라미터를 스크립트 상단에서 쉽게 변경할 수 있습니다.

## 🖥️ 개발 환경

  * **보드:** NVIDIA Jetson Nano Orin
  * **운영체제:** Ubuntu 22.04
  * **Python 버전:** 3.10.12

## 🛠️ 환경 설정 및 설치 가이드

이 스크립트를 실행하기 위해 다음 단계를 순서대로 진행하세요.

### 1\. Git 저장소 복제

```bash
git clone https://github.com/TodFrog/GetData_JetsonNano
cd https://github.com/TodFrog/GetData_JetsonNano
```

### 2\. 파이썬 가상환경(venv) 생성 및 활성화

프로젝트의 의존성을 시스템과 분리하여 관리하기 위해 가상환경을 생성합니다.

```bash
# 'venv' 라는 이름의 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate
```

이제 터미널 프롬프트 앞에 `(venv)`가 표시되며, 모든 패키지는 이 가상환경 내에 설치됩니다.

### 3\. 필수 라이브러리 설치

`requirements.txt` 파일을 사용하여 필요한 모든 파이썬 라이브러리를 한 번에 설치합니다.

```bash
pip install -r requirements.txt
```

> **Jetson Orin/Nano 사용자 참고:** `requirements.txt`에 포함된 `opencv-python`은 일반 버전입니다. 최상의 성능(GPU 가속)을 위해서는, 이 명령어를 실행하기 전에 [NVIDIA 공식 가이드](https://www.google.com/search?q=https://docs.nvidia.com/deeplearning/frameworks/install-tf2-jetson-platform/index.html)에 따라 Jetson에 최적화된 OpenCV를 먼저 설치하는 것을 강력히 권장합니다.

## 🚀 실행 방법

### 1\. 카메라 포트 확인 (최초 1회)

스크립트를 실행하기 전, 사용하려는 카메라가 시스템에 어떤 포트로 연결되었는지 확인해야 합니다.

```bash
# v4l-utils가 없다면 설치: sudo apt-get install v4l-utils
v4l2-ctl --list-devices
```

출력된 목록에서 사용하려는 카메라의 `/dev/videoX` 번호를 확인합니다. (예: `/dev/video0` -\> `0`)

### 2\. 스크립트 설정 수정

`saveimage_opencv.py` 파일을 열어 맨 위의 설정값을 사용자의 환경에 맞게 수정합니다.

```python
# --- 중요 설정! ---
IS_CSI_CAMERA = False # CSI 카메라면 True, USB 웹캠이면 False로 변경
CAMERA_INDEX = 0      # 위에서 확인한 카메라 번호로 수정
# --- ---
```

### 3\. 스크립트 실행

가상환경이 활성화된 터미널에서 아래 명령어를 실행합니다.

```bash
python3 saveimage_opencv.py
```

### 4\. 대화형 제어

스크립트가 실행되면 다음과 같이 제어할 수 있습니다.

1.  **즉시 라이브 영상 시작:** 스크립트를 실행하면 바로 `Live Capture` 라는 제목의 창에 실시간 영상이 나타납니다.
2.  **이미지 저장 시작:** 터미널에서 **엔터(Enter)** 키를 누릅니다. "이미지 저장을 시작합니다." 라는 메시지와 함께 세션 폴더에 이미지 저장이 시작됩니다. 영상 창에는 `SAVING...` 상태가 표시됩니다.
3.  **저장 및 프로그램 종료:** 다시 **엔터(Enter)** 키를 누릅니다. 이미지 저장이 중지되고 라이브 영상 창이 닫히며 프로그램이 완전히 종료됩니다.
4.  **강제 종료:** 언제든지 라이브 영상 창을 클릭하고 키보드에서 **'q'** 키를 누르면 즉시 모든 작업을 종료할 수 있습니다.

-----
