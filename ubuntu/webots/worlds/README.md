# 基于 FastAPI、ROS 2 与 Webots 的机器人控制系统

## 1. 项目简介

本项目使用 Python、FastAPI、ROS 2 Humble 和 Webots，构建一个四轮移动机器人的仿真控制系统。

系统采用客户端与服务端分离的结构。Windows 客户端通过 HTTP 请求访问运行在 Ubuntu 虚拟机中的 FastAPI 服务；FastAPI 通过 ROS 2 桥接节点发布机器人速度指令；Webots 中的机器人控制器订阅 `/cmd_vel` 话题，将速度指令转换为车轮运动，实现对仿真机器人的控制。

此外，项目还提供独立的 ROS 2 发布节点和订阅节点，用于命令行控制机器人以及监测速度指令和距离传感器数据。


## 2. 项目功能

### 2.1 FastAPI HTTP 控制

- 查询机器人状态。
- 获取传感器接口数据。
- 控制机器人前进、后退、左转和右转。
- 停止机器人。
- 执行预设的正方形运动轨迹。
- 通过 HTTP 接口实现远程控制。

### 2.2 ROS 2 话题控制

- 通过 ROS 2 发布节点发送速度指令。
- 使用 `/cmd_vel` 话题传递机器人运动命令。
- 通过 ROS 2 订阅节点监测速度指令。
- 发布并接收 Webots 距离传感器数据。

### 2.3 Webots 仿真

- 使用 Webots 仿真四轮移动机器人。
- 根据 ROS 2 速度指令控制车轮。
- 读取距离传感器数据并发布到 ROS 2 话题。
- 在仿真环境中验证机器人运动控制效果。

## 3. 系统架构

系统的主要控制流程如下：

```text
Windows HTTP 客户端
        |
        | HTTP 请求
        v
Ubuntu：FastAPI 服务
        |
        v
ROS 2 桥接节点
        |
        | /cmd_vel
        | geometry_msgs/msg/Twist
        v
Webots 机器人控制器
        |
        v
四轮机器人仿真运动
```

距离传感器数据的传递流程如下：

```text
Webots 距离传感器
        |
        v
Webots 机器人控制器
        |
        | /distance_sensors
        | std_msgs/msg/Float32MultiArray
        v
ROS 2 订阅节点
        |
        v
终端输出传感器数据
```

需要注意：FastAPI 的 `/sensor` 接口当前返回随机模拟数据；Webots 中的距离传感器则通过 `/distance_sensors` 话题发布实际仿真传感器读数。两者属于不同的数据来源。

## 4. 开发环境

| 项目 | 使用技术 |
|---|---|
| 服务端操作系统 | Ubuntu 22.04 |
| 客户端操作系统 | Windows |
| 编程语言 | Python |
| Web 框架 | FastAPI |
| ASGI 服务器 | Uvicorn |
| 数据验证 | Pydantic |
| 机器人通信框架 | ROS 2 Humble |
| 机器人仿真软件 | Webots |
| HTTP 客户端库 | Requests |

## 5. 项目目录结构

```text
robot_service/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── model.py
│   ├── robot.py
│   └── ros2_bridge.py
├── client/
│   └── client.py
├── ros2_nodes/
│   ├── cmd_vel_publisher.py
│   └── cmd_vel_subscriber.py
├── webots/
│   ├── controllers/
│   │   └── ros2_cmd_vel/
│   │       └── ros2_cmd_vel.py
│   └── worlds/
│       ├── 4_wheels_robot.wbt
│       └── .4_wheels_robot.wbproj
├── requirements.txt
└── README.md
```

### 主要文件说明

| 文件 | 作用 |
|---|---|
| `app/main.py` | 创建 FastAPI 应用并定义 HTTP 接口 |
| `app/model.py` | 定义请求数据模型并验证输入参数 |
| `app/robot.py` | 管理机器人应用层状态、运动命令及任务逻辑 |
| `app/ros2_bridge.py` | 创建 ROS 2 桥接节点，向 `/cmd_vel` 发布速度指令 |
| `client/client.py` | Windows HTTP 客户端程序 |
| `ros2_nodes/cmd_vel_publisher.py` | 命令行速度指令发布节点 |
| `ros2_nodes/cmd_vel_subscriber.py` | 速度指令和距离传感器数据订阅节点 |
| `webots/controllers/ros2_cmd_vel/ros2_cmd_vel.py` | 订阅速度指令、控制机器人车轮并发布距离传感器数据 |
| `webots/worlds/4_wheels_robot.wbt` | Webots 仿真世界文件 |
| `requirements.txt` | 记录 FastAPI 服务使用的 Python 依赖 |
| `README.md` | 项目说明与运行指南 |

## 6. 安装与启动

### 6.1 安装 Python 依赖

进入 Ubuntu 项目目录：

```bash
cd ~/robot_service
```

激活已有虚拟环境：

```bash
source venv/bin/activate
```

安装项目依赖：

```bash
pip install -r requirements.txt
```

注意：FastAPI 服务还需要能够导入 ROS 2 的 Python 模块。若运行时提示找不到 `rclpy`，需要检查 ROS 2 环境和 Python 虚拟环境配置。

### 6.2 配置 ROS 2 环境

在 Ubuntu 终端执行：

```bash
source /opt/ros/humble/setup.bash
```

检查 ROS 2 发行版：

```bash
echo $ROS_DISTRO
```

正常情况下应输出：

```text
humble
```

### 6.3 启动 Webots

打开项目中的仿真世界：

```bash
webots ~/robot_service/webots/worlds/4_wheels_robot.wbt
```

检查以下事项：

- Webots 成功加载四轮机器人。
- 机器人使用 `ros2_cmd_vel` 控制器。
- 仿真已经启动。
- 控制器没有出现 ROS 2 导入或话题通信错误。

