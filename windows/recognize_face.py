
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis


# 人脸照片所在目录
BASE_DIR = Path(__file__).resolve().parent
FACE_DIR = BASE_DIR / "faces"

# 人脸相似度阈值
SIMILARITY_THRESHOLD = 0.40


def load_model():
    """加载人脸检测和特征提取模型。"""
    model = FaceAnalysis(
        name="buffalo_l",
        providers=["CPUExecutionProvider"],
    )
    model.prepare(ctx_id=-1, det_size=(640, 640))
    return model


def get_embedding(model, image_path):
    """提取参考照片中的人脸特征。"""
    image = cv2.imread(str(image_path))

    if image is None:
        print(f"无法读取照片：{image_path}")
        return None

    faces = model.get(image)

    if len(faces) != 1:
        print(f"{image_path.name} 应当包含一张人脸")
        return None

    return faces[0].normed_embedding


def load_database(model):
    """读取参考照片，建立人员特征数据库。"""
    database = {}

    for person_id in ("person_a", "person_b"):
        #路径拼接
        person_dir = FACE_DIR / person_id

        if not person_dir.is_dir():
            print(f"缺少身份目录：{person_dir}")
            continue

        embeddings = []

        for path in person_dir.iterdir():
            if path.suffix.lower() not in (
                ".jpg", ".jpeg", ".png", ".bmp", ".webp"
            ):
                continue
            #获取这个人的人脸特征
            embedding = get_embedding(model, path)
            #加到总的里面
            if embedding is not None:
                embeddings.append(embedding)

        if embeddings:
            database[person_id] = embeddings
            print(f"{person_id}：加载了 {len(embeddings)} 张照片")

    return database


def recognize_face(embedding, database):
    """根据人脸特征判断人员身份。"""
    best_person = None
    best_score = -1.0

    for person_id, reference_embeddings in database.items():
        # 计算当前人脸与该身份所有参考照片的相似度，score保存的是当前人脸与这个人的所有参考照片中，最高的相似度。
        score = max(
            #由于 InsightFace 返回的是归一化特征向量，所以点积可以用来衡量两个向量的余弦相似度：相似度越接近 1，说明两个特征越相似。
            float(np.dot(embedding, reference))
            for reference in reference_embeddings
        )

        if score > best_score:
            best_score = score
            best_person = person_id

    if best_person is None or best_score < SIMILARITY_THRESHOLD:
        return "unknown", best_score

    return best_person, best_score
