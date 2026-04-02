"""
Camera abstraction layer.

Supports three modes:
  - upload    : Process images uploaded by the user (default for Replit/dev)
  - webcam    : Capture frames from a USB webcam using OpenCV
  - picamera2 : Raspberry Pi camera via Picamera2/libcamera (Pi only)

To switch mode, set CAMERA_MODE env variable or update CameraConfig in DB.
"""
import io
import time
import threading
import logging
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class BaseCamera(ABC):
    """Abstract base class for camera sources."""

    @abstractmethod
    def get_frame(self) -> bytes | None:
        """Return a JPEG-encoded frame as bytes, or None if unavailable."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the camera source is ready."""
        ...

    def release(self):
        """Release camera resources."""
        pass


class UploadSource(BaseCamera):
    """
    Camera source that uses a static image or the last uploaded frame.
    Used for Replit development and testing without a physical camera.
    """

    def __init__(self, static_dir: Path = None):
        self._current_frame: bytes | None = None
        self._placeholder_path = static_dir / 'img' / 'no_camera.jpg' if static_dir else None

    def set_frame(self, jpeg_bytes: bytes):
        """Set the current frame from an uploaded image."""
        self._current_frame = jpeg_bytes

    def get_frame(self) -> bytes | None:
        if self._current_frame:
            return self._current_frame
        # Return placeholder if available
        if self._placeholder_path and self._placeholder_path.exists():
            return self._placeholder_path.read_bytes()
        return None

    def is_available(self) -> bool:
        return self._current_frame is not None


class WebcamSource(BaseCamera):
    """
    Camera source using OpenCV to capture from a USB webcam.
    Uses a background thread to keep frames fresh.
    """

    def __init__(self, device_index: int = 0, width: int = 640, height: int = 480):
        self._cap = None
        self._frame: bytes | None = None
        self._lock = threading.Lock()
        self._running = False
        self._device_index = device_index
        self._width = width
        self._height = height
        self._start()

    def _start(self):
        try:
            import cv2
            self._cap = cv2.VideoCapture(self._device_index)
            if not self._cap.isOpened():
                logger.warning('WebcamSource: camera not available at index %d', self._device_index)
                self._cap = None
                return
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
            self._running = True
            t = threading.Thread(target=self._capture_loop, daemon=True)
            t.start()
        except Exception as e:
            logger.error('WebcamSource init error: %s', e)

    def _capture_loop(self):
        import cv2
        while self._running and self._cap:
            ret, frame = self._cap.read()
            if ret:
                _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                with self._lock:
                    self._frame = buf.tobytes()
            time.sleep(0.05)

    def get_frame(self) -> bytes | None:
        with self._lock:
            return self._frame

    def is_available(self) -> bool:
        return self._cap is not None and self._running

    def release(self):
        self._running = False
        if self._cap:
            self._cap.release()


class PiCameraSource(BaseCamera):
    """
    Raspberry Pi camera source using Picamera2 (libcamera).

    UPGRADE POINT: This class integrates Picamera2 for Pi camera support.
    Install: pip install picamera2
    Ensure libcamera is available on the Pi OS.
    """

    def __init__(self, width: int = 640, height: int = 480):
        self._frame: bytes | None = None
        self._lock = threading.Lock()
        self._running = False
        self._cam = None
        self._width = width
        self._height = height
        self._start()

    def _start(self):
        try:
            from picamera2 import Picamera2  # type: ignore
            import libcamera  # type: ignore
            self._cam = Picamera2()
            config = self._cam.create_still_configuration(
                main={'size': (self._width, self._height)}
            )
            self._cam.configure(config)
            self._cam.start()
            self._running = True
            t = threading.Thread(target=self._capture_loop, daemon=True)
            t.start()
            logger.info('PiCameraSource: Picamera2 started successfully')
        except ImportError:
            logger.error('PiCameraSource: picamera2 not installed. Run on Raspberry Pi with libcamera.')
        except Exception as e:
            logger.error('PiCameraSource init error: %s', e)

    def _capture_loop(self):
        import io
        while self._running and self._cam:
            try:
                stream = io.BytesIO()
                self._cam.capture_file(stream, format='jpeg')
                with self._lock:
                    self._frame = stream.getvalue()
            except Exception as e:
                logger.warning('PiCameraSource capture error: %s', e)
            time.sleep(0.1)

    def get_frame(self) -> bytes | None:
        with self._lock:
            return self._frame

    def is_available(self) -> bool:
        return self._cam is not None and self._running

    def release(self):
        self._running = False
        if self._cam:
            self._cam.stop()


class CameraManager:
    """
    Singleton-like manager that provides the active camera source.
    The source is chosen based on CAMERA_MODE config.
    """
    _instance: BaseCamera | None = None
    _mode: str = 'upload'

    @classmethod
    def get(cls, mode: str = 'upload', static_dir: Path = None) -> BaseCamera:
        if cls._instance is None or cls._mode != mode:
            cls._mode = mode
            if cls._instance:
                cls._instance.release()
            if mode == 'webcam':
                cls._instance = WebcamSource()
            elif mode == 'picamera2':
                cls._instance = PiCameraSource()
            else:
                cls._instance = UploadSource(static_dir=static_dir)
        return cls._instance

    @classmethod
    def reset(cls):
        if cls._instance:
            cls._instance.release()
        cls._instance = None
