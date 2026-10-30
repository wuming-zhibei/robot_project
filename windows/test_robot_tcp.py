
import json
import socket

UBUNTU_IP = "192.168.92.130"
TCP_PORT = 9000


def main():
    print(f"正在连接机器人状态服务：{UBUNTU_IP}:{TCP_PORT}")

    try:
        with socket.create_connection(
            (UBUNTU_IP, TCP_PORT), timeout=5
        ) as sock:
            print("TCP 连接成功，开始接收机器人状态……")

            # 服务端每条 JSON 消息以换行符结尾
            with sock.makefile(
                "r", encoding="utf-8"
            ) as stream:
                while True:
                    line = stream.readline()

                    if not line:
                        print("服务端已关闭连接")
                        break

                    try:
                        data = json.loads(line)
                        print(json.dumps(
                            data,
                            ensure_ascii=False,
                            indent=2
                        ))
                    except json.JSONDecodeError:
                        print("收到无法解析的 JSON：", line)

    except (OSError, TimeoutError) as exc:
        print(f"连接或接收失败：{exc}")


if __name__ == "__main__":
    main()
