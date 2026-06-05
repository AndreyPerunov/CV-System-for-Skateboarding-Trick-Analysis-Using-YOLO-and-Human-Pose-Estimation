COCO_KEYPOINT_NAMES = [
    "nose", "left eye", "right eye", "left ear", "right ear",
    "left shoulder", "right shoulder",
    "left elbow", "right elbow",
    "left wrist", "right wrist",
    "left hip", "right hip",
    "left knee", "right knee",
    "left ankle", "right ankle",
]

COCO_SKELETON = [
    (5, 7), (7, 9),
    (6, 8), (8, 10),
    (5, 6),
    (5, 11), (6, 12),
    (11, 12),
    (11, 13), (13, 15),
    (12, 14), (14, 16),
]

SKATE_KEYPOINT_NAMES = [
    "nose",
    "tail",
    "front_left_wheel",
    "front_right_wheel",
    "back_left_wheel",
    "back_right_wheel",
]

SKATE_KEYPOINT_COLORS = {
    "nose":              (255,   0,   0),
    "tail":              (255,   0, 255),
    "front_left_wheel":  (  0, 100,   0),
    "front_right_wheel": (  0,   0, 139),
    "back_left_wheel":   (144, 238, 144),
    "back_right_wheel":  (173, 216, 230),
}

SKATE_CONNECTIONS = [(0, 1), (2, 3), (4, 5)]

# Keypoint remapping when nose/tail are swapped.
SKATE_KP_SWAP = [1, 0, 5, 4, 3, 2]
