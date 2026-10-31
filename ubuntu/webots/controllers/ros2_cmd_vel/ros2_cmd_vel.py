
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Point
from controller import Supervisor



class Ros2CmdVelController(Node):
    def __init__(self, robot):
        self.robot = robot
        self.robot_name = robot.getName()

        super().__init__(f'{self.robot_name}_cmd_vel_controller')

        # 获取机器人在 Webots 世界中的实际坐标
        self.robot_node = robot.getSelf()
        self.translation_field = self.robot_node.getField('translation')

        # 获取四个车轮
        self.wheels = [
            robot.getDevice('wheel1'),
            robot.getDevice('wheel2'),
            robot.getDevice('wheel3'),
            robot.getDevice('wheel4'),
        ]

        # 设置车轮为速度控制模式
        for wheel in self.wheels:
            wheel.setPosition(float('inf'))
            wheel.setVelocity(0.0)

        self.max_speed = 6.28
        self.wheel_base = 0.2
        self.wheel_radius = 0.025

        # 当前接收到的速度指令
        self.linear_x = 0.0
        self.angular_z = 0.0
        self.last_command_time = self.get_clock().now()

        # 订阅 ROS 2 速度指令
        if self.robot_name == 'robot_b':
            cmd_topic = '/robot_b/cmd_vel'
        else:
            cmd_topic = '/cmd_vel'

        self.subscription = self.create_subscription(
            Twist,
            cmd_topic,
            self.command_callback,
            10
        )

        # 发布机器人实际坐标
        if self.robot_name == 'robot_b':
            position_topic = '/robot_b/robot_position'
        else:
            position_topic = '/robot_position'

        self.position_publisher = self.create_publisher(
            Point,
            position_topic,
            10
        )

        self.get_logger().info(
            f'Controller started for {self.robot_name}: '
            f'subscribing {cmd_topic}, '
            f'publishing {position_topic}'
        )

    def command_callback(self, msg):
        # 保存最新速度指令
        self.linear_x = msg.linear.x
        self.angular_z = msg.angular.z
        self.last_command_time = self.get_clock().now()

        self.get_logger().info(
            f'Received cmd_vel: '
            f'linear.x={self.linear_x:.2f}, '
            f'angular.z={self.angular_z:.2f}'
        )

    def update_motors(self):
        # 超过 1 秒没有收到新指令，就停止车轮
        elapsed = (
            self.get_clock().now() - self.last_command_time
        ).nanoseconds / 1e9

        if elapsed > 1.0:
            left_speed = 0.0
            right_speed = 0.0
        else:
            # 将线速度、角速度转换为左右车轮速度
            left_speed = (
                self.linear_x
                - self.angular_z * self.wheel_base / 2
            ) / self.wheel_radius

            right_speed = (
                self.linear_x
                + self.angular_z * self.wheel_base / 2
            ) / self.wheel_radius

        # 限制车轮速度
        left_speed = max(
            -self.max_speed,
            min(self.max_speed, left_speed)
        )
        right_speed = max(
            -self.max_speed,
            min(self.max_speed, right_speed)
        )

        # 左右两侧车轮使用相同速度
        self.wheels[0].setVelocity(left_speed)
        self.wheels[1].setVelocity(right_speed)
        self.wheels[2].setVelocity(left_speed)
        self.wheels[3].setVelocity(right_speed)

    def publish_position(self):
        # 读取 Webots 中机器人的实际世界坐标
        position = self.translation_field.getSFVec3f()

        msg = Point()
        msg.x = float(position[0])
        msg.y = float(position[1])
        msg.z = float(position[2])

        self.position_publisher.publish(msg)


def main():
    # 使用 Supervisor 获取机器人实际位置
    robot = Supervisor()
    timestep = int(robot.getBasicTimeStep())

    rclpy.init()
    node = Ros2CmdVelController(robot)

    try:
        while robot.step(timestep) != -1:
            # 处理 ROS 2 消息
            rclpy.spin_once(node, timeout_sec=0.0)

            # 控制车轮
            node.update_motors()

            # 发布实际坐标
            node.publish_position()

    except KeyboardInterrupt:
        pass
    finally:
        # 退出时停止车轮
        for wheel in node.wheels:
            wheel.setVelocity(0.0)

        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
