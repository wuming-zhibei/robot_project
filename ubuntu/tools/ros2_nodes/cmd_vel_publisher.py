
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class CmdVelPublisher(Node):
    def __init__(self):
        super().__init__("cmd_vel_publisher")
        self.publisher = self.create_publisher(
            Twist, "/cmd_vel", 10
        )

        # 保存当前指令
        self.linear_x = 0.0
        self.angular_z = 0.0

        # 每 0.1 秒重复发布一次
        self.timer = self.create_timer(
            0.1, self.publish_current_velocity
        )

        self.get_logger().info("Publisher started")

    def set_velocity(self, linear_x, angular_z):
        self.linear_x = float(linear_x)
        self.angular_z = float(angular_z)
        self.get_logger().info(
            f"Set command: linear.x={linear_x}, "
            f"angular.z={angular_z}"
        )

    def publish_current_velocity(self):
        msg = Twist()
        msg.linear.x = self.linear_x
        msg.angular.z = self.angular_z
        self.publisher.publish(msg)


def main():
    rclpy.init()
    node = CmdVelPublisher()

    # 单独的 ROS 2 线程负责定时发布，
    # 主线程负责等待用户输入
    import threading
    spin_thread = threading.Thread(
        target=rclpy.spin, args=(node,), daemon=True
    )
    spin_thread.start()

    try:
        print("输入命令：w前进，s后退，a左转，d右转，x停止，q退出")
        while rclpy.ok():
            command = input("命令: ").strip().lower()

            if command == "q":
                break
            elif command == "w":
                node.set_velocity(0.05, 0.0)
            elif command == "s":
                node.set_velocity(-0.05, 0.0)
            elif command == "a":
                node.set_velocity(0.0, 0.5)
            elif command == "d":
                node.set_velocity(0.0, -0.5)
            elif command == "x":
                node.set_velocity(0.0, 0.0)
            else:
                print("无效命令，请重新输入")

    finally:
        node.set_velocity(0.0, 0.0)
        # 留出一点时间发送停止指令
        import time
        time.sleep(0.2)
        node.destroy_node()
        rclpy.shutdown()
        spin_thread.join(timeout=1.0)


if __name__ == "__main__":
    main()
