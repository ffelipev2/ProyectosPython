from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

APP_TITLE = "MANOS VC"


@dataclass
class EffectState:
    names: tuple[str, ...] = ("Manos", "Energia")
    active_index: int = 0
    button_rects: tuple[tuple[int, int, int, int], ...] = ()

    @property
    def active_name(self) -> str:
        return self.names[self.active_index]

    def next_effect(self) -> None:
        self.active_index = (self.active_index + 1) % len(self.names)

    def handle_click(self, x: int, y: int) -> None:
        for index, rect in enumerate(self.button_rects):
            left, top, right, bottom = rect
            if left <= x <= right and top <= y <= bottom:
                self.active_index = index
                return


def load_logo(path: Path, target_width: int = 180) -> np.ndarray | None:
    if not path.exists():
        return None

    logo = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if logo is None:
        return None

    height, width = logo.shape[:2]
    if width <= 0 or height <= 0:
        return None

    scale = target_width / width
    target_size = (target_width, max(1, int(height * scale)))
    return cv2.resize(logo, target_size, interpolation=cv2.INTER_AREA)


def overlay_image(
    frame: np.ndarray,
    image: np.ndarray,
    top_left: tuple[int, int],
    opacity: float = 1.0,
) -> np.ndarray:
    x, y = top_left
    image_height, image_width = image.shape[:2]
    frame_height, frame_width = frame.shape[:2]

    if x >= frame_width or y >= frame_height:
        return frame

    visible_width = min(image_width, frame_width - x)
    visible_height = min(image_height, frame_height - y)
    if visible_width <= 0 or visible_height <= 0:
        return frame

    image_crop = image[:visible_height, :visible_width]
    target = frame[y : y + visible_height, x : x + visible_width]

    if image_crop.shape[2] == 4:
        alpha = (image_crop[:, :, 3] / 255.0) * opacity
        alpha = alpha[:, :, np.newaxis]
        frame[y : y + visible_height, x : x + visible_width] = (
            alpha * image_crop[:, :, :3] + (1.0 - alpha) * target
        ).astype(np.uint8)
    else:
        frame[y : y + visible_height, x : x + visible_width] = cv2.addWeighted(
            image_crop[:, :, :3],
            opacity,
            target,
            1.0 - opacity,
            0,
        )

    return frame


def draw_logo(frame: np.ndarray, logo: np.ndarray | None) -> np.ndarray:
    if logo is None:
        return frame

    margin = 24
    logo_height, logo_width = logo.shape[:2]
    x = max(margin, frame.shape[1] - logo_width - margin)
    blurred_logo = cv2.GaussianBlur(logo, (0, 0), sigmaX=3.5, sigmaY=3.5)
    return overlay_image(frame, blurred_logo, (x, margin), opacity=0.28)


def _button_rects(frame: np.ndarray) -> tuple[tuple[int, int, int, int], ...]:
    button_size = 86
    margin = 30
    top = max(92, (frame.shape[0] - button_size) // 2)
    return (
        (margin, top, margin + button_size, top + button_size),
        (
            frame.shape[1] - margin - button_size,
            top,
            frame.shape[1] - margin,
            top + button_size,
        ),
    )


def _draw_hand_icon(frame: np.ndarray, rect: tuple[int, int, int, int], color: tuple[int, int, int]) -> None:
    left, top, right, bottom = rect
    center_x = (left + right) // 2
    palm_y = top + 54
    wrist_y = bottom - 14

    cv2.line(frame, (center_x, palm_y), (center_x, wrist_y), color, 4, cv2.LINE_AA)
    cv2.circle(frame, (center_x, palm_y), 10, color, -1, cv2.LINE_AA)
    for offset, length in [(-20, 18), (-10, 25), (0, 29), (10, 24), (20, 17)]:
        tip = (center_x + offset, palm_y - length)
        base = (center_x + offset // 2, palm_y - 5)
        cv2.line(frame, base, tip, color, 5, cv2.LINE_AA)
        cv2.circle(frame, tip, 4, color, -1, cv2.LINE_AA)


def _draw_energy_icon(frame: np.ndarray, rect: tuple[int, int, int, int], color: tuple[int, int, int]) -> None:
    left, top, right, bottom = rect
    center = ((left + right) // 2, (top + bottom) // 2)

    cv2.circle(frame, center, 25, color, 2, cv2.LINE_AA)
    cv2.circle(frame, center, 15, color, -1, cv2.LINE_AA)
    cv2.circle(frame, center, 5, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.ellipse(frame, center, (32, 12), 0, 0, 360, color, 2, cv2.LINE_AA)
    cv2.ellipse(frame, center, (32, 12), 60, 0, 360, color, 1, cv2.LINE_AA)


def draw_title(frame: np.ndarray) -> np.ndarray:
    overlay = frame.copy()
    height, width = frame.shape[:2]
    cv2.rectangle(overlay, (0, 0), (width, 78), (8, 10, 16), -1, cv2.LINE_AA)
    frame = cv2.addWeighted(overlay, 0.58, frame, 0.42, 0)

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.08
    thickness = 2
    text_size, _ = cv2.getTextSize(APP_TITLE, font, font_scale, thickness)
    x = max(24, (width - text_size[0]) // 2)
    y = 48
    cv2.putText(frame, APP_TITLE, (x + 2, y + 2), font, font_scale, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(frame, APP_TITLE, (x, y), font, font_scale, (245, 248, 255), thickness, cv2.LINE_AA)
    return frame


def draw_effect_buttons(frame: np.ndarray, state: EffectState) -> np.ndarray:
    state.button_rects = _button_rects(frame)
    overlay = frame.copy()

    for index, rect in enumerate(state.button_rects):
        left, top, right, bottom = rect
        is_active = index == state.active_index
        fill = (18, 23, 31) if is_active else (10, 12, 18)
        border = (105, 245, 255) if is_active else (105, 115, 130)
        icon = (255, 255, 255) if is_active else (175, 185, 195)

        cv2.rectangle(overlay, (left, top), (right, bottom), fill, -1, cv2.LINE_AA)
        cv2.rectangle(overlay, (left, top), (right, bottom), border, 3 if is_active else 2, cv2.LINE_AA)
        if index == 0:
            _draw_hand_icon(overlay, rect, icon)
        else:
            _draw_energy_icon(overlay, rect, icon)

    frame = cv2.addWeighted(overlay, 0.78, frame, 0.22, 0)
    return frame


def handle_mouse_event(event: int, x: int, y: int, _flags: int, state: EffectState) -> None:
    if event == cv2.EVENT_LBUTTONDOWN:
        state.handle_click(x, y)
