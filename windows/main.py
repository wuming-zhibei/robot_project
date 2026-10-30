
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile

from recognize_face import (
    load_model,
    load_database,
    recognize_face,
)
from robot_status_client import RobotStatusClient

from camera_service import CameraRecognitionService


model = None
database = {}
camera_service = CameraRecognitionService(camera_index=0)


# Windows 后台 TCP 客户端：持续接收 Ubuntu 的机器人状态
robot_client = RobotStatusClient()

# 人员与机器人之间的固定对应关系
PERSON_ROBOT_MAP = {
    "person_a": "robot_a",
    "person_b": "robot_b",
    "unknown": None,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, database

    print("正在加载人脸识别模型...")
    model = load_model()
    database = load_database(model)

    if not database:
        model = None
        raise RuntimeError(
            "没有加载到有效参考照片，请检查 faces 目录"
        )

    print("人脸识别服务初始化完成")

    # 启动后台线程，接收 Ubuntu 推送的机器人状态
    robot_client.start()
    print("机器人状态接收客户端已启动")

    try:
        yield
    finally:
        # 关闭服务时释放 TCP 连接及人脸识别资源
        robot_client.stop()
        model = None
        database = {}
        print("人脸识别服务已关闭")


app = FastAPI(
    title="Robot Face Recognition API",
    description="人脸识别与机器人实时状态查询服务",
    version="1.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    """检查人脸识别模型和参考人员是否已初始化。"""
    return {
        "online": model is not None,
        "model": "buffalo_l",
        "loaded_persons": sorted(database.keys()),
    }


@app.post("/recognize")
async def recognize(file: UploadFile = File(...)):
    """接收图片，识别其中的每张人脸。"""

    if model is None or not database:
        raise HTTPException(
            status_code=503,
            detail="人脸识别服务尚未初始化",
        )

    if file.content_type not in {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/bmp",
    }:
        raise HTTPException(
            status_code=415,
            detail="请上传 JPEG、PNG、WEBP 或 BMP 图片",
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="上传的图片为空",
        )

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="图片不能超过 10 MB",
        )

    image_array = np.frombuffer(content, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(
            status_code=400,
            detail="无法解码图片，请检查文件是否损坏",
        )

    faces = model.get(image)
    results = []

    for face in faces:
        person_id, score = recognize_face(
            face.normed_embedding,
            database,
        )

        robot_id = PERSON_ROBOT_MAP.get(person_id)

        results.append({
            "person_id": person_id,
            "robot_id": robot_id,
            "similarity": round(float(score), 4),
            "bbox": [
                round(float(value), 1)
                for value in face.bbox
            ],
        })

    return {
        "status": "ok" if results else "no_face",
        "face_count": len(results),
        "faces": results,
    }


@app.get("/robots")
def get_robots():
    """获取最近收到的两台机器人的完整状态消息。"""

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


@app.get("/person-status/{person_id}")
def get_person_status(person_id: str):
    """根据人员身份，查询其对应机器人的最新状态。"""

    if person_id not in PERSON_ROBOT_MAP:
        raise HTTPException(
            status_code=400,
            detail="person_id 必须为 person_a、person_b 或 unknown",
        )

    robot_id = PERSON_ROBOT_MAP[person_id]

    # 未知人员不关联任何机器人
    if robot_id is None:
        return {
            "person_id": person_id,
            "robot_id": None,
            "robot_status": None,
            "message": "未识别到已登记人员，不关联机器人",
        }

    status = robot_client.get_status()

    if status is None:
        return {
            "person_id": person_id,
            "robot_id": robot_id,
            "robot_status": None,
            "message": "尚未收到机器人状态",
        }

    robots = status.get("robots", {})
    robot_key = {
    "robot_a": "a",
    "robot_b": "b",
    }.get(robot_id)

    robot_status = robots.get(robot_key) if robot_key else None

    return {
        "person_id": person_id,
        "robot_id": robot_id,
        "robot_status": robot_status,
        "timestamp": status.get("timestamp"),
        "message": (
            "已获取机器人状态"
            if robot_status is not None
            else "状态消息中暂时没有这台机器人的数据"
        ),
    }

@app.post("/camera/start")
def start_camera():
    """启动后台摄像头识别。"""

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
    """停止后台摄像头识别。"""
    camera_service.stop()

    return {
        "stopped": True,
        "message": "摄像头识别已停止",
    }


@app.get("/camera/status")
def get_camera_status():
    """查看摄像头运行情况及当前确认的身份。"""
    return camera_service.get_status()


@app.get("/live-status")
def get_live_status():
    """整合当前识别身份与对应机器人的最新状态。"""

    camera = camera_service.get_status()
    person_id = camera.get("person_id", "unknown")
    robot_id = PERSON_ROBOT_MAP.get(person_id)

    robot_status = None
    timestamp = None

    if robot_id is not None:
        message = robot_client.get_status()

        if message is not None:
            robots = message.get("robots", {})

            robot_key = {
                "robot_a": "a",
                "robot_b": "b",
            }.get(robot_id)

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

    camera = camera_service.get_status()
    person_id = camera.get("person_id", "unknown")
    robot_id = PERSON_ROBOT_MAP.get(person_id)

    # 默认显示未识别状态
    result = {
        "person": person_id,
        "robot": None,
        "online": False,
        "running": False,
        "direction": "unknown",
        "position": None,
        "message": "未识别人员",
    }

    if robot_id is None:
        return result

    result["message"] = "等待机器人状态"

    message = robot_client.get_status()
    if message is None:
        return result

    robot_key = {
        "robot_a": "a",
        "robot_b": "b",
    }.get(robot_id)

    robots = message.get("robots", {})
    robot_status = robots.get(robot_key) if robot_key else None

    if robot_status is None:
        return result

    position = robot_status.get("position")

    result.update({
        "robot": robot_id,
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
