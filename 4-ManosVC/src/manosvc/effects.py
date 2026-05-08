from __future__ import annotations

import math

import cv2
import mediapipe as mp
import numpy as np

WRIST_INDEX = 0
FINGER_TIPS = [4, 8, 12, 16, 20]
INTER_HAND_LINKS = [4, 8, 12, 16, 20]
PALM_LANDMARKS = [0, 5, 9, 13, 17]

Vision = mp.tasks.vision


def landmark_to_pixel(landmark, width: int, height: int) -> tuple[int, int]:
    x = min(max(int(landmark.x * width), 0), width - 1)
    y = min(max(int(landmark.y * height), 0), height - 1)
    return x, y


def hsv_to_bgr(hue: float, saturation: int = 255, value: int = 255) -> tuple[int, int, int]:
    hsv_color = np.uint8([[[int(hue) % 180, saturation, value]]])
    bgr_color = cv2.cvtColor(hsv_color, cv2.COLOR_HSV2BGR)[0, 0]
    return int(bgr_color[0]), int(bgr_color[1]), int(bgr_color[2])


def rainbow_color(effect_time: float, offset: float, brightness: int = 255) -> tuple[int, int, int]:
    hue = (effect_time * 80 + offset * 180) % 180
    return hsv_to_bgr(hue, value=brightness)


def interpolate_point(
    point_a: tuple[int, int], point_b: tuple[int, int], amount: float
) -> tuple[int, int]:
    x = int(point_a[0] + (point_b[0] - point_a[0]) * amount)
    y = int(point_a[1] + (point_b[1] - point_a[1]) * amount)
    return x, y


def draw_neon_line(
    core_layer: np.ndarray,
    glow_layer: np.ndarray,
    point_a: tuple[int, int],
    point_b: tuple[int, int],
    color: tuple[int, int, int],
    thickness: int,
) -> None:
    cv2.line(glow_layer, point_a, point_b, color, thickness + 10, cv2.LINE_AA)
    cv2.line(glow_layer, point_a, point_b, color, thickness + 5, cv2.LINE_AA)
    cv2.line(core_layer, point_a, point_b, (255, 255, 255), thickness + 2, cv2.LINE_AA)
    cv2.line(core_layer, point_a, point_b, color, thickness, cv2.LINE_AA)


