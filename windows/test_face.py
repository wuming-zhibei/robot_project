
import cv2
from insightface.app import FaceAnalysis


def main():
    # 1. 加载已经安装的人脸模型
    app = FaceAnalysis(
        name="buffalo_l",
        providers=["CPUExecutionProvider"],
    )
    app.prepare(ctx_id=-1, det_size=(640, 640))

    # 2. 打开摄像头
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("错误：无法打开摄像头")
        return

    print("摄像头已启动，按 q 键退出")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("错误：无法读取摄像头画面")
                break

            # 3. 检测人脸并提取特征
            faces = app.get(frame)

            # 4. 绘制检测框并输出特征维度
            for face in faces:
                x1, y1, x2, y2 = map(int, face.bbox)

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2,
                )

                # normed_embedding 是归一化的人脸特征向量
                embedding = face.normed_embedding

                cv2.putText(
                    frame,
                    f"Face dim: {len(embedding)}",
                    (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )

            cv2.putText(
                frame,
                f"Faces: {len(faces)}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2,
            )

            cv2.imshow("Face Detection Test", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
