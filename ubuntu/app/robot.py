import threading


class Robot:
    def __init__(self, robot_id):
        # 机器人编号
        self.robot_id = robot_id

        # 机器人基本状态
        self.online = False
        self.running = False
        self.direction = "stop"
        self.speed = 0

        # Webots 通过 ROS 2 发送的实际位置
        self.position = {
            "x": 0,
            "y": 0,
            "z": 0,
        }

        # 当前任务名称
        self.current_task = None

        # 控制线程的事件对象
        self.stop_event = threading.Event()

    def get_status(self):
        """返回机器人的当前状态。"""
        return {
            "robot_id": self.robot_id,
            "online": self.online,
            "running": self.running,
            "direction": self.direction,
            "speed": self.speed,
            "position": self.position.copy(),
            "current_task": self.current_task,
        }

    def move(self, direction, speed):
        """更新机器人的运动状态。"""
        self.stop_event.clear()
        self.running = True
        self.direction = direction
        self.speed = speed

    def stop(self):
        """停止当前任务，并重置运动状态。"""
        self.stop_event.set()
        self.running = False
        self.direction = "stop"
        self.speed = 0
        self.current_task = None

    def start_task(self, task):
        """记录任务，并设置任务开始时的运动状态。"""
        task_settings = {
            "forward": ("forward", 50),
            "backward": ("backward", 50),
            "left": ("left", 30),
            "right": ("right", 30),
            "square": ("forward", 50),
        }

        if task not in task_settings:
            raise ValueError(f"Unsupported task: {task}")

        self.stop_event.clear()
        self.current_task = task
        self.running = True
        self.direction, self.speed = task_settings[task]

    def finish_task(self):
        """任务正常结束后，重置运动状态。"""
        self.running = False
        self.direction = "stop"
        self.speed = 0
        self.current_task = None


# 创建两台独立的机器人对象
robot_a = Robot("a")
robot_b = Robot("b")

robots = {
    "a": robot_a,
    "b": robot_b
}