def draw_sparkle(
    sparkle_layer: np.ndarray,
    center: tuple[int, int],
    color: tuple[int, int, int],
    effect_time: float,
    seed: float,
    size: int = 8,
) -> None:
    pulse = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(effect_time * 8 + seed * 11))
    arm = max(3, int(size * pulse))
    diag = max(2, arm // 2)
    x, y = center

    cv2.circle(sparkle_layer, center, arm, color, -1, cv2.LINE_AA)
    cv2.circle(sparkle_layer, center, max(1, arm // 2), (255, 255, 255), -1, cv2.LINE_AA)
    cv2.line(sparkle_layer, (x - arm, y), (x + arm, y), color, 1, cv2.LINE_AA)
    cv2.line(sparkle_layer, (x, y - arm), (x, y + arm), color, 1, cv2.LINE_AA)
    cv2.line(
        sparkle_layer,
        (x - diag, y - diag),
        (x + diag, y + diag),
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    cv2.line(
        sparkle_layer,
        (x - diag, y + diag),
        (x + diag, y - diag),
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )


def draw_rainbow_connection(
    core_layer: np.ndarray,
    glow_layer: np.ndarray,
    sparkle_layer: np.ndarray,
    point_a: tuple[int, int],
    point_b: tuple[int, int],
    effect_time: float,
    seed: float,
    thickness: int = 2,
    segments: int = 9,
    sparkle_every: int = 3,
) -> None:
    delta_x = point_b[0] - point_a[0]
    delta_y = point_b[1] - point_a[1]
    length = max(math.hypot(delta_x, delta_y), 1.0)
    normal_x = -delta_y / length
    normal_y = delta_x / length

    for segment_index in range(segments):
        start_t = segment_index / segments
        end_t = (segment_index + 1) / segments
        start_point = interpolate_point(point_a, point_b, start_t)
        end_point = interpolate_point(point_a, point_b, end_t)
        color = rainbow_color(effect_time, seed + start_t * 0.8)

        draw_neon_line(core_layer, glow_layer, start_point, end_point, color, thickness)

        if segment_index % sparkle_every == 1:
            middle_t = start_t + (end_t - start_t) * 0.5
            middle_point = interpolate_point(point_a, point_b, middle_t)
            offset = math.sin(effect_time * 7 + seed * 9 + segment_index) * 4
            sparkle_center = (
                int(middle_point[0] + normal_x * offset),
                int(middle_point[1] + normal_y * offset),
            )
            draw_sparkle(
                sparkle_layer,
                sparkle_center,
                color,
                effect_time,
                seed + segment_index,
                size=6,
            )


def draw_hand_nodes_without_wrist(image: np.ndarray, points: list[tuple[int, int]]) -> None:
    landmark_styles = Vision.drawing_styles.get_default_hand_landmarks_style()

    for landmark_index, point in enumerate(points):
        if landmark_index == WRIST_INDEX:
            continue

        drawing_spec = landmark_styles[landmark_index]
        border_radius = max(
            drawing_spec.circle_radius + 1,
            int(drawing_spec.circle_radius * 1.2),
        )
        cv2.circle(
            image,
            point,
            border_radius,
            (224, 224, 224),
            drawing_spec.thickness,
            cv2.LINE_AA,
        )
        cv2.circle(
            image,
            point,
            drawing_spec.circle_radius,
            drawing_spec.color,
            drawing_spec.thickness,
            cv2.LINE_AA,
        )


def draw_hand_effects(
    frame: np.ndarray, result: Vision.HandLandmarkerResult, effect_time: float
) -> np.ndarray:
    height, width, _ = frame.shape
    all_points: list[tuple[int, int]] = []
    output = frame.copy()
    glow_layer = np.zeros_like(frame)
    core_layer = np.zeros_like(frame)
    sparkle_layer = np.zeros_like(frame)

    for hand_landmarks in result.hand_landmarks:
        Vision.drawing_utils.draw_landmarks(
            output,
            hand_landmarks,
            Vision.HandLandmarksConnections.HAND_CONNECTIONS,
            None,
            Vision.drawing_styles.get_default_hand_connections_style(),
        )

        points = [landmark_to_pixel(landmark, width, height) for landmark in hand_landmarks]
        all_points.extend(points)
        draw_hand_nodes_without_wrist(output, points)

        for tip_order, tip_index in enumerate(FINGER_TIPS):
            tip_color = rainbow_color(effect_time, tip_order / len(FINGER_TIPS))
            draw_sparkle(
                sparkle_layer,
                points[tip_index],
                tip_color,
                effect_time,
                tip_order + 0.5,
                size=9,
            )
            cv2.circle(core_layer, points[tip_index], 9, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(core_layer, points[tip_index], 6, tip_color, -1, cv2.LINE_AA)

        for i, tip_a in enumerate(FINGER_TIPS):
            for j, tip_b in enumerate(FINGER_TIPS[i + 1 :], start=i + 1):
                seed = (i * len(FINGER_TIPS) + j) / 12
                draw_rainbow_connection(
                    core_layer,
                    glow_layer,
                    sparkle_layer,
                    points[tip_a],
                    points[tip_b],
                    effect_time,
                    seed,
                    thickness=2,
                    segments=9,
                    sparkle_every=3,
                )

    if len(all_points) >= 42:
        for index in INTER_HAND_LINKS:
            draw_rainbow_connection(
                core_layer,
                glow_layer,
                sparkle_layer,
                all_points[index],
                all_points[index + 21],
                effect_time,
                0.7 + index / 21,
                thickness=3,
                segments=7,
                sparkle_every=2,
            )

    output = cv2.addWeighted(output, 1.0, glow_layer, 0.35, 0)
    output = cv2.addWeighted(output, 1.0, core_layer, 1.0, 0)
    output = cv2.addWeighted(output, 1.0, sparkle_layer, 0.65, 0)
    return output


def palm_center(points: list[tuple[int, int]]) -> tuple[int, int]:
    x = int(sum(points[index][0] for index in PALM_LANDMARKS) / len(PALM_LANDMARKS))
    y = int(sum(points[index][1] for index in PALM_LANDMARKS) / len(PALM_LANDMARKS))
    return x, y


def palm_radius(points: list[tuple[int, int]]) -> int:
    wrist = points[0]
    middle_base = points[9]
    distance = math.hypot(middle_base[0] - wrist[0], middle_base[1] - wrist[1])
    return max(22, min(72, int(distance * 0.75)))


def draw_energy_orbit(
    layer: np.ndarray,
    center: tuple[int, int],
    radius: int,
    effect_time: float,
    seed: float,
) -> None:
    orbit_color = rainbow_color(effect_time, seed, brightness=245)
    for dot_index in range(14):
        angle = effect_time * 2.7 + seed * 5 + dot_index * (math.tau / 14)
        wave = math.sin(effect_time * 4.0 + dot_index * 1.7 + seed)
        orbit_x = int(center[0] + math.cos(angle) * radius * (0.95 + wave * 0.08))
        orbit_y = int(center[1] + math.sin(angle) * radius * 0.42)
        dot_radius = 2 + (dot_index % 3)
        cv2.circle(layer, (orbit_x, orbit_y), dot_radius, orbit_color, -1, cv2.LINE_AA)


def draw_anime_energy_spikes(
    layer: np.ndarray,
    center: tuple[int, int],
    radius: int,
    effect_time: float,
    seed: float,
) -> None:
    for spike_index in range(22):
        angle = spike_index * (math.tau / 22) + math.sin(effect_time * 2.0 + seed) * 0.12
        wave = 0.7 + 0.3 * math.sin(effect_time * 11 + spike_index * 1.73 + seed)
        inner = radius * (0.72 + 0.08 * wave)
        outer = radius * (1.6 + 0.55 * wave)
        start = (
            int(center[0] + math.cos(angle) * inner),
            int(center[1] + math.sin(angle) * inner),
        )
        end = (
            int(center[0] + math.cos(angle) * outer),
            int(center[1] + math.sin(angle) * outer),
        )
        color = (255, 235, 95) if spike_index % 2 else (255, 255, 255)
        cv2.line(layer, start, end, color, 2 + spike_index % 3, cv2.LINE_AA)


def draw_anime_lightning(
    layer: np.ndarray,
    center: tuple[int, int],
    radius: int,
    effect_time: float,
    seed: float,
) -> None:
    for bolt_index in range(7):
        angle = effect_time * 1.7 + seed + bolt_index * (math.tau / 7)
        points = []
        for step in range(5):
            distance = radius * (0.55 + step * 0.27)
            jitter = math.sin(effect_time * 15 + bolt_index * 3.1 + step * 2.4) * radius * 0.12
            point_angle = angle + jitter / max(radius, 1)
            points.append(
                (
                    int(center[0] + math.cos(point_angle) * distance),
                    int(center[1] + math.sin(point_angle) * distance),
                )
            )

        color = (255, 245, 125) if bolt_index % 2 else (255, 255, 255)
        for point_a, point_b in zip(points, points[1:]):
            cv2.line(layer, point_a, point_b, color, 2, cv2.LINE_AA)


def draw_anime_energy_beam(
    layer: np.ndarray,
    point_a: tuple[int, int],
    point_b: tuple[int, int],
    effect_time: float,
    seed: float,
) -> None:
    color = (255, 230, 70)
    delta_x = point_b[0] - point_a[0]
    delta_y = point_b[1] - point_a[1]
    length = max(math.hypot(delta_x, delta_y), 1.0)
    normal_x = -delta_y / length
    normal_y = delta_x / length
    previous = point_a

    for segment in range(1, 7):
        amount = segment / 6
        wave = math.sin(effect_time * 14 + seed * 7 + segment * 1.9) * 7
        current = (
            int(point_a[0] + delta_x * amount + normal_x * wave),
            int(point_a[1] + delta_y * amount + normal_y * wave),
        )
        cv2.line(layer, previous, current, color, 3, cv2.LINE_AA)
        cv2.line(layer, previous, current, (255, 255, 255), 1, cv2.LINE_AA)
        previous = current


def draw_energy_ball_effect(
    frame: np.ndarray, result: Vision.HandLandmarkerResult, effect_time: float
) -> np.ndarray:
    height, width, _ = frame.shape
    output = frame.copy()
    glow_layer = np.zeros_like(frame)
    core_layer = np.zeros_like(frame)
    sparkle_layer = np.zeros_like(frame)

    for hand_index, hand_landmarks in enumerate(result.hand_landmarks):
        points = [landmark_to_pixel(landmark, width, height) for landmark in hand_landmarks]

        center = palm_center(points)
        radius = palm_radius(points)
        pulse = 0.9 + 0.14 * math.sin(effect_time * 7.5 + hand_index)
        color_outer = (255, 225, 40)
        color_mid = (255, 180, 35)
        color_inner = (255, 245, 115)

        draw_anime_energy_spikes(glow_layer, center, radius, effect_time, hand_index * 0.6)
        cv2.circle(glow_layer, center, int(radius * 2.35 * pulse), color_outer, -1, cv2.LINE_AA)
        cv2.circle(glow_layer, center, int(radius * 1.75), color_mid, -1, cv2.LINE_AA)
        cv2.circle(core_layer, center, int(radius * 1.02 * pulse), color_inner, -1, cv2.LINE_AA)
        cv2.circle(core_layer, center, int(radius * 0.72), (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(core_layer, center, max(5, int(radius * 0.28)), (245, 255, 255), -1, cv2.LINE_AA)

        cv2.ellipse(sparkle_layer, center, (int(radius * 1.45), int(radius * 0.55)), 0, 0, 360, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.ellipse(sparkle_layer, center, (int(radius * 1.55), int(radius * 0.45)), 55, 0, 360, color_outer, 2, cv2.LINE_AA)
        cv2.ellipse(sparkle_layer, center, (int(radius * 1.65), int(radius * 0.5)), -55, 0, 360, color_outer, 2, cv2.LINE_AA)

        draw_anime_lightning(sparkle_layer, center, radius, effect_time, hand_index * 0.71)

        for tip_order, tip_index in enumerate(FINGER_TIPS):
            seed = hand_index + tip_order * 0.23
            draw_anime_energy_beam(sparkle_layer, points[tip_index], center, effect_time, seed)

    output = cv2.addWeighted(output, 1.0, glow_layer, 0.42, 0)
    output = cv2.addWeighted(output, 1.0, core_layer, 0.98, 0)
    output = cv2.addWeighted(output, 1.0, sparkle_layer, 0.82, 0)
    return output
