import csv
import math
import os
import random
import time

import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions

WINDOW_NAME = "Quiz REC con Vision"
CAMERA_INDEX = 0
MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
QUESTIONS_PATH = os.path.join(os.path.dirname(__file__), "preguntas.txt")
QUESTIONS_PER_GAME = 3

# Tiempo que el dedo debe quedarse sobre una opcion para seleccionarla
DWELL_TIME = 1.2
START_DWELL_TIME = 1.0
QUESTION_TRANSITION_DELAY = 3.0
RESTART_DWELL_TIME = 1.0

# Resolucion
WIDTH = 1280
HEIGHT = 720
QUESTION_TEXT_X = 55
QUESTION_TEXT_MAX_WIDTH = 900
OPTION_BOX_X = 70
STATUS_TEXT_X = 50
STATUS_TEXT_Y = 118
QUESTION_PANEL_Y = 170
QUESTION_PANEL_H = 120

# Paleta inspirada en la grafica oficial del Festival REC.
REC_BG = (18, 25, 33)
REC_PANEL = (38, 46, 56)
REC_PANEL_ALT = (55, 64, 76)
REC_TEXT = (247, 243, 234)
REC_MUTED = (209, 216, 221)
REC_YELLOW = (241, 208, 86)
REC_CYAN = (93, 200, 210)
REC_CORAL = (234, 111, 101)
REC_TEAL = (78, 169, 157)
REC_SUCCESS = (140, 214, 124)
REC_DARK_TEXT = (27, 31, 38)
REC_POINTER = (255, 248, 239)
REC_WARNING = (255, 190, 120)

WINDOWS_FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
FONT_REGULAR_PATH = None
FONT_BOLD_PATH = None
FONT_CACHE = {}


def resolve_font(*candidates):
    for candidate in candidates:
        font_path = os.path.join(WINDOWS_FONT_DIR, candidate)
        if os.path.exists(font_path):
            return font_path
    raise FileNotFoundError("No se encontro una fuente compatible para dibujar texto.")


FONT_REGULAR_PATH = resolve_font("segoeui.ttf", "arial.ttf")
FONT_BOLD_PATH = resolve_font("segoeuib.ttf", "arialbd.ttf", "segoeui.ttf")


def rgb_to_bgr(color):
    return (color[2], color[1], color[0])


def load_font(size, bold=False):
    key = (size, bold)
    if key not in FONT_CACHE:
        font_path = FONT_BOLD_PATH if bold else FONT_REGULAR_PATH
        FONT_CACHE[key] = ImageFont.truetype(font_path, size=size)
    return FONT_CACHE[key]


def landmark_point(landmarks, idx):
    landmark = landmarks[idx]
    return np.array([landmark.x, landmark.y], dtype=np.float32)


def point_distance(point_a, point_b):
    return float(np.linalg.norm(point_a - point_b))


def normalize_text(text):
    if "Ã" in text or "Â" in text:
        try:
            return text.encode("latin-1").decode("utf-8")
        except UnicodeError:
            return text
    return text


def load_questions(file_path):
    questions = []

    with open(file_path, encoding="utf-8", newline="") as file:
        lines = []
        for line in file:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lines.append(line)

    reader = csv.reader(lines, skipinitialspace=True)
    for line_number, row in enumerate(reader, start=1):
        if len(row) < 5:
            raise ValueError(
                f"La linea {line_number} de {file_path} debe tener pregunta, opciones y respuesta."
            )

        question = normalize_text(row[0].strip())
        options = [normalize_text(item.strip()) for item in row[1:-1]]

        try:
            answer_number = int(row[-1].strip())
        except ValueError as exc:
            raise ValueError(
                f"La linea {line_number} de {file_path} debe terminar con el numero de la respuesta correcta."
            ) from exc

        if len(options) < 2:
            raise ValueError(
                f"La linea {line_number} de {file_path} debe tener al menos dos opciones."
            )

        if not 1 <= answer_number <= len(options):
            raise ValueError(
                f"La linea {line_number} de {file_path} tiene una respuesta correcta fuera de rango."
            )

        questions.append(
            {
                "question": question,
                "options": options,
                "answer": answer_number - 1,
            }
        )

    if not questions:
        raise ValueError(f"No se encontraron preguntas validas en {file_path}.")

    return questions


