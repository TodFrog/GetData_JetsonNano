import cv2
import os
import numpy as np
from datetime import datetime

# --- 설정값 ---
# 사용할 카메라의 인덱스 번호를 리스트로 지정합니다.
# 예: 2대 사용 -> [0, 1], 3대 사용 -> [0, 1, 2]
# 특정 번호 지정도 가능합니다. -> [0, 2, 4]
CAMERA_INDICES = [0, 2] # 예시: 0번, 2번 카메라 사용
IS_CSI_CAMERA = False # 모든 카메라가 CSI면 True, USB면 False

# 카메라에 요청할 해상도 & 최종 저장될 이미지의 크기
CAPTURE_WIDTH = 480
CAPTURE_HEIGHT = 480
# --- ---

# --- 나머지 설정값 ---
MAIN_OUTPUT_DIR = "image_recordings" # 저장 폴더
SAVE_FPS = 10 # 초당 저장할 이미지 수
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
            for c in caps:
                c.release()
            return
        
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if actual_width < CAPTURE_WIDTH or actual_height < CAPTURE_HEIGHT:
            print(f"오류: 카메라 #{index}의 실제 해상도({actual_width}x{actual_height})가 원하는 크기보다 작습니다.")
            for c in caps:
                c.release()
            return
            
        crop_x = (actual_width - CAPTURE_WIDTH) // 2
        crop_y = (actual_height - CAPTURE_HEIGHT) // 2
        
        caps.append(cap)
        crop_coords.append((crop_x, crop_y))

    print(f"\n총 {len(caps)}대의 카메라 설정 완료. 라이브 영상을 시작합니다.")
    print("엔터를 누르면 이미지 저장이 시작됩니다.")

    is_saving = False
    session_dirs = []
    saved_image_counts = [0] * len(caps)
    
    camera_fps = caps[0].get(cv2.CAP_PROP_FPS)
    if camera_fps == 0: camera_fps = 30
    capture_interval = int(camera_fps / SAVE_FPS) if SAVE_FPS > 0 else 0
    frame_count = 0

    try:
        while True:
            # 두 종류의 프레임 리스트를 만듭니다.
            clean_frames_for_saving = []
            frames_for_display = []
            
            for i, cap in enumerate(caps):
                ret, frame = cap.read()
                if not ret:
                    print(f"오류: 카메라 #{CAMERA_INDICES[i]}에서 프레임을 읽을 수 없습니다.")
                    frame = np.zeros((CAPTURE_HEIGHT, CAPTURE_WIDTH, 3), dtype=np.uint8)

                crop_x, crop_y = crop_coords[i]
                cropped_frame = frame[crop_y : crop_y + CAPTURE_HEIGHT, crop_x : crop_x + CAPTURE_WIDTH]

                # 글씨 없는 원본은 저장용 리스트에 추가합니다.
                clean_frames_for_saving.append(cropped_frame)

                # 화면 표시용으로 프레임을 복사합니다.
                display_frame = cropped_frame.copy()
                
                # 복사한 프레임에만 글씨를 그립니다.
                cam_label = f"CAM {CAMERA_INDICES[i]}"
                cv2.putText(display_frame, cam_label, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

                status_text = ''
                if is_saving: text_color = (0, 0, 255)
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
                if not is_saving:
                    is_saving = True
                    current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    base_save_path = os.path.join(MAIN_OUTPUT_DIR, current_time_str)
                    session_dirs = []
                    for index in CAMERA_INDICES:
                        cam_dir = os.path.join(base_save_path, f"cam_{index}")
                        os.makedirs(cam_dir, exist_ok=True)
                        session_dirs.append(cam_dir)
                    
                    frame_count = 0
                    saved_image_counts = [0] * len(caps)
                    print(f"\n>>> 이미지 저장을 시작합니다. 저장 폴더: '{base_save_path}'")
                    print(">>> 다시 엔터를 누르면 모든 작업이 종료됩니다.")
                else:
                    print("\n>>> 이미지 저장을 중지하고 프로그램을 종료합니다.")
                    break

            if is_saving:
                frame_count += 1
                if capture_interval > 0 and frame_count % capture_interval == 0:
                    for i, clean_frame in enumerate(clean_frames_for_saving):
                        saved_image_counts[i] += 1
                        filename = os.path.join(session_dirs[i], f"frame_{saved_image_counts[i]:06d}.jpg")
                        cv2.imwrite(filename, clean_frame)

    finally:
        for cap in caps:
            cap.release()
        cv2.destroyAllWindows()
        
        if is_saving and sum(saved_image_counts) > 0:
            print("\n--- 저장 결과 ---")
            for i, count in enumerate(saved_image_counts):
                print(f"카메라 #{CAMERA_INDICES[i]}: 총 {count}개의 이미지를 '{session_dirs[i]}'에 저장했습니다.")
        print("\n프로그램을 종료했습니다.")

if __name__ == '__main__':
    main()