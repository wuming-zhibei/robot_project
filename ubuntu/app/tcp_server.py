
import json
import socketserver
import threading
import time
from datetime import datetime

from app.robot import robots
from app.ros2_bridge import get_position


HOST = "0.0.0.0"
PORT = 9000
SEND_INTERVAL = 1.0

_tcp_server = None
_tcp_thread = None
_server_lock = threading.Lock()


def build_status_message():
    """获取两台机器人的最新状态，并构造成统一的 JSON 数据。"""
    robot_statuses = {}

    for robot_id, robot in robots.items():
        status = robot.get_status()

        # 优先采用 Webots 通过 ROS 2 发布的实际位置
        position = get_position(robot_id)
        status["position"] = position
        status["online"] = position is not None

        robot_statuses[robot_id] = status

    return {
        "type": "robot_status",
        "robots": robot_statuses,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


class StatusHandler(socketserver.BaseRequestHandler):
    """每个连接一个处理线程，持续发送机器人状态。"""

    def handle(self):
        client = self.client_address
        print(f"[TCP] Client connected: {client}")

        try:
            self.request.settimeout(5.0)

            while self.server.running:
                message = build_status_message()

                # 每条 JSON 消息以换行符结束
                payload = (
                    json.dumps(message, ensure_ascii=False) + "\n"
                ).encode("utf-8")

                self.request.sendall(payload)
                time.sleep(SEND_INTERVAL)

        except (OSError, ConnectionError) as exc:
            print(f"[TCP] Client disconnected: {client} ({exc})")

        finally:
            print(f"[TCP] Connection closed: {client}")


class RobotStatusTCPServer(socketserver.ThreadingTCPServer):
    """允许多个客户端同时连接的 TCP 服务端。"""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, handler):
        self.running = True
        super().__init__(address, handler)


def start_tcp_server():
    """启动 TCP 服务端；重复调用不会重复启动。"""
    global _tcp_server, _tcp_thread

    with _server_lock:
        if _tcp_thread is not None and _tcp_thread.is_alive():
            return

        try:
            _tcp_server = RobotStatusTCPServer(
                (HOST, PORT),
                StatusHandler,
            )
        except OSError as exc:
            _tcp_server = None
            print(f"[TCP] Failed to start on {HOST}:{PORT}: {exc}")
            return

        _tcp_thread = threading.Thread(
            target=_tcp_server.serve_forever,
            name="robot-status-tcp-server",
            daemon=True,
        )
        _tcp_thread.start()

        print(f"[TCP] Status server listening on {HOST}:{PORT}")


def stop_tcp_server():
    """关闭 TCP 服务端，供 FastAPI 关闭时调用。"""
    global _tcp_server, _tcp_thread

    with _server_lock:
        server = _tcp_server
        thread = _tcp_thread

        if server is None:
            return

        server.running = False

    # shutdown() 应从 serve_forever 所在线程之外调用
    server.shutdown()
    server.server_close()

    if thread is not None:
        thread.join(timeout=3.0)

    with _server_lock:
        _tcp_server = None
        _tcp_thread = None

    print("[TCP] Status server stopped")