# =========================
# CONFIGURACION DEL QUIZ
# =========================
QUESTION_BANK = load_questions(QUESTIONS_PATH)

if len(QUESTION_BANK) < QUESTIONS_PER_GAME:
    raise ValueError(
        f"Se necesitan al menos {QUESTIONS_PER_GAME} preguntas en {QUESTIONS_PATH}."
    )

QUESTIONS = random.sample(QUESTION_BANK, QUESTIONS_PER_GAME)

# =========================
# HAND TRACKING
# =========================
mp_draw = vision.drawing_utils
hand_connections = vision.HandLandmarksConnections.HAND_CONNECTIONS

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"No se encontro el modelo de MediaPipe en: {MODEL_PATH}"
    )

hands = vision.HandLandmarker.create_from_options(
    vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.7,
        min_tracking_confidence=0.7,
    )
)


class TextCanvas:
    def __init__(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self._image = Image.fromarray(rgb_frame)
        self._draw = ImageDraw.Draw(self._image)

    def measure(self, text, size=36, bold=False):
        font = load_font(size, bold=bold)
        left, top, right, bottom = self._draw.textbbox((0, 0), text, font=font)
        return right - left, bottom - top

    def wrap_text(self, text, max_width, size=36, bold=False):
        words = text.split()
        lines = []
        current = ""

        for word in words:
            test = f"{current} {word}".strip()
            text_width, _ = self.measure(test, size=size, bold=bold)
            if text_width <= max_width or not current:
                current = test
            else:
                lines.append(current)
                current = word

        if current:
            lines.append(current)

        return lines

    def text(self, text, x, y, size=36, color=REC_TEXT, bold=False, anchor="lt"):
        font = load_font(size, bold=bold)
        self._draw.text((x, y), text, font=font, fill=color, anchor=anchor)

    def polygon(self, points, fill=None, outline=None, width=1):
        self._draw.polygon(points, fill=fill, outline=outline, width=width)

    def multiline(
        self,
        text,
        x,
        y,
        max_width=1000,
        line_height=40,
        size=36,
        color=REC_TEXT,
        bold=False,
    ):
        lines = self.wrap_text(text, max_width=max_width, size=size, bold=bold)
        for index, line in enumerate(lines):
            self.text(line, x, y + index * line_height, size=size, color=color, bold=bold)

    def apply(self, frame):
        frame[:] = cv2.cvtColor(np.array(self._image), cv2.COLOR_RGB2BGR)


def blend_rect(frame, x, y, w, h, fill_color, alpha=0.85, border_color=None, border_thickness=2):
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), rgb_to_bgr(fill_color), -1)
    frame[:] = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    if border_color is not None:
        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            rgb_to_bgr(border_color),
            border_thickness,
        )


