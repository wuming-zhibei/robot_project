import requests

BASE_URL = "http://127.0.0.1:8000"

def get_status():
    try:
        response = requests.get(BASE_URL + "/status", timeout=5)
        response.raise_for_status()

        print("\n设备状态:")
        print(response.json())

    except requests.exceptions.RequestException:
        print("\n 无法连接机器人服务，请检查 FastAPI 是否启动")
def get_sensor():
    try:
        response = requests.get(BASE_URL + "/sensor", timeout=5)
        response.raise_for_status()

        print("\n传感器数据:")
        print(response.json())

    except requests.exceptions.RequestException:
        print("\n 无法连接机器人服务，请检查 FastAPI 是否启动")
def move_robot():
    direction = input(
        "请输入方向(forward/backward/left/right):"
    )

    if direction not in ["forward", "backward", "left", "right"]:
        print("无效的方向")
        return

    try:
        speed = int(input("请输入速度(0-100):"))
    except ValueError:
        print(" 速度必须是整数")
        return

    if speed < 0 or speed > 100:
        print(" 速度必须在 0-100 之间")
        return

    data = {
        "direction": direction,
        "speed": speed
    }

    try:
        response = requests.post(
            BASE_URL + "/move",
            json=data,
            timeout=5
        )
        response.raise_for_status()

        print("\n服务器响应:")
        print(response.json())

    except requests.exceptions.RequestException:
        print("\n 无法连接机器人服务，请检查 FastAPI 是否启动")
def stop_robot():
    try:
        response = requests.post(
            BASE_URL + "/stop",
            timeout=5
        )
        response.raise_for_status()

        print("\n服务器响应:")
        print(response.json())

    except requests.exceptions.RequestException:
        print("\n无法连接机器人服务,请检查 FastAPI 是否启动")
def run_task():
    print("\n预设任务:")
    print("1. forward")
    print("2. square")

    choice = input("请选择任务：")

    if choice == "1":
        task_name = "forward"

    elif choice == "2":
        task_name = "square"

    else:
        print("❌ 无效任务")
        return

    data = {
        "task": task_name
    }

    try:
        response = requests.post(
            BASE_URL + "/task",
            json=data,
            timeout=5
        )
        response.raise_for_status()

        print("\n服务器响应:")
        print(response.json())

    except requests.exceptions.RequestException:
        print("\n无法连接机器人服务,请检查 FastAPI 是否启动")
def main():
    while True:
        print("\n==============================")
        print("      虚拟机器人客户端")
        print("==============================")
        print("1. 查询设备状态")
        print("2. 查询传感器")
        print("3. 控制机器人移动")
        print("4. 停止机器人")
        print("5. 执行预设任务")
        print("0. 退出")

        choice = input("请选择：")

        if choice == "1":
            get_status()

        elif choice == "2":
            get_sensor()

        elif choice == "3":
            move_robot()

        elif choice == "4":
            stop_robot()

        elif choice == "5":
            run_task()

        elif choice == "0":
            print("客户端退出")
            break

        else:
            print("无效选项，请重新输入")
if __name__=="__main__":
    main()
