
import threading


class Robot:
    def __init__(self, robot_id="a"):
        self.robot_id = robot_id

        # 基本状态
        self.online = True
        self.running = False
        self.direction = "stop"
        self.speed = 0

        # 位置由 main.py 根据 Webots 的实际位置消息更新
        self.position = {
            "x": 0,
            "y": 0,
        }

        # 当前任务
        self.current_task = None

        # 每台机器人拥有独立的任务取消事件
        self.stop_event = threading.Event()

    def get_status(self):
        """返回当前机器人的软件状态。"""
        return {
            "robot_id": self.robot_id,
            "online": self.online,
            "running": self.running,
            "direction": self.direction,
            "speed": self.speed,
            "position": self.position,
            "current_task": self.current_task,
        }

    def move(self, direction, speed):
        """更新当前机器人的运动状态。"""
        self.stop_event.clear()
        self.running = True
        self.direction = direction
        self.speed = speed

    def stop(self):
        """停止当前机器人的运动状态，并通知任务退出。"""
        self.stop_event.set()
        self.running = False
        self.direction = "stop"
        self.speed = 0
        self.current_task = None

    def start_task(self, task):
        """记录当前机器人正在执行的任务。"""
        self.stop_event.clear()
        self.current_task = task
        self.running = True

        task_settings = {
            "forward": ("forward", 50),
            "backward": ("backward", 50),
            "left": ("left", 30),
            "right": ("right", 30),
            "square": ("forward", 50),
        }

        if task not in task_settings:
            self.current_task = None
            self.running = False
            self.direction = "stop"
            self.speed = 0
            raise ValueError(f"Unsupported task: {task}")

        self.direction, self.speed = task_settings[task]

    def finish_task(self):
        """记录当前任务结束。"""
        self.running = False
        self.direction = "stop"
        self.speed = 0
        self.current_task = None


# 两台机器人使用同一个类，但拥有完全独立的状态
robot_a = Robot("a")
robot_b = Robot("b")

robots = {
    "a": robot_a,
    "b": robot_b,
}

# 临时保留旧变量名，确保 main.py 尚未重构时仍能运行
robot = robot_a
