
import argparse
import json
import socket
import time


def run_client(host: str, port: int):
    """连接 TCP 服务端，接收状态并在断线后自动重连。"""

    while True:
        try:
            print(f"[Client] Connecting to {host}:{port} ...")

            with socket.create_connection(
                (host, port),
                timeout=5.0,
            ) as sock:
                print("[Client] Connected")

                # 将 TCP 字节流包装成按行读取的文本流
                with sock.makefile(
                    "r",
                    encoding="utf-8",
                ) as reader:

                    for line in reader:
                        if not line.strip():
                            continue

                        try:
                            message = json.loads(line)
                        except json.JSONDecodeError as exc:
                            print(f"[Client] Invalid JSON: {exc}")
                            continue

                        print(
                            json.dumps(
                                message,
                                ensure_ascii=False,
                                indent=2,
                            )
                        )

                print("[Client] Connection closed")

        except KeyboardInterrupt:
            print("\n[Client] Exiting")
            break

        except OSError as exc:
            print(f"[Client] Connection error: {exc}")

        print("[Client] Retrying in 2 seconds ...")
        time.sleep(2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Robot TCP status client simulator"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)

    args = parser.parse_args()
    run_client(args.host, args.port)
