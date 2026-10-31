
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Point


class CmdVelSubscriber(Node):
    def __init__(self):
        super().__init__('cmd_vel_subscriber')

        # 最新的运动指令
        self.linear_x = 0.0
        self.angular_z = 0.0

        # 机器人实际坐标
        self.position_x = 0.0
        self.position_y = 0.0
        self.position_z = 0.0

        self.received_cmd = False
        self.received_position = False

        # 订阅运动指令
        self.cmd_subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_callback,
            10
        )

        # 订阅机器人实际位置
        self.position_subscription = self.create_subscription(
            Point,
            '/robot_position',
            self.position_callback,
            10
        )

        # 每秒统一输出一次
        self.status_timer = self.create_timer(
            1.0,
            self.print_status
        )

        self.get_logger().info(
            'Subscriber started: /cmd_vel and /robot_position'
        )

    def cmd_callback(self, msg):
        self.linear_x = msg.linear.x
        self.angular_z = msg.angular.z
        self.received_cmd = True

    def position_callback(self, msg):
        self.position_x = msg.x
        self.position_y = msg.y
        self.position_z = msg.z
        self.received_position = True

    def print_status(self):
        print('\n========== Robot Status ==========')

        if self.received_cmd:
            print(
                f'Command: linear.x={self.linear_x:.3f} m/s, '
                f'angular.z={self.angular_z:.3f} rad/s'
            )
        else:
            print('Command: waiting for /cmd_vel')

        if self.received_position:
            print(
                f'Position: x={self.position_x:.3f}, '
                f'y={self.position_y:.3f}, '
                f'z={self.position_z:.3f} m'
            )
        else:
            print('Position: waiting for /robot_position')

        print('===================================')


def main():
    rclpy.init()
    node = CmdVelSubscriber()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
