
import json
import socket
import threading
import time
from datetime import datetime

from app.robot import robots
from app.ros2_bridge import get_position


HOST = "0.0.0.0"
PORT = 9000
SEND_INTERVAL = 1.0

_server_socket = None
_server_thread = None
_stop_event = threading.Event()


def start_tcp_server():
    """启动 TCP 服务器。"""
    global _server_socket, _server_thread

    if _server_thread is not None and _server_thread.is_alive():
        return
    #创建套接字
    _server_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )
    #绑定和监听
    _server_socket.bind((HOST, PORT))
    _server_socket.listen()
    # 清除停止信号
    _stop_event.clear()
    #监听工作放到一个独立线程中
    _server_thread = threading.Thread(
        target=accept_clients,
        daemon=True,
    )
    _server_thread.start()

    print(f"[TCP] Server listening on {HOST}:{PORT}")


def build_status_message():
    """获取两台机器人的最新状态。"""
    robot_statuses = {}
    #遍历两台机器人
    for robot_id, robot in robots.items():
        #获取状态信息，通过from app.robot import robots
        status = robot.get_status()
        #获取实际位置，通过from app.ros2_bridge import get_position
        position = get_position(robot_id)
        #更新状态字典
        status["position"] = position
        status["online"] = position is not None
        #将 A、B 两台机器人的状态放进同一个字典
        robot_statuses[robot_id] = status

    return {
        "type": "robot_status",
        "robots": robot_statuses,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

#等待客户端连接
def accept_clients():
    """接收客户端，为每个客户端创建线程。"""
    while not _stop_event.is_set():
        try:
            conn, addr = _server_socket.accept()
        except OSError:
            break
        

        threading.Thread(
            target=handle_client,
            args=(conn, addr),
            daemon=True,
        ).start()

#	向已经连接的客户端发送数据
def handle_client(conn, addr):
    """定时向客户端发送机器人状态。"""
    print(f"[TCP] Client connected: {addr}")

    try:
        #只要没有收到停止信号，就不断执行循环。
        while not _stop_event.is_set():
            #获取信息
            message = build_status_message()
            #转换成json格式并且编码发送，将中文正常显示，'\n'给每条消息添加换行符，作为消息边界
            payload = (
                json.dumps(message, ensure_ascii=False) + "\n"
            ).encode("utf-8")

            conn.sendall(payload)
            #没有收到停止信号：等待 1 秒后返回 False，继续循环，收到停止信号：立即返回 True，执行 break。
            if _stop_event.wait(SEND_INTERVAL):
                break
    #异常处理
    except OSError as exc:
        print(f"[TCP] Client disconnected: {addr} ({exc})")
    #资源释放
    finally:
        conn.close()
        print(f"[TCP] Connection closed: {addr}")


def stop_tcp_server():
    """停止 TCP 服务器。"""
    global _server_socket, _server_thread

    _stop_event.set()

    if _server_socket is not None:
        _server_socket.close()
        _server_socket = None

    if _server_thread is not None:
        #让当前线程等待指定线程结束。
        _server_thread.join(timeout=3.0)
        _server_thread = None

    print("[TCP] Server stopped")
