import threading
import time

import cv2

from recognize_face import recognize_face
#使用默认摄像头和需要连续识别3帧才确认身份。

class CameraRecognitionService:
    def __init__(self, camera_index=0, confirm_frames=3):
        self.camera_index = camera_index
        self.confirm_frames = confirm_frames

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None

        self._model = None
        self._database = {}

        self._status = {
            "camera_running": False,
            "camera_open": False,
            "person_id": "unknown",
            "similarity": 0.0,
            "bbox": None,
            "face_count": 0,
            "message": "摄像头尚未启动",
        }

        self._candidate = None
        self._candidate_count = 0
        self._no_face_count = 0
    def start(self, model, database):
        """启动摄像头识别。"""
        if self._thread is not None and self._thread.is_alive():
            return False

        self._model = model
        self._database = database
        self._stop_event.clear()

        # 每次启动都重置识别计数
        self._candidate = None
        self._candidate_count = 0
        self._no_face_count = 0

        with self._lock:
            self._status = {
                "camera_running": True,
                "camera_open": False,
                "person_id": "unknown",
                "similarity": 0.0,
                "bbox": None,
                "face_count": 0,
                "message": "正在打开摄像头",
            }

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
        )
        self._thread.start()
        return True
    def stop(self):
        """停止摄像头识别。"""
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join(timeout=5)

        with self._lock:
            self._status["camera_running"] = False
            self._status["camera_open"] = False
            self._status["message"] = "摄像头已停止"

        self._thread = None
    def get_status(self):
        """获取当前摄像头识别状态。"""
        with self._lock:
            return dict(self._status)
    def _run(self):
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        #兼容不同的摄像头驱动
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            with self._lock:
                self._status.update({
                    "camera_running": False,
                    "camera_open": False,
                    "message": "无法打开摄像头",
                })
            cap.release()
            return
        #设置摄像头缓冲区大小为 1，尽可能减少延迟
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        with self._lock:
            self._status.update({
                "camera_running": True,
                "camera_open": True,
                "message": "摄像头已打开，正在识别",
            })

        try:
            while not self._stop_event.is_set():
                ok, frame = cap.read()

                if not ok:
                    time.sleep(0.1)
                    continue

                try:
                    faces = self._model.get(frame)
                except Exception as exc:
                    with self._lock:
                        self._status["message"] = (
                            f"人脸检测失败：{type(exc).__name__}"
                        )
                    time.sleep(0.2)
                    continue

                if not faces:
                    self._no_face_count += 1
                    self._candidate = None
                    self._candidate_count = 0

                    if self._no_face_count >= 5:
                        with self._lock:
                            self._status.update({
                                "person_id": "unknown",
                                "similarity": 0.0,
                                "bbox": None,
                                "face_count": 0,
                                "message": "未检测到人脸",
                            })
                    else:
                        with self._lock:
                            self._status["face_count"] = 0

                    continue
                #有人脸了，清空无人脸个数
                self._no_face_count = 0

                # 选择画面中最大的人脸
                face = max(
                    faces,
                    #计算人脸面积，lambda是比较每张人脸的面积，而不是直接比较人脸对象
                    key=lambda item: (
                        (item.bbox[2] - item.bbox[0])
                        * (item.bbox[3] - item.bbox[1])
                    ),
                )

                person_id, score = recognize_face(
                    face.normed_embedding,
                    self._database,
                )
                #把人脸坐标转换成普通浮点数，并保留一位小数。
                bbox = [
                    round(float(value), 1)
                    for value in face.bbox
                ]

                # 连续识别到相同身份才确认
                if person_id == self._candidate:
                    self._candidate_count += 1
                else:
                    self._candidate = person_id
                    self._candidate_count = 1

                with self._lock:
                    self._status["face_count"] = len(faces)

                    if self._candidate_count >= self.confirm_frames:
                        self._status.update({
                            "person_id": person_id,
                            "similarity": round(float(score), 4),
                            "bbox": bbox,
                            "message": "身份已确认",
                        })
                    else:
                        self._status["message"] = (
                            f"正在确认身份 "
                            f"({self._candidate_count}/"
                            f"{self.confirm_frames})"
                        )

        finally:
            cap.release()

            with self._lock:
                self._status["camera_running"] = False
                self._status["camera_open"] = False

                if self._status["message"] != "摄像头已停止":
                    self._status["message"] = "摄像头识别已结束"