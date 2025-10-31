import cv2
import os
import numpy as np
from datetime import datetime

# --- 설정값 ---
CAMERA_INDICES = [0, 2] # 예시: 0번, 2번 카메라 사용
IS_CSI_CAMERA = False # 모든 카메라가 CSI면 True, USB면 False

CAPTURE_WIDTH = 480
CAPTURE_HEIGHT = 480
# --- ---

# --- 나머지 설정값 ---
MAIN_OUTPUT_DIR = "video_recordings" # 저장 폴더
SAVE_FPS = 10 # 저장될 영상의 초당 프레임 수
# --- ---

def gstreamer_pipeline(sensor_id, capture_width, capture_height, framerate=30):
    """Jetson Nano의 CSI 카메라를 위한 GStreamer 파이프라인"""
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width=(int){capture_width}, height=(int){capture_height}, framerate=(fraction){framerate}/1 ! "
        "nvvidconv flip-method=0 ! "
        "video/x-raw, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
    )

def main():
    if len(CAMERA_INDICES) < 2:
        print("오류: 카메라를 2대 이상 지정해주세요. (CAMERA_INDICES 리스트 수정)")
        return

    caps = []
    crop_coords = []

    for index in CAMERA_INDICES:
        if IS_CSI_CAMERA:
            pipeline = gstreamer_pipeline(index, CAPTURE_WIDTH, CAPTURE_HEIGHT)
            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            print(f"CSI 카메라 #{index} (GStreamer) 모드로 {CAPTURE_WIDTH}x{CAPTURE_HEIGHT} 해상도를 요청합니다.")
        else:
            cap = cv2.VideoCapture(index)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
            print(f"USB 카메라 #{index} 모드로 {CAPTURE_WIDTH}x{CAPTURE_HEIGHT} 해상도를 요청합니다.")

        if not cap.isOpened():
            print(f"오류: 카메라 #{index}를 열 수 없습니다. 연결을 확인하세요.")
            for c in caps: c.release()
            return
        
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if actual_width < CAPTURE_WIDTH or actual_height < CAPTURE_HEIGHT:
            print(f"오류: 카메라 #{index}의 실제 해상도({actual_width}x{actual_height})가 원하는 크기보다 작습니다.")
            for c in caps: c.release()
            return
            
        crop_x = (actual_width - CAPTURE_WIDTH) // 2
        crop_y = (actual_height - CAPTURE_HEIGHT) // 2
        
        caps.append(cap)
        crop_coords.append((crop_x, crop_y))

    print(f"\n총 {len(caps)}대의 카메라 설정 완료. 라이브 영상을 시작합니다.")
    print("엔터를 누르면 영상 녹화가 시작됩니다.")

    is_recording = False
    video_writers = []
    base_save_path = ""

    try:
        while True:
            clean_frames_for_saving = []
            frames_for_display = []
            
            for i, cap in enumerate(caps):
                ret, frame = cap.read()
                if not ret:
                    print(f"오류: 카메라 #{CAMERA_INDICES[i]}에서 프레임을 읽을 수 없습니다.")
                    frame = np.zeros((CAPTURE_HEIGHT, CAPTURE_WIDTH, 3), dtype=np.uint8)

                crop_x, crop_y = crop_coords[i]
                cropped_frame = frame[crop_y : crop_y + CAPTURE_HEIGHT, crop_x : crop_x + CAPTURE_WIDTH]

                clean_frames_for_saving.append(cropped_frame)
                display_frame = cropped_frame.copy()
                
                cam_label = f"CAM {CAMERA_INDICES[i]}"
                cv2.putText(display_frame, cam_label, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

                status_text = ''
                if is_recording:
                    text_color = (0, 0, 255)
                    cv2.circle(display_frame, (30, CAPTURE_HEIGHT - 30), 10, text_color, -1)
                else:
                    status_text = 'Press ENTER to start'
                    text_color = (0, 255, 0)
                
                cv2.putText(display_frame, status_text, (10, CAPTURE_HEIGHT - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2)
                frames_for_display.append(display_frame)

            combined_frame = cv2.hconcat(frames_for_display)
            cv2.imshow('Multi-Camera Live', combined_frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break
            elif key == 13:
                if not is_recording:
                    is_recording = True
                    current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    base_save_path = os.path.join(MAIN_OUTPUT_DIR, current_time_str)
                    os.makedirs(base_save_path, exist_ok=True)
                    
                    video_writers = []
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    for index in CAMERA_INDICES:
                        filename = os.path.join(base_save_path, f"cam_{index}.mp4")
                        writer = cv2.VideoWriter(filename, fourcc, SAVE_FPS, (CAPTURE_WIDTH, CAPTURE_HEIGHT))
                        video_writers.append(writer)
                    
                    print(f"\n>>> 영상 녹화를 시작합니다. 저장 폴더: '{base_save_path}'")
                    print(">>> 다시 엔터를 누르면 모든 작업이 종료됩니다.")
                else:
                    print("\n>>> 영상 녹화를 중지하고 프로그램을 종료합니다.")
                    break

            if is_recording:
                for i, clean_frame in enumerate(clean_frames_for_saving):
                    if i < len(video_writers):
                        video_writers[i].write(clean_frame)

    finally:
        for cap in caps:
            cap.release()
        for writer in video_writers:
            writer.release()
        cv2.destroyAllWindows()
        
        if is_recording and base_save_path:
            print("\n--- 저장 결과 ---")
            print(f"모든 카메라의 영상이 '{base_save_path}' 폴더에 저장되었습니다.")
        print("\n프로그램을 종료했습니다.")

if __name__ == '__main__':
    main()
