# Development of a Computer Vision System for Skateboarding Trick Analysis Using YOLO and Human Pose Estimation

A computer vision system that analyzes skateboarding tricks from video footage using custom YOLO pose estimation. The system detects the skateboard and skater, then extracts metrics such as jump height, air time, board rotation, and skater stance.

## Install Heavy files from cloude

Install `/dataset` `/test` `/predictions` from **Google Drive** and place the in the root directory:

https://drive.google.com/drive/folders/1k1EUrYD4FaNOKjkP7oG5kCNLJXnZX0tu?usp=sharing

## Goal

Analyze skateboarding tricks from video automatically. The videos are recorded with a **static camera** and always contain **one skater and one skateboard**. The long-term goal is full trick classification by board rotation and skater body movement.

## Models

| File                       | Description                                    |
| -------------------------- | ---------------------------------------------- |
| `models/skate-pose-2.0.pt` | Custom skateboard keypoint model (6 keypoints) |
| `models/yolo11m-pose.pt`   | Standard YOLO human pose model                 |
| `models/yolo11m-seg.pt`    | Standard YOLO segmentation model               |

## Skateboard Skeleton

The dataset was annotated in CVAT. Since a skateboard is approximately symmetric, `nose` and `tail` labels were assigned arbitrarily and do not correspond to the physical front or back of the board.

The skateboard orientation is defined by the vector from `tail` to `nose`. The "right" side of the board is the side to the right of this vector.

### Keypoint order

| Index | Name              | Description                 |
| ----- | ----------------- | --------------------------- |
| 1     | nose              | One end of the skateboard   |
| 2     | tail              | Other end of the skateboard |
| 3     | front_left_wheel  | Left wheel near nose        |
| 4     | front_right_wheel | Right wheel near nose       |
| 5     | back_left_wheel   | Left wheel near tail        |
| 6     | back_right_wheel  | Right wheel near tail       |

Each keypoint has a visibility flag: `2` — visible, `1` — occluded, `0` — not labeled.

## Running application localy

Start API:

```
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Start WEB server:

```
cd web
bun run dev
```

## Setup

Python `3.11.9`, CUDA `12.1`.

```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install ultralytics mlflow opencv-python matplotlib
```

Virtual environment is at `.venv`.

## Training

Key parameters used in `train.ipynb`:

```python
model.train(
    data="./dataset/data.yaml",
    epochs=200,
    imgsz=640,
    batch=16,
)
```

MLflow experiment `keypoints-detector` logs metrics to `runs/mlflow/`.

## Analysis

`analysis.ipynb` runs all three models on every frame and extracts structured metrics.

### Per-frame metrics — `plot_metrics()`

| Signal            | Source                                                                     |
| ----------------- | -------------------------------------------------------------------------- |
| Board angle       | PCA of visible keypoints and segmentation mask — two independent estimates |
| Angle consistency | `\|kpts_angle − seg_angle\|` — how well keypoints and segmentation agree   |
| Knee angles       | Left and right knee joint angles from COCO human pose                      |
| CoM offset        | Euclidean distance from human centre-of-mass to board centroid             |

### Jump height — `plot_jump_height()`

Height in cm = `(baseline_board_Y − board_Y) / median_board_len_px × board_length_cm`.

Calibration uses the median nose-to-tail pixel length across ground frames (board horizontal).
Reliable for side-view recordings (`ltr` / `rtl`); unreliable for `toward` / `away` shots.

### Trick detection — `detect_tricks()`

Returns `list[TrickInterval]` with `start_time`, `end_time`, `duration_s`, `peak_height_cm`,
`start_frame`, `end_frame`, `peak_frame`. Detected intervals are shaded on the jump-height plot.

### Usage

```python
analyses, frame_numbers, fps = analyze_video("clip.mp4")

tricks = detect_tricks(analyses, frame_numbers, fps)
for t in tricks:
    print(f"{t.start_time:.2f}s → {t.end_time:.2f}s  peak {t.peak_height_cm:.1f} cm")

plot_jump_height(analyses, frame_numbers, fps)
plot_metrics(analyses, frame_numbers, fps)
```

## Milestones

- [x] Collect data — record skateboarding tricks
- [x] Label data — split videos into frames and annotate the skateboard in CVAT
- [x] Train custom YOLO pose estimation model for the skateboard
- [x] Detect trick start and end frames
- [x] Measure jump height and air time
- [x] Detect direction of travel
- [x] Determine skater stance from direction + regular/goofy parameter
- [x] Compute board yaw and flip
- [x] Compute skater body rotation
- [x] Classify full trick by board and body movement
