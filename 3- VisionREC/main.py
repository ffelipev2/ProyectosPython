import csv
import os
import random
import time

import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions

WINDOW_NAME = "Quiz REC con Vision"
CAMERA_INDEX = 0
MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
QUESTIONS_PATH = os.path.join(os.path.dirname(__file__), "preguntas.txt")
QUESTIONS_PER_GAME = 5

# Tiempo que el dedo debe quedarse sobre una opcion para seleccionarla
DWELL_TIME = 1.2
START_DWELL_TIME = 1.0
QUESTION_TRANSITION_DELAY = 3.0
RESTART_DWELL_TIME = 1.0

# Resolucion
WIDTH = 1280
HEIGHT = 720
QUESTION_TEXT_X = 55
QUESTION_TEXT_MAX_WIDTH = 860
OPTION_BOX_X = 70
STATUS_TEXT_X = 30


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

        question = row[0].strip()
        options = [item.strip() for item in row[1:-1]]

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
            color = (0, 200, 0)
        elif hovered:
            color = (0, 220, 255)
        else:
            color = (255, 180, 0)

        cv2.rectangle(frame, (self.x, self.y), (self.x + self.w, self.y + self.h), color, -1)
        cv2.rectangle(frame, (self.x, self.y), (self.x + self.w, self.y + self.h), (255, 255, 255), 3)

        text_scale = 0.9
        text_thickness = 2
        text_size = cv2.getTextSize(self.text, cv2.FONT_HERSHEY_SIMPLEX, text_scale, text_thickness)[0]

        if isinstance(self.idx, int):
            option_letter = chr(ord("A") + self.idx)
            cv2.circle(frame, (self.x + 45, self.y + self.h // 2), 24, (255, 255, 255), -1)
            cv2.putText(
                frame,
                option_letter,
                (self.x + 34, self.y + self.h // 2 + 10),
                cv2.FONT_HERSHEY_DUPLEX,
                0.95,
                (0, 0, 0),
                2,
                cv2.LINE_AA,
            )
            text_x = self.x + 85
        else:
            text_x = self.x + (self.w - text_size[0]) // 2

        text_y = self.y + (self.h + text_size[1]) // 2

        cv2.putText(
            frame,
            self.text,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            text_scale,
            (0, 0, 0),
            text_thickness,
            cv2.LINE_AA,
        )


def draw_multiline_text(
    frame,
    text,
    x,
    y,
    max_width=1000,
    line_height=40,
    font=cv2.FONT_HERSHEY_SIMPLEX,
    scale=1.0,
    color=(255, 255, 255),
    thickness=2,
):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = current + " " + word if current else word
        size = cv2.getTextSize(test, font, scale, thickness)[0]
        if size[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    for i, line in enumerate(lines):
        yy = y + i * line_height
        cv2.putText(frame, line, (x, yy), font, scale, color, thickness, cv2.LINE_AA)


def get_option_boxes(options):
    box_w = 600
    box_h = 82
    start_x = OPTION_BOX_X
    start_y = 240
    gap = 40

    boxes = []
    for i, opt in enumerate(options):
        y = start_y + i * (box_h + gap)
        boxes.append(OptionBox(start_x, y, box_w, box_h, opt, i))
    return boxes


def get_start_button():
    box_w = 420
    box_h = 110
    x = (WIDTH - box_w) // 2
    y = 420
    return OptionBox(x, y, box_w, box_h, "COMENZAR", "start")


def get_restart_button():
    box_w = 420
    box_h = 100
    x = (WIDTH - box_w) // 2
    y = 455
    return OptionBox(x, y, box_w, box_h, "REINICIAR", "restart")


# =========================
# ESTADO DEL JUEGO
# =========================
question_index = 0
score = 0
game_state = "start"

hovered_option = None
hover_start_time = None
feedback_text = ""
feedback_color = (255, 255, 255)
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
    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)
    fill_w = int(w * progress)
    cv2.rectangle(frame, (x, y), (x + fill_w, y + h), (0, 255, 255), -1)


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

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (WIDTH, HEIGHT), (20, 20, 20), -1)
        frame = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)

        fingertip = None

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        results = hands.detect_for_video(mp_image, int(time.time() * 1000))

        if results.hand_landmarks:
            hand_landmarks = results.hand_landmarks[0]
            mp_draw.draw_landmarks(frame, hand_landmarks, hand_connections)

            lm = hand_landmarks[8]
            px = int(lm.x * WIDTH)
            py = int(lm.y * HEIGHT)
            fingertip = (px, py)

            cv2.circle(frame, fingertip, 12, (0, 0, 255), -1)

        cv2.putText(frame, "TRIVIA REC", (40, 60), cv2.FONT_HERSHEY_DUPLEX, 1.4, (0, 255, 255), 3, cv2.LINE_AA)

        if game_state == "start":
            start_button = get_start_button()
            current_hover = None

            draw_multiline_text(
                frame,
                "Apunta con tu dedo indice para iniciar la trivia",
                x=250,
                y=220,
                max_width=780,
                line_height=55,
                scale=1.2,
                thickness=3,
            )
            cv2.putText(
                frame,
                f"Banco cargado: {len(QUESTIONS)} preguntas",
                (410, 310),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.95,
                (220, 220, 220),
                2,
                cv2.LINE_AA,
            )

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

            cv2.putText(
                frame,
                "Tambien puedes presionar R para volver a esta pantalla cuando quieras",
                (220, 640),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (220, 220, 220),
                2,
                cv2.LINE_AA,
            )

        elif game_state == "playing":
            current = QUESTIONS[question_index]

            status_text = f"Pregunta {question_index + 1}/{len(QUESTIONS)}   Puntaje: {score}"
            cv2.putText(frame, status_text, (STATUS_TEXT_X, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)

            draw_multiline_text(
                frame,
                current["question"],
                x=QUESTION_TEXT_X,
                y=170,
                max_width=QUESTION_TEXT_MAX_WIDTH,
                line_height=45,
                scale=1.1,
                thickness=3,
            )

            boxes = get_option_boxes(current["options"])

            current_hover = None
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
                    draw_progress_bar(frame, box.x, box.y + box.h + 5, box.w, 12, progress)

            if hovered_option is not None and hover_start_time is not None:
                if (now - hover_start_time) >= DWELL_TIME:
                    selected = hovered_option
                    correct = current["answer"]

                    if selected == correct:
                        score += 1
                        set_feedback("Correcto!", (0, 255, 0), QUESTION_TRANSITION_DELAY)
                    else:
                        correct_text = current["options"][correct]
                        set_feedback(
                            f"Incorrecto. Era: {correct_text}",
                            (0, 100, 255),
                            QUESTION_TRANSITION_DELAY,
                        )

                    next_action = "finish" if question_index == len(QUESTIONS) - 1 else "next_question"
                    begin_question_transition(selected, next_action)

            cv2.putText(
                frame,
                "Apunta con tu dedo indice a una alternativa y mantenlo sobre la opcion",
                (60, 680),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (220, 220, 220),
                2,
                cv2.LINE_AA,
            )

        elif game_state == "transition":
            current = QUESTIONS[question_index]
            remaining = max(0.0, transition_until - now)
            selected_text = current["options"][selected_option] if selected_option is not None else ""
            countdown_value = max(1, int(remaining) + 1)

            panel_x = 170
            panel_y = 170
            panel_w = 940
            panel_h = 420

            cv2.rectangle(frame, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (30, 30, 30), -1)
            cv2.rectangle(frame, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (255, 255, 255), 3)

            cv2.putText(
                frame,
                "Respuesta registrada",
                (430, 240),
                cv2.FONT_HERSHEY_DUPLEX,
                1.2,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )
            draw_multiline_text(
                frame,
                feedback_text,
                x=250,
                y=315,
                max_width=780,
                line_height=50,
                scale=1.0,
                color=feedback_color,
                thickness=3,
            )
            draw_multiline_text(
                frame,
                f"Seleccionaste: {selected_text}",
                x=250,
                y=395,
                max_width=780,
                line_height=40,
                scale=0.9,
                color=(235, 235, 235),
                thickness=2,
            )

            next_label = "Mostrando resultados..." if transition_action == "finish" else "Cargando siguiente pregunta..."
            cv2.putText(
                frame,
                next_label,
                (390, 470),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (220, 220, 220),
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                frame,
                str(countdown_value),
                (610, 565),
                cv2.FONT_HERSHEY_DUPLEX,
                2.8,
                (0, 255, 255),
                4,
                cv2.LINE_AA,
            )

            if now >= transition_until:
                finish_transition()

        else:
            restart_button = get_restart_button()
            current_hover = None

            cv2.putText(frame, "TRIVIA TERMINADA", (360, 180), cv2.FONT_HERSHEY_DUPLEX, 1.6, (0, 255, 255), 3, cv2.LINE_AA)

            final_msg = f"Tu puntaje: {score} / {len(QUESTIONS)}"
            cv2.putText(frame, final_msg, (430, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3, cv2.LINE_AA)

            if score == len(QUESTIONS):
                msg2 = "Modo festivalero nivel experto!"
            elif score >= 2:
                msg2 = "Muy bien!"
            else:
                msg2 = "Buen intento. Vuelve a jugar!"

            cv2.putText(frame, msg2, (350, 390), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 0), 3, cv2.LINE_AA)

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

            cv2.putText(
                frame,
                "Apunta al boton para volver al inicio o presiona ESC para salir",
                (235, 610),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (220, 220, 220),
                2,
                cv2.LINE_AA,
            )

        if game_state == "playing" and time.time() < feedback_until:
            cv2.putText(frame, feedback_text, (80, 630), cv2.FONT_HERSHEY_SIMPLEX, 1.0, feedback_color, 3, cv2.LINE_AA)

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
