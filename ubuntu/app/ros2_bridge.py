import rclpy
import threading
from rclpy.node import Node
from geometry_msgs.msg import Twist, Point


class Ros2Bridge(Node):
    def __init__(self):
        super().__init__("fastapi_cmd_vel_bridge")

        # A、B 两台机器人的独立速度状态
        self.linear_x = {"a": 0.0, "b": 0.0}
        self.angular_z = {"a": 0.0, "b": 0.0}
        self.moving = {"a": False, "b": False}

        # 分别保存两台机器人的最新位置
        self.positions = {"a": None, "b": None}

        # 分别创建速度发布器和位置订阅器
        self.velocity_publishers = {
            "a": self.create_publisher(Twist, "/cmd_vel", 10),
            "b": self.create_publisher(Twist, "/robot_b/cmd_vel", 10),
        }

        self.position_subscriptions = [
            self.create_subscription(
                Point,
                "/robot_position",
                lambda msg: self.position_callback(msg, "a"),
                10,
            ),
            self.create_subscription(
                Point,
                "/robot_b/robot_position",
                lambda msg: self.position_callback(msg, "b"),
                10,
            ),
        ]

        # 每隔 0.1 秒重新发布正在执行的速度指令
        self.timer = self.create_timer(
            0.1, self.publish_current_velocity
        )

        self.get_logger().info(
            "FastAPI bridge started for robots A and B"
        )

    def publish_cmd_vel(self, robot_id, linear_x, angular_z):
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.angular.z = float(angular_z)

        self.velocity_publishers[robot_id].publish(msg)

    def publish_current_velocity(self):
        for robot_id in ("a", "b"):
            if self.moving[robot_id]:
                self.publish_cmd_vel(
                    robot_id,
                    self.linear_x[robot_id],
                    self.angular_z[robot_id],
                )

    def position_callback(self, msg, robot_id):
        self.positions[robot_id] = {
            "x": round(msg.x, 4),
            "y": round(msg.y, 4),
            "z": round(msg.z, 4),
        }


_bridge = None
_spin_thread = None


def start_ros2():
    global _bridge, _spin_thread

    if _bridge is not None:
        return

    if not rclpy.ok():
        rclpy.init()

    _bridge = Ros2Bridge()

    _spin_thread = threading.Thread(
        target=rclpy.spin,
        args=(_bridge,),
        daemon=True,
    )
    _spin_thread.start()


def send_velocity(linear_x, angular_z, robot_id="a"):
    if _bridge is None:
        raise RuntimeError("ROS 2 节点尚未启动")

    if robot_id not in ("a", "b"):
        raise ValueError("robot_id 必须是 'a' 或 'b'")

    _bridge.linear_x[robot_id] = float(linear_x)
    _bridge.angular_z[robot_id] = float(angular_z)

    if linear_x == 0.0 and angular_z == 0.0:
        _bridge.publish_cmd_vel(robot_id, 0.0, 0.0)
        _bridge.moving[robot_id] = False
    else:
        _bridge.moving[robot_id] = True
        _bridge.publish_cmd_vel(
            robot_id, linear_x, angular_z
        )


def get_position(robot_id="a"):
    if _bridge is None:
        return None

    if robot_id not in ("a", "b"):
        raise ValueError("robot_id 必须是 'a' 或 'b'")

    return _bridge.positions[robot_id]
def get_motion_state(robot_id="a"):
    if _bridge is None:
        return None

    if robot_id not in ("a", "b"):
        raise ValueError("robot_id 必须是 'a' 或 'b'")

    return {
        "running": _bridge.moving[robot_id],
        "linear_x": _bridge.linear_x[robot_id],
        "angular_z": _bridge.angular_z[robot_id],
    }