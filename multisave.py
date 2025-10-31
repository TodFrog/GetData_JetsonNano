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

# 카메라에 요청할 해상도 & 최종 저장될 이미지/비디오의 크기
CAPTURE_WIDTH = 480
CAPTURE_HEIGHT = 480
# --- ---

# --- 저장 방식 설정 ---
SAVE_IMAGES = True # True로 설정하면 이미지를 저장합니다.
SAVE_VIDEO = True # True로 설정하면 비디오를 저장합니다.

# 저장 FPS 설정
IMAGE_SAVE_FPS = 10  # 초당 저장할 *이미지* 수
VIDEO_SAVE_FPS = 10  # 저장될 *비디오*의 초당 프레임 수
# --- ---

# --- 나머지 설정값 ---
MAIN_OUTPUT_DIR = "data_recordings" # 저장 폴더
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
    
    if not SAVE_IMAGES and not SAVE_VIDEO:
        print("오류: SAVE_IMAGES와 SAVE_VIDEO가 모두 False입니다. 저장할 것이 없습니다.")
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
    print("엔터를 누르면 녹화(이미지/비디오 저장)가 시작됩니다.")

    is_recording = False
    
    # 비디오 저장용 변수
    video_writers = []
    
    # 이미지 저장용 변수
    image_session_dirs = []
    saved_image_counts = [0] * len(caps)
    frame_count = 0
    image_capture_interval = 0
    
    # 실제 카메라 FPS 기반으로 이미지 저장 간격 계산
    camera_fps = caps[0].get(cv2.CAP_PROP_FPS)
    if camera_fps == 0: camera_fps = 30 # 기본값
    if SAVE_IMAGES and IMAGE_SAVE_FPS > 0:
        image_capture_interval = int(camera_fps / IMAGE_SAVE_FPS)

    base_save_path = ""

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
                if is_recording:
                    text_color = (0, 0, 255)
                    # 녹화 중일 때 빨간 원 표시
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
            elif key == 13: # 엔터키
                if not is_recording:
                    is_recording = True
                    current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    base_save_path = os.path.join(MAIN_OUTPUT_DIR, current_time_str)
                    os.makedirs(base_save_path, exist_ok=True)
                    
                    # --- 비디오 라이터 설정 (SAVE_VIDEO == True일 때) ---
                    if SAVE_VIDEO:
                        video_writers = []
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        for i, index in enumerate(CAMERA_INDICES):
                            filename = os.path.join(base_save_path, f"cam_{index}.mp4")
                            writer = cv2.VideoWriter(filename, fourcc, VIDEO_SAVE_FPS, (CAPTURE_WIDTH, CAPTURE_HEIGHT))
                            video_writers.append(writer)
                    
                    # --- 이미지 저장 폴더 설정 (SAVE_IMAGES == True일 때) ---
                    if SAVE_IMAGES:
                        image_session_dirs = []
                        base_image_path = os.path.join(base_save_path, "images")
                        for index in CAMERA_INDICES:
                            cam_dir = os.path.join(base_image_path, f"cam_{index}")
                            os.makedirs(cam_dir, exist_ok=True)
                            image_session_dirs.append(cam_dir)
                        
                        frame_count = 0
                        saved_image_counts = [0] * len(caps)

                    print(f"\n>>> 녹화를 시작합니다. 저장 폴더: '{base_save_path}'")
                    print(f"--- 이미지 저장: {SAVE_IMAGES} (FPS: {IMAGE_SAVE_FPS}), 영상 저장: {SAVE_VIDEO} (FPS: {VIDEO_SAVE_FPS}) ---")
                    print(">>> 다시 엔터를 누르면 모든 작업이 종료됩니다.")
                else:
                    print("\n>>> 녹화를 중지하고 프로그램을 종료합니다.")
                    break

            # --- 저장 로직 ---
            if is_recording:
                # 1. 이미지 저장 (설정된 간격마다)
                if SAVE_IMAGES:
                    frame_count += 1
                    if image_capture_interval > 0 and frame_count % image_capture_interval == 0:
                        for i, clean_frame in enumerate(clean_frames_for_saving):
                            saved_image_counts[i] += 1
                            filename = os.path.join(image_session_dirs[i], f"frame_{saved_image_counts[i]:06d}.jpg")
                            cv2.imwrite(filename, clean_frame)
                
                # 2. 비디오 저장 (매 프레임)
                if SAVE_VIDEO:
                    for i, clean_frame in enumerate(clean_frames_for_saving):
                        if i < len(video_writers):
                            video_writers[i].write(clean_frame)

    finally:
        # 모든 리소스 해제
        for cap in caps:
            cap.release()
        
        if SAVE_VIDEO:
            for writer in video_writers:
                writer.release()
                
        cv2.destroyAllWindows()
        
        # --- 최종 저장 결과 요약 ---
        if is_recording and base_save_path:
            print("\n--- 저장 결과 ---")
            if SAVE_VIDEO:
                print(f"🎥 모든 카메라의 영상이 '{base_save_path}' 폴더에 저장되었습니다.")
            
            if SAVE_IMAGES and sum(saved_image_counts) > 0:
                print("🖼️ 이미지 저장 내역:")
                for i, count in enumerate(saved_image_counts):
                    print(f"  - 카메라 #{CAMERA_INDICES[i]}: 총 {count}개의 이미지를 '{image_session_dirs[i]}'에 저장했습니다.")
        
        print("\n프로그램을 종료했습니다.")

if __name__ == '__main__':
    main()