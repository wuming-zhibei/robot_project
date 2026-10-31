
import random
import threading
from threading import Thread

from fastapi import FastAPI, HTTPException

from app.model import MoveRequest, TaskRequest
from app.robot import robots
from app.ros2_bridge import (
    start_ros2,
    send_velocity,
    get_position,
)
from app.tcp_server import start_tcp_server, stop_tcp_server


app = FastAPI(title="Webots Robot Control API")

# 两台机器人分别管理自己的任务线程
task_threads = {
    "a": None,
    "b": None,
}

task_locks = {
    "a": threading.Lock(),
    "b": threading.Lock(),
}


def get_robot(robot_id: str):
    """根据机器人编号获取对应的状态对象。"""
    robot = robots.get(robot_id)

    if robot is None:
        raise HTTPException(
            status_code=404,
            detail=f"Robot '{robot_id}' not found",
        )

    return robot


def direction_to_velocity(direction: str, speed: int):
    """将 API 的方向和速度转换为 ROS 2 的线速度、角速度。"""
    ratio = speed / 50.0

    if direction == "forward":
        return 0.025 * ratio, 0.0

    if direction == "backward":
        return -0.025 * ratio, 0.0

    if direction == "left":
        return 0.0, 0.25 * ratio

    if direction == "right":
        return 0.0, -0.25 * ratio

    return 0.0, 0.0


def cancel_robot_task(robot_id: str):
    """只取消指定机器人的任务，并向对应话题发送停止命令。"""
    robot = get_robot(robot_id)

    # 设置该机器人的停止事件
    robot.stop()

    # 只等待该机器人的任务线程退出
    thread = task_threads[robot_id]
    if thread is not None and thread.is_alive():
        thread.join()

    task_threads[robot_id] = None

    # 停止对应的 Webots 机器人
    send_velocity(0.0, 0.0, robot_id=robot_id)


@app.on_event("startup")
def start_event():
    """FastAPI 启动时初始化 ROS 2 桥接节点。"""
    start_ros2()
    start_tcp_server()


@app.on_event("shutdown")
def shutdown_event():
    """FastAPI 关闭时，停止 TCP 状态服务。"""
    stop_tcp_server()  
      

@app.get("/robots/{robot_id}/status")
def get_status(robot_id: str):
    """查询指定机器人的软件状态和 Webots 实际位置。"""
    robot = get_robot(robot_id)

    status = robot.get_status()
    position = get_position(robot_id)

    if position is not None:
        robot.position = position

    status["position"] = position
    status["online"] = position is not None

    return status


@app.get("/robots/a/sensor")
def get_sensor():
    """返回模拟传感器数据，目前尚未连接真实传感器。"""
    return {
        "temperature": round(random.uniform(20, 30), 2),
        "humidity": round(random.uniform(40, 70), 2),
        "battery": round(random.uniform(60, 100), 2),
        "distance": round(random.uniform(10, 200), 2),
        "simulated": True,
    }


@app.post("/robots/{robot_id}/move")
def move(robot_id: str, request: MoveRequest):
    """控制指定机器人向前、向后、向左或向右移动。"""
    robot = get_robot(robot_id)

    cancel_robot_task(robot_id)

    robot.move(request.direction, request.speed)

    linear_x, angular_z = direction_to_velocity(
        request.direction,
        request.speed,
    )

    send_velocity(
        linear_x,
        angular_z,
        robot_id=robot_id,
    )

    return {
        "success": True,
        "message": f"Robot {robot_id} command sent",
        "robot_id": robot_id,
        "direction": robot.direction,
        "speed": robot.speed,
    }


@app.post("/robots/{robot_id}/stop")
def stop(robot_id: str):
    """停止指定机器人，不影响另一台机器人。"""
    get_robot(robot_id)

    cancel_robot_task(robot_id)

    return {
        "success": True,
        "message": f"Robot {robot_id} stopped",
        "robot_id": robot_id,
    }


def run_square(robot_id: str = "a"):
    """让指定机器人执行正方形轨迹。"""
    robot = get_robot(robot_id)

    try:
        for _ in range(4):
            if robot.stop_event.is_set():
                break

            # 前进
            robot.direction = "forward"
            robot.speed = 50

            send_velocity(
                0.08,
                0.0,
                robot_id=robot_id,
            )

            if robot.stop_event.wait(2.0):
                break

            # 原地左转
            robot.direction = "left"
            robot.speed = 30

            send_velocity(
                0.0,
                0.26,
                robot_id=robot_id,
            )

            if robot.stop_event.wait(3.63):
                break

    finally:
        send_velocity(0.0, 0.0, robot_id=robot_id)
        robot.finish_task()


@app.post("/robots/a/task")
def start_task(request: TaskRequest):
    """启动 A 机器人的预设任务。"""
    robot_id = "a"
    robot = get_robot(robot_id)

    cancel_robot_task(robot_id)

    robot.start_task(request.task)

    if request.task == "square":
        thread = Thread(
            target=run_square,
            args=(robot_id,),
            daemon=True,
        )
        task_threads[robot_id] = thread
        thread.start()

    else:
        linear_x, angular_z = direction_to_velocity(
            request.task,
            robot.speed,
        )

        send_velocity(
            linear_x,
            angular_z,
            robot_id=robot_id,
        )

    return {
        "success": True,
        "message": "Task started",
        "robot_id": robot_id,
        "task": request.task,
    }
