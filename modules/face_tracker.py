import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from ultralytics import YOLO
from utils.helpers import setup_logger, parse_timestamp


class FaceTracker:
    """Face detection and tracking using YOLOv8"""

    def __init__(self, job_folder: Path):
        self.job_folder = job_folder
        self.logger = setup_logger(
            "FaceTracker",
            job_folder / "processing.log"
        )

        # Initialize YOLO Pose model for accurate face tracking via keypoints
        # Using YOLOv8n-pose (nano) for speed on M4 Pro
        # Will download on first run
        self.logger.info("Loading YOLOv8 Pose model for face detection via keypoints")
        self.model = YOLO('yolov8n-pose.pt')  # Pose model provides nose/eyes keypoints

    def track_faces_in_clip(
        self,
        video_path: Path,
        start_time: str,
        end_time: str,
        sample_rate: int = 5
    ) -> Dict[str, any]:
        """
        Track faces throughout a clip segment

        Args:
            video_path: Source video file
            start_time: Clip start (HH:MM:SS)
            end_time: Clip end (HH:MM:SS)
            sample_rate: Sample every N frames (default 5 for speed)

        Returns:
            Dict with face positions and optimal crop coordinates
        """
        self.logger.info(f"Tracking faces from {start_time} to {end_time}")

        # Open video
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)

        # Get frame dimensions (actual source resolution)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Calculate frame numbers
        start_seconds = parse_timestamp(start_time)
        end_seconds = parse_timestamp(end_time)
        start_frame = int(start_seconds * fps)
        end_frame = int(end_seconds * fps)

        # Set to start frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        face_positions = []
        frame_count = start_frame

        while frame_count < end_frame:
            ret, frame = cap.read()
            if not ret:
                break

            # Sample frames for efficiency
            if (frame_count - start_frame) % sample_rate == 0:
                # Detect persons and keypoints using YOLO Pose
                results = self.model(
                    frame,
                    device='mps',  # Use Apple Silicon GPU
                    verbose=False
                )

                # Extract pose keypoints (nose, eyes) for accurate face centering
                for result in results:
                    # Check if keypoints are available
                    if result.keypoints is None or len(result.keypoints) == 0:
                        continue

                    boxes = result.boxes
                    keypoints = result.keypoints

                    for i, (box, kpts) in enumerate(zip(boxes, keypoints)):
                        confidence = box.conf[0].cpu().numpy()

                        if confidence > 0.5:  # Confidence threshold
                            # Get bounding box for reference
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                            # Extract keypoints (COCO format: 17 keypoints)
                            # 0 = nose, 1 = left_eye, 2 = right_eye, 3 = left_ear, 4 = right_ear
                            kpts_xy = kpts.xy[0].cpu().numpy()  # Shape: [17, 2]

                            # Get face keypoints (nose + eyes)
                            nose = kpts_xy[0]       # [x, y]
                            left_eye = kpts_xy[1]
                            right_eye = kpts_xy[2]

                            # Calculate face center from nose and eyes
                            # Use average of available keypoints (some might be occluded)
                            face_points = []

                            # Keypoint is valid if both x and y are > 0
                            if nose[0] > 0 and nose[1] > 0:
                                face_points.append(nose)
                            if left_eye[0] > 0 and left_eye[1] > 0:
                                face_points.append(left_eye)
                            if right_eye[0] > 0 and right_eye[1] > 0:
                                face_points.append(right_eye)

                            # If we have face keypoints, use them; otherwise fall back to person box
                            if len(face_points) >= 1:
                                # Calculate average position of detected face keypoints
                                face_x = np.mean([pt[0] for pt in face_points])
                                face_y = np.mean([pt[1] for pt in face_points])

                                face_positions.append({
                                    'frame': frame_count,
                                    'center_x': int(face_x),
                                    'center_y': int(face_y),
                                    'box': [int(x1), int(y1), int(x2), int(y2)],
                                    'keypoints_used': len(face_points),
                                    'confidence': float(confidence),
                                    'method': 'pose_keypoints'
                                })
                            else:
                                # Fallback: use person box with heuristic
                                box_width = x2 - x1
                                box_height = y2 - y1
                                center_x = int((x1 + x2) / 2)
                                center_y = int(y1 + box_height * 0.15)

                                face_positions.append({
                                    'frame': frame_count,
                                    'center_x': center_x,
                                    'center_y': center_y,
                                    'box': [int(x1), int(y1), int(x2), int(y2)],
                                    'keypoints_used': 0,
                                    'confidence': float(confidence),
                                    'method': 'bbox_heuristic'
                                })

            frame_count += 1

        cap.release()

        if not face_positions:
            self.logger.warning("No faces detected in clip")
            # Return center of frame as fallback
            return self._get_fallback_center(frame_width, frame_height)

        # Calculate stable face center over time
        stats = self._calculate_face_center(face_positions, frame_width, frame_height)

        self.logger.info(f"Detected {len(face_positions)} face positions")
        return {
            'face_positions': face_positions,
            'face_center_x': stats['face_center_x'],
            'face_center_y': stats['face_center_y'],
            'source_width': frame_width,
            'source_height': frame_height
        }

    def _calculate_face_center(
        self,
        face_positions: List[Dict],
        frame_width: int,
        frame_height: int
    ) -> Dict:
        """
        Calculate a stable face center position over time.

        Uses median position for robustness and logs tracking statistics.
        """
        # Get all center positions
        x_positions = [pos['center_x'] for pos in face_positions]
        y_positions = [pos['center_y'] for pos in face_positions]

        # Use median for robustness against outliers
        median_x = int(np.median(x_positions))
        median_y = int(np.median(y_positions))

        # Calculate statistics for logging
        mean_x = int(np.mean(x_positions))
        std_x = int(np.std(x_positions))

        # Count detection methods used
        keypoint_detections = sum(
            1 for p in face_positions if p.get('method') == 'pose_keypoints'
        )
        heuristic_detections = sum(
            1 for p in face_positions if p.get('method') == 'bbox_heuristic'
        )

        # Log detection quality
        self.logger.info("Face tracking stats:")
        self.logger.info(f"  - Total detections: {len(face_positions)}")
        self.logger.info(f"  - Using pose keypoints: {keypoint_detections}")
        self.logger.info(f"  - Using bbox heuristic: {heuristic_detections}")
        self.logger.info(f"  - Median face position: ({median_x}, {median_y})")
        self.logger.info(f"  - Mean face position: ({mean_x}, {median_y})")
        self.logger.info(f"  - Horizontal std dev: {std_x} pixels (lower is more stable)")
        self.logger.info(f"  - Frame size: {frame_width}x{frame_height}")

        # Get sample keypoint info
        if face_positions:
            sample_pos = face_positions[len(face_positions) // 2]
            self.logger.info(
                f"  - Sample frame method: {sample_pos.get('method', 'unknown')}"
            )
            if sample_pos.get('method') == 'pose_keypoints':
                self.logger.info(
                    f"  - Keypoints detected: {sample_pos.get('keypoints_used', 0)}/3 "
                    "(nose + eyes)"
                )

        return {
            'face_center_x': median_x,
            'face_center_y': median_y
        }

    def _get_fallback_center(self, frame_width: int, frame_height: int) -> Dict:
        """
        Fallback center if no faces detected.

        Returns the geometric center of the frame so downstream cropping
        can still produce a reasonable shot.
        """
        self.logger.info("Using fallback center (no faces detected)")

        center_x = frame_width // 2 if frame_width > 0 else 0
        center_y = frame_height // 2 if frame_height > 0 else 0

        return {
            'face_positions': [],
            'face_center_x': center_x,
            'face_center_y': center_y,
            'source_width': frame_width,
            'source_height': frame_height
        }

    def detect_face_in_frame(self, frame_path: Path) -> Tuple[int, int]:
        """
        Detect face in single frame using pose keypoints (for quick testing)

        Returns:
            (center_x, center_y) of detected face
        """
        frame = cv2.imread(str(frame_path))

        results = self.model(
            frame,
            device='mps',
            verbose=False
        )

        for result in results:
            if result.keypoints is None or len(result.keypoints) == 0:
                continue

            # Get first detected person's keypoints
            kpts_xy = result.keypoints.xy[0].cpu().numpy()

            # Try to use face keypoints (nose, eyes)
            nose = kpts_xy[0]
            left_eye = kpts_xy[1]
            right_eye = kpts_xy[2]

            face_points = []
            if nose[0] > 0 and nose[1] > 0:
                face_points.append(nose)
            if left_eye[0] > 0 and left_eye[1] > 0:
                face_points.append(left_eye)
            if right_eye[0] > 0 and right_eye[1] > 0:
                face_points.append(right_eye)

            if len(face_points) >= 1:
                face_x = int(np.mean([pt[0] for pt in face_points]))
                face_y = int(np.mean([pt[1] for pt in face_points]))
                return face_x, face_y

        # Fallback to center
        height, width = frame.shape[:2]
        return width // 2, height // 2


class FaceTrackerOptimized(FaceTracker):
    """
    Optimized version that tracks fewer frames
    for faster processing on longer clips
    """

    def track_faces_in_clip(
        self,
        video_path: Path,
        start_time: str,
        end_time: str,
        sample_rate: int = 30  # Sample every 30 frames (~1 second at 30fps)
    ) -> Dict[str, any]:
        """
        Faster tracking by sampling fewer frames
        Good for clips where face doesn't move much
        """
        return super().track_faces_in_clip(
            video_path,
            start_time,
            end_time,
            sample_rate
        )