def draw_rec_background(frame):
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (WIDTH, HEIGHT), rgb_to_bgr(REC_BG), -1)
    frame[:] = cv2.addWeighted(overlay, 0.72, frame, 0.28, 0)

    accents = frame.copy()
    cv2.circle(accents, (WIDTH - 120, 130), 135, rgb_to_bgr(REC_YELLOW), -1)
    cv2.circle(accents, (WIDTH - 20, 200), 115, rgb_to_bgr(REC_CORAL), -1)
    cv2.circle(accents, (1030, 565), 210, rgb_to_bgr(REC_CYAN), -1)
    cv2.fillConvexPoly(
        accents,
        np.array([[0, 560], [320, 460], [600, HEIGHT], [0, HEIGHT]], dtype=np.int32),
        rgb_to_bgr(REC_TEAL),
    )
    cv2.fillConvexPoly(
        accents,
        np.array([[650, 0], [910, 0], [730, 165]], dtype=np.int32),
        rgb_to_bgr(REC_CORAL),
    )
    frame[:] = cv2.addWeighted(accents, 0.18, frame, 0.82, 0)

    header = frame.copy()
    cv2.rectangle(header, (0, 0), (WIDTH, 92), rgb_to_bgr((9, 14, 20)), -1)
    frame[:] = cv2.addWeighted(header, 0.84, frame, 0.16, 0)

    cv2.line(frame, (38, 93), (WIDTH - 38, 93), rgb_to_bgr(REC_CYAN), 2)
    cv2.line(frame, (WIDTH - 360, 74), (WIDTH - 55, 30), rgb_to_bgr(REC_YELLOW), 5)
    cv2.line(frame, (WIDTH - 415, 48), (WIDTH - 90, 10), rgb_to_bgr(REC_CORAL), 3)


def draw_multiline_text(
    canvas,
    text,
    x,
    y,
    max_width=1000,
    line_height=40,
    size=36,
    color=REC_TEXT,
    bold=False,
):
    canvas.multiline(
        text,
        x,
        y,
        max_width=max_width,
        line_height=line_height,
        size=size,
        color=color,
        bold=bold,
    )


def draw_star_rating(canvas, center_x, center_y, filled_stars, total_stars=3):
    spacing = 78
    start_x = center_x - ((total_stars - 1) * spacing) / 2

    for star_index in range(total_stars):
        star_x = start_x + star_index * spacing
        fill_color = REC_YELLOW if star_index < filled_stars else REC_PANEL_ALT
        outline_color = REC_YELLOW if star_index < filled_stars else REC_MUTED
        points = []
        outer_radius = 26
        inner_radius = 11

        for point_index in range(10):
            angle = math.radians(-90 + point_index * 36)
            radius = outer_radius if point_index % 2 == 0 else inner_radius
            points.append(
                (
                    star_x + math.cos(angle) * radius,
                    center_y + math.sin(angle) * radius,
                )
            )

        canvas.polygon(points, fill=fill_color, outline=outline_color, width=3)


def is_finger_extended(landmarks, tip_idx, pip_idx, mcp_idx):
    wrist = landmark_point(landmarks, 0)
    tip = landmark_point(landmarks, tip_idx)
    pip = landmark_point(landmarks, pip_idx)
    mcp = landmark_point(landmarks, mcp_idx)

    return (
        point_distance(wrist, tip) > point_distance(wrist, pip) * 1.12
        and point_distance(tip, mcp) > point_distance(pip, mcp)
    )


def detect_interaction_gesture(landmarks):
    index_extended = is_finger_extended(landmarks, 8, 6, 5)
    middle_extended = is_finger_extended(landmarks, 12, 10, 9)
    ring_extended = is_finger_extended(landmarks, 16, 14, 13)
    pinky_extended = is_finger_extended(landmarks, 20, 18, 17)

    extended_count = sum(
        [index_extended, middle_extended, ring_extended, pinky_extended]
    )
    open_hand = extended_count >= 3
    index_only = index_extended and not middle_extended and not ring_extended

    if open_hand:
        return True, "Mano abierta"

    if index_only:
        return True, "Indice extendido"

    return False, ""


