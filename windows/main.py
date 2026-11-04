
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from recognize_face import load_model, load_database
from camera_service import CameraRecognitionService
from robot_status_client import RobotStatusClient


# 人脸识别模型和人员特征数据库
model = None
database = {}

# 摄像头识别服务
camera_service = CameraRecognitionService(camera_index=0)

# Ubuntu 机器人状态接收客户端
robot_client = RobotStatusClient()

# 人员与机器人之间的对应关系
PERSON_ROBOT_MAP = {
    "person_a": "robot_a",
    "person_b": "robot_b",
    "unknown": None,
}

# 机器人名称与状态字典键之间的对应关系
ROBOT_KEY_MAP = {
    "robot_a": "a",
    "robot_b": "b",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理服务启动和关闭时的资源。"""
    global model, database

    # 启动时加载人脸识别模型和人员数据库
    print("正在加载人脸识别模型...")
    model = load_model()
    database = load_database(model)

    if not database:
        model = None
        raise RuntimeError("没有加载到有效参考照片，请检查 faces 目录")

    print("人脸识别服务初始化完成")

    # 启动 TCP 客户端，接收 Ubuntu 发送的机器人状态
    robot_client.start()
    print("机器人状态接收客户端已启动")

    try:
        yield
    finally:
        # 关闭时停止 TCP 客户端并释放资源
        robot_client.stop()
        camera_service.stop()

        model = None
        database = {}

        print("人脸识别服务已关闭")


app = FastAPI(
    title="Robot Face Recognition API",
    description="摄像头人脸识别与机器人状态查询服务",
    version="1.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    """检查人脸识别服务是否初始化。"""
    return {
        "online": model is not None,
        "model": "buffalo_l",
        "loaded_persons": sorted(database.keys()),
    }


@app.get("/robots")
def get_robots():
    """获取两台机器人的最新状态。"""
    status = robot_client.get_status()

    if status is None:
        return {
            "received": False,
            "message": "尚未收到机器人状态，请检查 Ubuntu TCP 服务",
            "robots": {},
        }

    return {
        "received": True,
        "timestamp": status.get("timestamp"),
        "robots": status.get("robots", {}),
    }


@app.post("/camera/start")
def start_camera():
    """启动摄像头识别。"""
    if model is None or not database:
        raise HTTPException(
            status_code=503,
            detail="人脸识别模型尚未初始化",
        )

    started = camera_service.start(model, database)

    return {
        "started": started,
        "message": (
            "摄像头识别线程已启动"
            if started
            else "摄像头识别已经在运行"
        ),
    }


@app.post("/camera/stop")
def stop_camera():
    """停止摄像头识别。"""
    camera_service.stop()

    return {
        "stopped": True,
        "message": "摄像头识别已停止",
    }


@app.get("/camera/status")
def get_camera_status():
    """获取当前摄像头识别状态。"""
    return camera_service.get_status()


@app.get("/live-status")
def get_live_status():
    """获取当前识别人员及其对应机器人的状态。"""
    #获取当前人员对应的机器人id
    camera = camera_service.get_status()
    person_id = camera.get("person_id", "unknown")
    robot_id = PERSON_ROBOT_MAP.get(person_id)

    robot_status = None
    timestamp = None

    if robot_id is not None:
        message = robot_client.get_status()

        if message is not None:
            robots = message.get("robots", {})
            robot_key = ROBOT_KEY_MAP.get(robot_id)

            if robot_key:
                robot_status = robots.get(robot_key)

            timestamp = message.get("timestamp")

    return {
        "camera": camera,
        "person_id": person_id,
        "robot_id": robot_id,
        "robot_status": robot_status,
        "timestamp": timestamp,
    }



@app.get("/display-status")
def get_display_status():
    """提供适合 ESP32 OLED 显示的精简状态。"""

    # 直接复用 live-status 获取最新数据
    live = get_live_status()

    person_id = live["person_id"]
    robot_id = live["robot_id"]
    robot_status = live["robot_status"]

    # 默认显示状态
    result = {
        "person": person_id,
        "robot": robot_id,
        "online": False,
        "running": False,
        "direction": "unknown",
        "position": None,
        "message": "未识别人员",
    }

    # 没有识别到人员
    if robot_id is None:
        return result

    # 已识别人员，但没有获取到机器人状态
    if robot_status is None:
        result["message"] = "等待机器人状态"
        return result

    position = robot_status.get("position")

    result.update({
        "online": bool(robot_status.get("online", False)),
        "running": bool(robot_status.get("running", False)),
        "direction": robot_status.get("direction", "unknown"),
        "position": (
            {
                "x": round(float(position["x"]), 3),
                "y": round(float(position["y"]), 3),
            }
            if isinstance(position, dict)
            and "x" in position
            and "y" in position
            else None
        ),
        "message": (
            "机器人在线"
            if robot_status.get("online", False)
            else "机器人离线"
        ),
    })

    return result