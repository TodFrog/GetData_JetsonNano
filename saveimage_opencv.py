import cv2
import os
from datetime import datetime

# --- 설정값 (여기서 자유롭게 변경하세요) ---
IS_CSI_CAMERA = False # CSI 카메라면 True, USB 웹캠이면 False로 변경
CAMERA_INDEX = 0      # v4l2-ctl로 확인한 카메라 번호 (0, 1 등)
# --- ---

# --- 나머지 설정값 ---
MAIN_OUTPUT_DIR = "image_recordings"
SAVE_FPS = 10
CAP_WIDTH = 480
CAP_HEIGHT = 480
CROP_W = 480
CROP_H = 480
CROP_X = (CAP_WIDTH - CROP_W) // 2
CROP_Y = (CAP_HEIGHT - CROP_H) // 2
# --- ---

def gstreamer_pipeline(capture_width=1280, capture_height=720, framerate=30):
    """Jetson Nano의 CSI 카메라를 위한 GStreamer 파이프라인"""
    return (
        f"nvarguscamerasrc sensor-id={CAMERA_INDEX} ! "
        f"video/x-raw(memory:NVMM), width=(int){capture_width}, height=(int){capture_height}, framerate=(fraction){framerate}/1 ! "
        "nvvidconv flip-method=0 ! "
        "video/x-raw, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
    )

def main():
    if IS_CSI_CAMERA:
        pipeline = gstreamer_pipeline(capture_width=CAP_WIDTH, capture_height=CAP_HEIGHT)
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        print("CSI 카메라 (GStreamer) 모드로 실행합니다.")
    else:
        cap = cv2.VideoCapture(CAMERA_INDEX)
        print("USB 카메라 모드로 실행합니다.")

    if not cap.isOpened():
        print(f"오류: 카메라를 열 수 없습니다. 카메라 종류(CSI/USB)와 인덱스({CAMERA_INDEX}) 설정을 확인하세요.")
        return
        
    if not IS_CSI_CAMERA:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAP_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAP_HEIGHT)

    # [핵심 수정] 실제 카메라의 너비와 높이를 읽어와 변수에 저장합니다.
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    camera_fps = cap.get(cv2.CAP_PROP_FPS)
    if camera_fps == 0: camera_fps = 30
        
    print(f"카메라 설정 완료: {CAP_WIDTH}x{CAP_HEIGHT}. 라이브 영상을 시작합니다.")
    print("엔터를 누르면 이미지 저장이 시작됩니다.")

    # 상태 변수 및 카운터 초기화
    is_saving = False
    session_dir = ""
    capture_interval = int(camera_fps / SAVE_FPS) if SAVE_FPS > 0 else 0
    frame_count = 0
    saved_image_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("오류: 프레임을 읽을 수 없습니다.")
                break
            
            # is_saving 상태에 따라 프레임 하단에 텍스트 표시
            if is_saving:
                status_text = ''
                # 이제 'height' 변수가 정의되었으므로 이 코드가 정상 작동합니다.
                cv2.putText(frame, status_text, (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            else:
                status_text = 'Press ENTER to start saving'
                cv2.putText(frame, status_text, (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            cv2.imshow('Live Capture', frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break
            elif key == 13: # Enter key
                if not is_saving:
                    is_saving = True
                    current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    session_dir = os.path.join(MAIN_OUTPUT_DIR, current_time_str)
                    os.makedirs(session_dir, exist_ok=True)
                    frame_count = 0
                    saved_image_count = 0
                    print(f"\n>>> 이미지 저장을 시작합니다. 저장 폴더: '{session_dir}'")
                    print(">>> 다시 엔터를 누르면 모든 작업이 종료됩니다.")
                else:
                    print("\n>>> 이미지 저장을 중지하고 프로그램을 종료합니다.")
                    break

            if is_saving:
                frame_count += 1
                if capture_interval > 0 and frame_count % capture_interval == 0:
                    cropped_frame = frame[CROP_Y : CROP_Y + CROP_H, CROP_X : CROP_X + CROP_W]
                    saved_image_count += 1
                    filename = os.path.join(session_dir, f"frame_{saved_image_count:06d}.jpg")
                    cv2.imwrite(filename, cropped_frame)

    finally:
        cap.release()
        cv2.destroyAllWindows()
        if saved_image_count > 0:
            print(f"총 {saved_image_count}개의 이미지가 '{session_dir}'에 저장되었습니다.")
        print("프로그램을 종료했습니다.")

if __name__ == '__main__':
    main()