# =========================
# BOTONES
# =========================
class OptionBox:
    def __init__(self, x, y, w, h, text, idx):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.text = text
        self.idx = idx

    def contains(self, px, py):
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    def draw(self, frame, hovered=False, selected=False):
        if selected:
            fill_color = REC_CORAL
            border_color = REC_YELLOW
        elif hovered:
            fill_color = REC_YELLOW
            border_color = REC_TEXT
        else:
            fill_color = REC_PANEL
            border_color = REC_CYAN

        blend_rect(
            frame,
            self.x,
            self.y,
            self.w,
            self.h,
            fill_color,
            alpha=0.9,
            border_color=border_color,
            border_thickness=3,
        )

        if isinstance(self.idx, int):
            bubble_fill = REC_TEXT if hovered or selected else REC_CYAN
            bubble_border = REC_DARK_TEXT if hovered or selected else REC_TEXT
            bubble_center = (self.x + 45, self.y + self.h // 2)
            cv2.circle(frame, bubble_center, 24, rgb_to_bgr(bubble_fill), -1)
            cv2.circle(frame, bubble_center, 24, rgb_to_bgr(bubble_border), 2)

    def draw_label(self, canvas, hovered=False, selected=False):
        text_color = REC_DARK_TEXT if hovered or selected else REC_TEXT

        if isinstance(self.idx, int):
            option_letter = chr(ord("A") + self.idx)
            canvas.text(
                option_letter,
                self.x + 45,
                self.y + self.h // 2 - 2,
                size=27,
                color=REC_DARK_TEXT,
                bold=True,
                anchor="mm",
            )
            canvas.text(
                self.text,
                self.x + 85,
                self.y + self.h // 2 - 3,
                size=29,
                color=text_color,
                bold=True,
                anchor="lm",
            )
        else:
            canvas.text(
                self.text,
                self.x + self.w // 2,
                self.y + self.h // 2 - 3,
                size=34,
                color=text_color,
                bold=True,
                anchor="mm",
            )


def get_option_boxes(options):
    box_w = 610
    box_h = 82
    start_x = OPTION_BOX_X
    start_y = 305
    gap = 32

    boxes = []
    for i, opt in enumerate(options):
        y = start_y + i * (box_h + gap)
        boxes.append(OptionBox(start_x, y, box_w, box_h, opt, i))
    return boxes


def get_start_button():
    box_w = 420
    box_h = 110
    x = (WIDTH - box_w) // 2
    y = 430
    return OptionBox(x, y, box_w, box_h, "COMENZAR", "start")


def get_restart_button():
    box_w = 420
    box_h = 100
    x = (WIDTH - box_w) // 2
    y = 470
    return OptionBox(x, y, box_w, box_h, "JUGAR OTRA VEZ", "restart")


# =========================
# ESTADO DEL JUEGO
# =========================
question_index = 0
score = 0
game_state = "start"

hovered_option = None
hover_start_time = None
feedback_text = ""
feedback_color = REC_TEXT
feedback_until = 0
selected_option = None
transition_until = 0
transition_action = None

# =========================
# CAMARA
# =========================
cap = cv2.VideoCapture(CAMERA_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

if not cap.isOpened():
    raise RuntimeError("No se pudo abrir la camara.")

cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)


def draw_progress_bar(frame, x, y, w, h, progress):
    progress = max(0.0, min(1.0, progress))
    cv2.rectangle(frame, (x, y), (x + w, y + h), rgb_to_bgr(REC_TEXT), 2)
    fill_w = int(w * progress)
    cv2.rectangle(frame, (x, y), (x + fill_w, y + h), rgb_to_bgr(REC_YELLOW), -1)


def reset_hover():
    global hovered_option, hover_start_time
    hovered_option = None
    hover_start_time = None


def reset_transition():
    global selected_option, transition_until, transition_action
    selected_option = None
    transition_until = 0
    transition_action = None


def set_feedback(text, color, seconds=1.2):
    global feedback_text, feedback_color, feedback_until
    feedback_text = text
    feedback_color = color
    feedback_until = time.time() + seconds


def start_quiz():
    global question_index, score, game_state, feedback_text, feedback_until, QUESTIONS
    QUESTIONS = random.sample(QUESTION_BANK, QUESTIONS_PER_GAME)
    question_index = 0
    score = 0
    game_state = "playing"
    feedback_text = ""
    feedback_until = 0
    reset_hover()
    reset_transition()


def restart_quiz():
    global question_index, score, game_state, feedback_text, feedback_until, QUESTIONS
    QUESTIONS = random.sample(QUESTION_BANK, QUESTIONS_PER_GAME)
    question_index = 0
    score = 0
    game_state = "start"
    reset_hover()
    reset_transition()
    feedback_text = ""
    feedback_until = 0


def begin_question_transition(selected, action):
    global game_state, selected_option, transition_until, transition_action
    game_state = "transition"
    selected_option = selected
    transition_until = time.time() + QUESTION_TRANSITION_DELAY
    transition_action = action
    reset_hover()


def finish_transition():
    global question_index, game_state
    if transition_action == "next_question":
        question_index += 1
        game_state = "playing"
    elif transition_action == "finish":
        game_state = "finished"
    reset_hover()
    reset_transition()


try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        now = time.time()

        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (WIDTH, HEIGHT))

        detection_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=detection_rgb)
        results = hands.detect_for_video(mp_image, int(now * 1000))

        draw_rec_background(frame)
        fingertip = None
        active_gesture_label = ""

        if results.hand_landmarks:
            hand_landmarks = results.hand_landmarks[0]
            mp_draw.draw_landmarks(frame, hand_landmarks, hand_connections)

            gesture_is_valid, active_gesture_label = detect_interaction_gesture(
                hand_landmarks
            )
            if gesture_is_valid:
                lm = hand_landmarks[8]
                px = int(lm.x * WIDTH)
                py = int(lm.y * HEIGHT)
                fingertip = (px, py)

                cv2.circle(frame, fingertip, 15, rgb_to_bgr(REC_POINTER), -1)
                cv2.circle(frame, fingertip, 15, rgb_to_bgr(REC_CORAL), 2)

        render_state = game_state

        if render_state == "start":
            start_button = get_start_button()
            current_hover = None

            blend_rect(frame, 220, 165, 840, 180, REC_PANEL, alpha=0.84, border_color=REC_CYAN, border_thickness=3)

            if fingertip and start_button.contains(*fingertip):
                current_hover = start_button.idx

            if current_hover is not None:
                if hovered_option != current_hover:
                    hovered_option = current_hover
                    hover_start_time = now
            else:
                reset_hover()

            start_button.draw(frame, hovered=hovered_option == start_button.idx)

            if hovered_option == start_button.idx and hover_start_time is not None:
                progress = (now - hover_start_time) / START_DWELL_TIME
                draw_progress_bar(
                    frame,
                    start_button.x,
                    start_button.y + start_button.h + 10,
                    start_button.w,
                    14,
                    progress,
                )
                if (now - hover_start_time) >= START_DWELL_TIME:
                    start_quiz()

        elif render_state == "playing":
            current = QUESTIONS[question_index]
            boxes = get_option_boxes(current["options"])
            current_hover = None

            blend_rect(
                frame,
                40,
                QUESTION_PANEL_Y,
                950,
                QUESTION_PANEL_H,
                REC_PANEL,
                alpha=0.84,
                border_color=REC_CYAN,
                border_thickness=3,
            )

            for box in boxes:
                if fingertip and box.contains(*fingertip):
                    current_hover = box.idx
                    break

            if current_hover is not None:
                if hovered_option != current_hover:
                    hovered_option = current_hover
                    hover_start_time = now
            else:
                reset_hover()

            for box in boxes:
                is_hovered = box.idx == hovered_option
                box.draw(frame, hovered=is_hovered)

                if is_hovered and hover_start_time is not None:
                    progress = (now - hover_start_time) / DWELL_TIME
                    draw_progress_bar(frame, box.x, box.y + box.h + 6, box.w, 12, progress)

            if hovered_option is not None and hover_start_time is not None:
                if (now - hover_start_time) >= DWELL_TIME:
                    selected = hovered_option
                    correct = current["answer"]

                    if selected == correct:
                        score += 1
                        set_feedback("¡Correcto!", REC_SUCCESS, QUESTION_TRANSITION_DELAY)
                    else:
                        correct_text = current["options"][correct]
                        set_feedback(
                            f"Incorrecto. Era: {correct_text}",
                            REC_CORAL,
                            QUESTION_TRANSITION_DELAY,
                        )

                    next_action = "finish" if question_index == len(QUESTIONS) - 1 else "next_question"
                    begin_question_transition(selected, next_action)

            if time.time() < feedback_until:
                blend_rect(frame, 62, 592, 900, 62, REC_PANEL_ALT, alpha=0.9, border_color=feedback_color, border_thickness=2)

        elif render_state == "transition":
            current = QUESTIONS[question_index]
            remaining = max(0.0, transition_until - now)
            selected_text = current["options"][selected_option] if selected_option is not None else ""
            countdown_value = max(1, int(remaining) + 1)

            panel_x = 170
            panel_y = 170
            panel_w = 940
            panel_h = 420

            blend_rect(
                frame,
                panel_x,
                panel_y,
                panel_w,
                panel_h,
                REC_PANEL_ALT,
                alpha=0.92,
                border_color=REC_YELLOW,
                border_thickness=3,
            )

        else:
            restart_button = get_restart_button()
            current_hover = None
            total_questions = len(QUESTIONS)

            blend_rect(frame, 250, 130, 780, 320, REC_PANEL, alpha=0.86, border_color=REC_CYAN, border_thickness=3)

            if fingertip and restart_button.contains(*fingertip):
                current_hover = restart_button.idx

            if current_hover is not None:
                if hovered_option != current_hover:
                    hovered_option = current_hover
                    hover_start_time = now
            else:
                reset_hover()

            restart_button.draw(frame, hovered=hovered_option == restart_button.idx)

            if hovered_option == restart_button.idx and hover_start_time is not None:
                progress = (now - hover_start_time) / RESTART_DWELL_TIME
                draw_progress_bar(
                    frame,
                    restart_button.x,
                    restart_button.y + restart_button.h + 10,
                    restart_button.w,
                    14,
                    progress,
                )
                if (now - hover_start_time) >= RESTART_DWELL_TIME:
                    restart_quiz()

        text_canvas = TextCanvas(frame)
        text_canvas.text("TRIVIA REC", 42, 28, size=42, color=REC_YELLOW, bold=True)
        text_canvas.text(
            "Concepción vibra con música, color y cultura",
            43,
            68,
            size=20,
            color=REC_MUTED,
        )
        if active_gesture_label:
            text_canvas.text(
                f"Gesto activo: {active_gesture_label}",
                WIDTH - 48,
                66,
                size=21,
                color=REC_TEXT,
                anchor="ra",
            )
        else:
            text_canvas.text(
                "Activa con mano abierta o índice extendido",
                WIDTH - 48,
                66,
                size=21,
                color=REC_WARNING,
                anchor="ra",
            )

        if render_state == "start":
            draw_multiline_text(
                text_canvas,
                "Apunta con tu dedo índice para iniciar una partida de 3 preguntas.",
                x=255,
                y=192,
                max_width=770,
                line_height=52,
                size=37,
                color=REC_TEXT,
                bold=True,
            )
            text_canvas.text(
                f"Banco disponible: {len(QUESTION_BANK)} preguntas",
                640,
                315,
                size=25,
                color=REC_MUTED,
                anchor="mm",
            )
            start_button.draw_label(text_canvas, hovered=hovered_option == start_button.idx)
            text_canvas.text(
                "También puedes presionar R para volver al inicio cuando quieras.",
                640,
                642,
                size=23,
                color=REC_MUTED,
                anchor="mm",
            )

        elif render_state == "playing":
            current = QUESTIONS[question_index]
            status_text = f"Pregunta {question_index + 1}/{len(QUESTIONS)}   Puntaje: {score}"
            text_canvas.text(
                status_text,
                STATUS_TEXT_X,
                STATUS_TEXT_Y,
                size=24,
                color=REC_TEXT,
                bold=True,
            )

            draw_multiline_text(
                text_canvas,
                current["question"],
                x=QUESTION_TEXT_X,
                y=QUESTION_PANEL_Y + 22,
                max_width=QUESTION_TEXT_MAX_WIDTH,
                line_height=40,
                size=34,
                color=REC_TEXT,
                bold=True,
            )

            for box in boxes:
                box.draw_label(text_canvas, hovered=box.idx == hovered_option)

            text_canvas.text(
                "Apunta a una alternativa y mantén el dedo sobre la opción para seleccionarla.",
                60,
                680,
                size=23,
                color=REC_MUTED,
            )

            if time.time() < feedback_until:
                text_canvas.text(
                    feedback_text,
                    82,
                    606,
                    size=28,
                    color=feedback_color,
                    bold=True,
                )

        elif render_state == "transition":
            next_label = "Mostrando resultados..." if transition_action == "finish" else "Cargando siguiente pregunta..."

            text_canvas.text(
                "Respuesta registrada",
                640,
                220,
                size=38,
                color=REC_YELLOW,
                bold=True,
                anchor="mm",
            )
            draw_multiline_text(
                text_canvas,
                feedback_text,
                x=245,
                y=285,
                max_width=800,
                line_height=46,
                size=33,
                color=feedback_color,
                bold=True,
            )
            draw_multiline_text(
                text_canvas,
                f"Seleccionaste: {selected_text}",
                x=245,
                y=380,
                max_width=800,
                line_height=38,
                size=28,
                color=REC_TEXT,
            )
            text_canvas.text(
                next_label,
                640,
                472,
                size=25,
                color=REC_MUTED,
                anchor="mm",
            )
            text_canvas.text(
                str(countdown_value),
                640,
                552,
                size=72,
                color=REC_CYAN,
                bold=True,
                anchor="mm",
            )

            if now >= transition_until:
                finish_transition()

        else:
            total_questions = len(QUESTIONS)
            final_msg = f"Tu puntaje: {score} / {total_questions}"
            star_rating = max(1, min(3, score))

            if score == total_questions:
                msg2 = "Modo festivalero nivel experto."
                msg2_color = REC_YELLOW
            elif score >= max(1, total_questions - 1):
                msg2 = "Muy bien, estuviste cerca del puntaje perfecto."
                msg2_color = REC_CYAN
            else:
                msg2 = "Buen intento. Vuelve a jugar y súbele el volumen."
                msg2_color = REC_CORAL

            text_canvas.text(
                "TRIVIA TERMINADA",
                640,
                190,
                size=46,
                color=REC_YELLOW,
                bold=True,
                anchor="mm",
            )
            text_canvas.text(
                final_msg,
                640,
                290,
                size=34,
                color=REC_TEXT,
                bold=True,
                anchor="mm",
            )
            draw_star_rating(text_canvas, 640, 350, star_rating)
            draw_multiline_text(
                text_canvas,
                msg2,
                x=340,
                y=405,
                max_width=610,
                line_height=38,
                size=29,
                color=msg2_color,
                bold=True,
            )
            restart_button.draw_label(text_canvas, hovered=hovered_option == restart_button.idx)
            text_canvas.text(
                "Apunta al botón para volver al inicio o presiona ESC para salir.",
                640,
                635,
                size=24,
                color=REC_MUTED,
                anchor="mm",
            )

        text_canvas.apply(frame)

        cv2.imshow(WINDOW_NAME, frame)
        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break
        if key in (ord("r"), ord("R")):
            restart_quiz()
finally:
    hands.close()
    cap.release()
    cv2.destroyAllWindows()
