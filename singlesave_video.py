import cv2
import os
from datetime import datetime

# --- 설정값 (여기서 원하는 최종 해상도를 설정하세요) ---
IS_CSI_CAMERA = False  # CSI 카메라면 True, USB 웹캠이면 False
CAMERA_INDEX = 0       # v4l2-ctl로 확인한 카메라 번호 (0, 1 등)

# 카메라에 요청할 해상도 & 최종 저장될 영상의 크기
CAPTURE_WIDTH = 480
CAPTURE_HEIGHT = 480
# --- ---

# --- 나머지 설정값 ---
MAIN_OUTPUT_DIR = "video_recordings" # 저장 폴더
SAVE_FPS = 10  # 저장될 영상의 초당 프레임 수
# --- ---

def gstreamer_pipeline(capture_width, capture_height, framerate=30):
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
    # 카메라 종류에 따라 VideoCapture 객체 생성 및 해상도 요청
    if IS_CSI_CAMERA:
        pipeline = gstreamer_pipeline(CAPTURE_WIDTH, CAPTURE_HEIGHT)
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        print(f"CSI 카메라 (GStreamer) 모드로 {CAPTURE_WIDTH}x{CAPTURE_HEIGHT} 해상도를 요청합니다.")
    else:
        cap = cv2.VideoCapture(CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
        print(f"USB 카메라 모드로 {CAPTURE_WIDTH}x{CAPTURE_HEIGHT} 해상도를 요청합니다.")

    if not cap.isOpened():
        print(f"오류: 카메라를 열 수 없습니다. 카메라 종류(CSI/USB)와 인덱스({CAMERA_INDEX}) 설정을 확인하세요.")
        return

    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    if actual_width != CAPTURE_WIDTH or actual_height != CAPTURE_HEIGHT:
        print(f"참고: 요청한 {CAPTURE_WIDTH}x{CAPTURE_HEIGHT} 대신, 카메라가 지원하는 {actual_width}x{actual_height}로 설정되었습니다.")
        print(f"영상은 {CAPTURE_WIDTH}x{CAPTURE_HEIGHT} 크기로 중앙을 잘라내어 표시됩니다.")

    crop_x = (actual_width - CAPTURE_WIDTH) // 2
    crop_y = (actual_height - CAPTURE_HEIGHT) // 2

    if actual_width < CAPTURE_WIDTH or actual_height < CAPTURE_HEIGHT:
        print(f"오류: 카메라의 실제 해상도({actual_width}x{actual_height})가 원하는 크기({CAPTURE_WIDTH}x{CAPTURE_HEIGHT})보다 작습니다.")
        cap.release()
        return

    print(f"카메라 설정 완료. 라이브 영상을 시작합니다.")
    print("엔터를 누르면 영상 녹화가 시작됩니다.")

    is_recording = False
    video_writer = None
    session_dir = ""

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("오류: 프레임을 읽을 수 없습니다.")
                break
            
            cropped_frame = frame[crop_y : crop_y + CAPTURE_HEIGHT, crop_x : crop_x + CAPTURE_WIDTH]

            display_frame = cropped_frame.copy()
            status_text = ''
            if is_recording:
                text_color = (0, 0, 255) # 빨간색 (녹화중)
                cv2.circle(display_frame, (30, 30), 10, text_color, -1) # 녹화중 표시
            else:
                status_text = 'Press ENTER to start recording'
                text_color = (0, 255, 0) # 초록색

            cv2.putText(display_frame, status_text, (10, CAPTURE_HEIGHT - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2)
            cv2.imshow('Live Capture', display_frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break
            elif key == 13: # Enter key
                if not is_recording:
                    is_recording = True
                    current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    session_dir = os.path.join(MAIN_OUTPUT_DIR, current_time_str)
                    os.makedirs(session_dir, exist_ok=True)
                    
                    video_filename = os.path.join(session_dir, f"video_{current_time_str}.mp4")
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    video_writer = cv2.VideoWriter(video_filename, fourcc, SAVE_FPS, (CAPTURE_WIDTH, CAPTURE_HEIGHT))
                    
                    print(f"\n>>> 영상 녹화를 시작합니다. 저장 파일: '{video_filename}'")
                    print(">>> 다시 엔터를 누르면 모든 작업이 종료됩니다.")
                else:
                    print("\n>>> 영상 녹화를 중지하고 프로그램을 종료합니다.")
                    break

            if is_recording and video_writer:
                video_writer.write(cropped_frame)

    finally:
        if video_writer:
            video_writer.release()
        cap.release()
        cv2.destroyAllWindows()
        if is_recording:
            print(f"영상이 '{session_dir}'에 저장되었습니다.")
        print("프로그램을 종료했습니다.")

if __name__ == '__main__':
    main()
