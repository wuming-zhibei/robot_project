import threading

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Point

class Ros2Bridge(Node):
    def __init__(self):
        # 分别保存 A、B 两台机器人的速度指令
        self.linear_x = {"a": 0.0, "b": 0.0}
        self.angular_z = {"a": 0.0, "b": 0.0}
        self.moving = {"a": False, "b": False}

        # 保存 Webots 发布的最新位置
        self.positions = {"a": None, "b": None}
        # 创建速度发布器
        self.velocity_publishers = {
            "a": self.create_publisher(Twist, "/cmd_vel", 10),
            "b": self.create_publisher(Twist, "/robot_b/cmd_vel", 10),
        }

        # 创建位置订阅器
        self.position_subscriptions = {
            "a": self.create_subscription(
                Point,
                "/robot_position",
                lambda msg: self.position_callback(msg, "a"),
                10,
            ),
            "b": self.create_subscription(
                Point,
                "/robot_b/robot_position",
                lambda msg: self.position_callback(msg, "b"),
                10,
            ),
        }
         # 每隔 0.1 秒重新发布正在执行的速度指令
        self.timer = self.create_timer(
            0.1,
            self.publish_current_velocity,
        )

        self.get_logger().info(
            "ROS 2 bridge started for robots A and B"
        )
    def publish_cmd_vel(self, robot_id, linear_x, angular_z):
        """向指定机器人的速度话题发布 Twist 消息。"""
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.angular.z = float(angular_z)

        self.velocity_publishers[robot_id].publish(msg)

    def publish_current_velocity(self):
        """定时重复发布两台机器人当前正在执行的速度。"""
        for robot_id in ("a", "b"):
            if self.moving[robot_id]:
                self.publish_cmd_vel(
                    robot_id,
                    self.linear_x[robot_id],
                    self.angular_z[robot_id],
                )
    def position_callback(self, msg, robot_id):
        """接收 Webots 发布的位置并保存。"""
        self.positions[robot_id] = {
            "x": round(msg.x, 4),
            "y": round(msg.y, 4),
            "z": round(msg.z, 4),
        }
_bridge = None
_spin_thread = None

def start_ros2():
    """初始化 ROS 2，并在后台线程运行节点。"""
    global _bridge, _spin_thread
    #只初始化一次ros2环境
    if not rclpy.ok():
        rclpy.init()
    # 防止重复创建节点
    if _bridge is not None:
        return
    _bridge = Ros2Bridge()
     # spin 会持续处理 ROS 2 消息，不能阻塞 FastAPI
    _spin_thread = threading.Thread(
        target=rclpy.spin,
        args=(_bridge,),
        daemon=True,
    )
    _spin_thread.start()
def send_velocity(linear_x, angular_z, robot_id="a"):
    """向指定机器人发送速度指令。"""
    if _bridge is None:
        raise RuntimeError("ROS 2 节点尚未启动")

    if robot_id not in ("a", "b"):
        raise ValueError("robot_id 必须是 'a' 或 'b'")

    # 保存当前速度，供定时器重复发布
    _bridge.linear_x[robot_id] = float(linear_x)
    _bridge.angular_z[robot_id] = float(angular_z)

    if linear_x == 0.0 and angular_z == 0.0:
        # 零速度表示停止
        _bridge.publish_cmd_vel(robot_id, 0.0, 0.0)
        _bridge.moving[robot_id] = False
    else:
        _bridge.moving[robot_id] = True
        _bridge.publish_cmd_vel(
            robot_id,
            linear_x,
            angular_z,
        )
def get_position(robot_id="a"):
    """获取指定机器人的最新实际位置。"""
    if _bridge is None:
        return None

    if robot_id not in ("a", "b"):
        raise ValueError("robot_id 必须是 'a' 或 'b'")

    position = _bridge.positions[robot_id]

    # 返回副本，避免外部直接修改内部位置数据
    return position.copy() if position is not None else None
def stop_ros2():
    """关闭 ROS 2 节点和后台线程。"""
    global _bridge, _spin_thread

    if _bridge is None:
        return

    # 通知 ROS 2 停止 spin
    if rclpy.ok():
        rclpy.shutdown()

    # 等待后台线程退出
    if _spin_thread is not None:
        _spin_thread.join(timeout=3.0)

    # 释放节点资源
    _bridge.destroy_node()

    _bridge = None
    _spin_thread = None

