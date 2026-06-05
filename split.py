import os
import random
import shutil

BASE_DIR = "."
IMAGES_DIR = os.path.join(BASE_DIR, "images")
LABELS_DIR = os.path.join(BASE_DIR, "labels")

VAL_RATIO = 0.2  # 20% val, 80% train

for split in ["train", "val"]:
    os.makedirs(os.path.join(IMAGES_DIR, split), exist_ok=True)
    os.makedirs(os.path.join(LABELS_DIR, split), exist_ok=True)

image_files = [
    f for f in os.listdir(IMAGES_DIR)
    if os.path.isfile(os.path.join(IMAGES_DIR, f))
    and f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
]

random.shuffle(image_files)

val_count = int(len(image_files) * VAL_RATIO)

val_images = image_files[:val_count]
train_images = image_files[val_count:]


def move_files(image_list, split):
    for img_name in image_list:
        img_src = os.path.join(IMAGES_DIR, img_name)
        img_dst = os.path.join(IMAGES_DIR, split, img_name)

        shutil.move(img_src, img_dst)

        label_name = os.path.splitext(img_name)[0] + ".txt"
        label_src = os.path.join(LABELS_DIR, label_name)

        if os.path.exists(label_src):
            label_dst = os.path.join(LABELS_DIR, split, label_name)
            shutil.move(label_src, label_dst)
        else:
            print(f"[WARNING] No label for: {img_name}")


move_files(train_images, "train")
move_files(val_images, "val")

print("✅ Dataset split completed.")
print(f"Train images: {len(train_images)}")
print(f"Val images: {len(val_images)}")