### 6.4 启动 FastAPI 服务

在已配置 ROS 2 环境的终端中执行：

```bash
cd ~/robot_service
source /opt/ros/humble/setup.bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

保持终端运行。

在 Ubuntu 本机浏览器中，可以访问：

```text
http://127.0.0.1:8000/docs
```

该地址用于查看 FastAPI 自动生成的接口文档。

从 Windows 访问时，需要使用 Ubuntu 虚拟机的可达 IP 地址，或者使用已经配置好的 VMware NAT 端口转发地址。

## 7. HTTP API 接口

当前项目提供以下主要接口。请求参数和响应字段以实际代码及 `/docs` 页面为准。

| 请求方法 | 接口 | 功能 |
|---|---|---|
| GET | `/status` | 查询机器人应用层状态 |
| GET | `/sensor` | 获取随机模拟传感器数据 |
| POST | `/move` | 发送机器人运动指令 |
| POST | `/stop` | 请求机器人停止 |
| POST | `/task` | 执行预设任务 |

### 7.1 查询机器人状态

```http
GET /status
```

该接口用于查询机器人当前的应用层状态，例如在线状态、运行状态、运动方向、速度、位置以及当前任务等。实际返回字段以 `app/robot.py` 和 `app/main.py` 为准。

### 7.2 获取传感器数据

```http
GET /sensor
```

该接口当前使用随机模拟数据，包含温度、湿度、电池电量和距离等字段。

这些数据用于演示 HTTP 接口的数据读取功能，并不代表 Webots 距离传感器的实际测量值。

### 7.3 控制机器人移动

```http
POST /move
Content-Type: application/json
```

请求体示例：

```json
{
  "direction": "forward",
  "speed": 50
}
```

支持的运动方向包括：

- `forward`：前进
- `backward`：后退
- `left`：左转
- `right`：右转

速度参数的有效范围以 `app/model.py` 中的请求模型定义为准。

FastAPI 接收到命令后，通过 ROS 2 桥接节点发布相应的速度指令，最终由 Webots 控制器驱动机器人。

### 7.4 停止机器人

```http
POST /stop
```

该接口用于请求机器人停止运动，并更新应用层状态。

### 7.5 执行正方形轨迹

```http
POST /task
Content-Type: application/json
```

请求体示例：

```json
{
  "task": "square"
}
```

正方形轨迹任务按照项目中的任务执行逻辑控制机器人完成连续运动，形成正方形路径。



## 8. ROS 2 话题控制

### 8.1 速度控制话题

话题名称：

```text
/cmd_vel
```

消息类型：

```text
geometry_msgs/msg/Twist
```

控制器主要使用以下字段：

- `linear.x`：控制机器人前进或后退。
- `angular.z`：控制机器人转向。

可以使用 ROS 2 命令行直接发布一次前进指令：

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
"{linear: {x: 0.05}, angular: {z: 0.0}}"
```

执行前应确保 ROS 2 环境已加载，并且 Webots 仿真及机器人控制器正在运行。

### 8.2 运行 ROS 2 发布节点

在 Ubuntu 终端执行：

```bash
cd ~/robot_service
source /opt/ros/humble/setup.bash
python3 ros2_nodes/cmd_vel_publisher.py
```

该节点提供命令行交互控制，可使用键盘命令控制机器人前进、后退、转向、停止和退出。

### 8.3 运行 ROS 2 订阅节点

在另一个终端执行：

```bash
cd ~/robot_service
source /opt/ros/humble/setup.bash
python3 ros2_nodes/cmd_vel_subscriber.py
```

订阅节点用于监测 `/cmd_vel` 和 `/robot_position` 等话题，并在终端输出接收到的消息。


## 9. Windows 客户端

客户端程序位于：

```text
client/client.py
```

Windows 端需要安装 Requests：

```bash
python -m pip install requests
```

客户端必须配置为访问 Ubuntu 中运行的 FastAPI 服务。具体基础地址以 `client/client.py` 中的实际配置为准。

例如，如果使用 Ubuntu 虚拟机 IP 地址，可以配置为：

```python
BASE_URL = "http://<Ubuntu虚拟机IP>:8000"
```

其中 `<Ubuntu虚拟机IP>` 需要替换为实际地址。

如果使用 VMware NAT 端口转发，则应填写 Windows 主机侧可访问的地址和转发端口。

运行客户端前，请确保：

1. Webots 仿真正常运行。
2. FastAPI 服务已经启动。
3. Windows 能够访问 FastAPI 服务地址。
4. ROS 2 桥接节点和 Webots 控制器可以正常通信。



## 10. 项目说明与限制

1. 本项目使用 Webots 仿真机器人，不涉及真实硬件。
2. FastAPI 的 `/sensor` 接口使用随机模拟数据，与 Webots 实际距离传感器数据相互独立。
3. Webots 距离传感器数据通过 ROS 2 话题发布。
4. 机器人应用层状态与 Webots 中的实际仿真状态不是同一概念，应根据各自的数据来源进行判断。
5. ROS 2 Humble、Webots 和 Python 运行环境需要正确配置，单纯安装 `requirements.txt` 中的依赖不足以替代这些组件。
6. 实际接口参数、客户端地址和测试结果应以当前代码与运行环境为准。

## 11. 总结

本项目完成了 FastAPI、ROS 2 和 Webots 的综合集成，实现了基于 HTTP 的远程控制、基于 ROS 2 话题的直接控制、四轮机器人仿真运动以及距离传感器数据监测。

项目展示了从上层 Web API 到机器人中间件，再到仿真控制器的完整控制流程，可用于学习 Web 服务、机器人通信和移动机器人仿真控制的集成方法。
