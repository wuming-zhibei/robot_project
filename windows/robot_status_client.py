
import json
import socket
import threading
import time


UBUNTU_IP = "192.168.92.130"
TCP_PORT = 9000


class RobotStatusClient:
    """持续接收 Ubuntu 推送的双机器人状态。"""

    def __init__(self, host=UBUNTU_IP, port=TCP_PORT):
        self.host = host
        self.port = port

        self._latest_status = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self._socket = None

    def start(self):
        """启动后台接收线程，重复调用不会重复启动。"""
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._receive_loop,
            name="robot-status-client",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        """停止接收并关闭连接。"""
        self._stop_event.set()

        if self._socket is not None:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                self._socket.close()
            except OSError:
                pass

        if self._thread is not None:
            self._thread.join(timeout=3)

        self._thread = None
        self._socket = None

    def get_status(self):
        """获取最近收到的完整状态消息。"""
        with self._lock:
            if self._latest_status is None:
                return None

            # 返回副本，避免调用方修改缓存
            return dict(self._latest_status)

    def _receive_loop(self):
        """断线后自动重连，并逐行解析 JSON。"""
        while not self._stop_event.is_set():
            try:
                print(
                    f"[Robot TCP] Connecting to "
                    f"{self.host}:{self.port}"
                )

                with socket.create_connection(
                    (self.host, self.port), timeout=5
                ) as sock:
                    self._socket = sock
                    sock.settimeout(2)

                    print("[Robot TCP] Connected")

                    buffer = b""

                    while not self._stop_event.is_set():
                        try:
                            chunk = sock.recv(4096)
                        except socket.timeout:
                            continue

                        if not chunk:
                            break

                        buffer += chunk

                        while b"\n" in buffer:
                            line, buffer = buffer.split(b"\n", 1)

                            if not line.strip():
                                continue

                            try:
                                message = json.loads(
                                    line.decode("utf-8")
                                )

                                if message.get("type") == "robot_status":
                                    with self._lock:
                                        self._latest_status = message

                            except (UnicodeDecodeError, json.JSONDecodeError):
                                print(
                                    "[Robot TCP] Invalid JSON message"
                                )

                self._socket = None

            except OSError as exc:
                if not self._stop_event.is_set():
                    print(f"[Robot TCP] Connection error: {exc}")

            if not self._stop_event.is_set():
                time.sleep(2)
