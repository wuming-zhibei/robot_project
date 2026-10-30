
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis


BASE_DIR = Path(__file__).resolve().parent
FACE_DIR = BASE_DIR / "faces"

# 初始测试阈值，不代表已经验证可靠
SIMILARITY_THRESHOLD = 0.40


def load_model():
    """加载人脸检测与特征提取模型。"""
    model = FaceAnalysis(
        name="buffalo_l",
        providers=["CPUExecutionProvider"],
    )
    model.prepare(ctx_id=-1, det_size=(640, 640))
    return model


def get_embedding(model, image_path):
    """从参考照片提取人脸特征。"""
    image = cv2.imread(str(image_path))

    if image is None:
        print(f"无法读取照片：{image_path}")
        return None

    faces = model.get(image)

    if len(faces) != 1:
        print(
            f"{image_path.name} 应当包含一张清晰人脸，"
            f"实际检测到 {len(faces)} 张"
        )
        return None

    return faces[0].normed_embedding


def load_database(model):
    """读取 person_a 和 person_b 的参考照片。"""
    database = {}

    for person_id in ("person_a", "person_b"):
        person_dir = FACE_DIR / person_id

        if not person_dir.is_dir():
            print(f"缺少身份目录：{person_dir}")
            continue

        embeddings = []

        for path in person_dir.iterdir():
            if path.suffix.lower() not in {
                ".jpg", ".jpeg", ".png", ".bmp", ".webp"
            }:
                continue

            embedding = get_embedding(model, path)

            if embedding is not None:
                embeddings.append(embedding)

        if embeddings:
            database[person_id] = embeddings
            print(f"{person_id}：已加载 {len(embeddings)} 张参考照片")
        else:
            print(f"{person_id}：没有可用的参考照片")

    return database


def recognize_face(embedding, database):
    """比较当前人脸与所有身份参考特征。"""
    best_person = None
    best_score = -1.0

    for person_id, reference_embeddings in database.items():
        # 对同一身份的多张照片分别比较，取最高相似度
        score = max(
            float(np.dot(embedding, reference))
            for reference in reference_embeddings
        )

        if score > best_score:
            best_score = score
            best_person = person_id

    if best_person is None or best_score < SIMILARITY_THRESHOLD:
        return "unknown", best_score

    return best_person, best_score


def main():
    model = load_model()
    database = load_database(model)

    if not database:
        print("错误：没有加载到任何有效参考照片。")
        return

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("错误：无法打开摄像头。")
        return

    print("身份识别已启动，按 q 退出。")

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                print("无法读取摄像头画面。")
                break

            faces = model.get(frame)

            for face in faces:
                x1, y1, x2, y2 = map(int, face.bbox)

                person_id, score = recognize_face(
                    face.normed_embedding,
                    database,
                )

                if person_id == "person_a":
                    robot_id = "Robot A"
                elif person_id == "person_b":
                    robot_id = "Robot B"
                else:
                    robot_id = "Unknown"

                label = f"{robot_id} ({score:.2f})"

                color = (
                    (0, 255, 0)
                    if person_id != "unknown"
                    else (0, 0, 255)
                )

                cv2.rectangle(
                    frame, (x1, y1), (x2, y2), color, 2
                )

                cv2.putText(
                    frame,
                    label,
                    (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    color,
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

            cv2.imshow("Face Recognition", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
