from __future__ import annotations

import argparse
import ctypes
import functools
import http.server
import socket
import socketserver
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from manosvc.effects import draw_energy_ball_effect, draw_hand_effects
from manosvc.ui import (
    EffectState,
    draw_effect_buttons,
    draw_logo,
    draw_title,
    handle_mouse_event,
    load_logo,
)

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
)
FACE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
)
MODEL_PATH = ROOT_DIR / "models" / "hand_landmarker.task"
FACE_MODEL_PATH = ROOT_DIR / "models" / "face_landmarker.task"
LOGO_PATH = ROOT_DIR / "assets" / "images" / "uss_logo.png"
WINDOW_NAME = "Hand Tracking Effects"
DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 720
DEFAULT_WEB_PORT = 8000

BaseOptions = mp.tasks.BaseOptions
Vision = mp.tasks.vision


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Servidor web para Manos VC y modo escritorio opcional."
    )
    parser.add_argument(
        "--desktop",
        action="store_true",
        help="Ejecuta la version de escritorio con OpenCV en lugar del servidor web.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host del servidor web. Por defecto: 127.0.0.1.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_WEB_PORT,
        help=f"Puerto inicial para el servidor web. Por defecto: {DEFAULT_WEB_PORT}.",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=0,
        help="Indice de la camara a usar. Por defecto: 0.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="Cantidad maxima de frames a procesar. 0 significa infinito.",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Procesa el video sin abrir la ventana de OpenCV.",
    )
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Abre la ventana en pantalla completa.",
    )
    parser.add_argument(
        "--window-width",
        type=int,
        default=DEFAULT_WINDOW_WIDTH,
        help=f"Ancho de la ventana cuando no se usa pantalla completa. Por defecto: {DEFAULT_WINDOW_WIDTH}.",
    )
    parser.add_argument(
        "--window-height",
        type=int,
        default=DEFAULT_WINDOW_HEIGHT,
        help=f"Alto de la ventana cuando no se usa pantalla completa. Por defecto: {DEFAULT_WINDOW_HEIGHT}.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Valida dependencias y modelo sin abrir la camara.",
    )
    return parser.parse_args()


def find_available_port(host: str, start_port: int) -> int:
    for port in range(start_port, start_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test_socket:
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                test_socket.bind((host, port))
            except OSError:
                continue
            return port

    raise RuntimeError(
        f"No hay puertos libres entre {start_port} y {start_port + 19}."
    )


def run_web_server(host: str, port: int) -> None:
    selected_port = find_available_port(host, port)
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=str(ROOT_DIR),
    )

    with socketserver.TCPServer((host, selected_port), handler) as httpd:
        url = f"http://{host}:{selected_port}/web/index.html"
        print("", flush=True)
        print("=" * 64, flush=True)
        print("Servidor web listo.", flush=True)
        print(f"URL: {url}", flush=True)
        print("Presiona Ctrl+C para detener el servidor.", flush=True)
        print("=" * 64, flush=True)
        print("", flush=True)
        httpd.serve_forever()


def ensure_model(model_path: Path, model_url: str = MODEL_URL) -> Path:
    if model_path.exists():
        return model_path

    model_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Descargando modelo de MediaPipe en {model_path}...")

    try:
        with urllib.request.urlopen(model_url) as response, model_path.open("wb") as file:
            shutil.copyfileobj(response, file)
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "No se pudo descargar el modelo de MediaPipe. "
            "Revisa tu conexion a internet e intenta nuevamente."
        ) from exc

    return model_path


def create_landmarker(model_path: Path, running_mode: Vision.RunningMode):
    options = Vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path.resolve())),
        running_mode=running_mode,
        num_hands=2,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    return Vision.HandLandmarker.create_from_options(options)


def run_self_test(model_path: Path) -> None:
    blank_image = np.zeros((480, 640, 3), dtype=np.uint8)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=blank_image)

    with create_landmarker(model_path, Vision.RunningMode.IMAGE) as landmarker:
        result = landmarker.detect(mp_image)

    print(
        "Self-test correcto: imports, modelo y detector listos. "
        f"Manos detectadas en imagen vacia: {len(result.hand_landmarks)}"
    )


def open_camera(camera_index: int) -> cv2.VideoCapture:
    backends = []
    if hasattr(cv2, "CAP_DSHOW"):
        backends.append(cv2.CAP_DSHOW)
    backends.append(None)

    for backend in backends:
        cap = (
            cv2.VideoCapture(camera_index, backend)
            if backend is not None
            else cv2.VideoCapture(camera_index)
        )
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, DEFAULT_WINDOW_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, DEFAULT_WINDOW_HEIGHT)
            return cap
        cap.release()

    raise RuntimeError(
        f"No se pudo abrir la camara con indice {camera_index}. "
        "Prueba con otro indice o cierra apps que la esten usando."
    )


def draw_selected_effect(frame: np.ndarray, result, effect_time: float, state: EffectState) -> np.ndarray:
    if state.active_index == 1:
        return draw_energy_ball_effect(frame, result, effect_time)
    return draw_hand_effects(frame, result, effect_time)


def center_window(window_name: str, width: int, height: int) -> None:
    try:
        user32 = ctypes.windll.user32
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
    except AttributeError:
        return

    x = max(0, (screen_width - width) // 2)
    y = max(0, (screen_height - height) // 2)
    cv2.resizeWindow(window_name, width, height)
    cv2.moveWindow(window_name, x, y)


def configure_window(window_name: str, fullscreen: bool, width: int, height: int) -> None:
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    if fullscreen:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    else:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
        center_window(window_name, width, height)


def run_camera(
    camera_index: int,
    max_frames: int,
    no_display: bool,
    fullscreen: bool,
    window_width: int,
    window_height: int,
    model_path: Path,
) -> None:
    cap = open_camera(camera_index)
    frame_count = 0
    last_timestamp = 0
    logo = load_logo(LOGO_PATH)
    effect_state = EffectState()

    if not no_display:
        configure_window(WINDOW_NAME, fullscreen, window_width, window_height)
        cv2.setMouseCallback(WINDOW_NAME, handle_mouse_event, effect_state)

    with create_landmarker(model_path, Vision.RunningMode.VIDEO) as landmarker:
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(
                        "La camara se abrio, pero no fue posible leer frames."
                    )

                frame = cv2.flip(frame, 1)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

                timestamp_ms = time.monotonic_ns() // 1_000_000
                if timestamp_ms <= last_timestamp:
                    timestamp_ms = last_timestamp + 1
                last_timestamp = timestamp_ms

                result = landmarker.detect_for_video(mp_image, timestamp_ms)
                output = draw_selected_effect(
                    frame,
                    result,
                    timestamp_ms / 1000.0,
                    effect_state,
                )
                output = draw_title(output)
                output = draw_effect_buttons(output, effect_state)
                output = draw_logo(output, logo)

                if not no_display:
                    cv2.imshow(WINDOW_NAME, output)
                    key = cv2.waitKey(1) & 0xFF
                    if key == 27:
                        break
                    if key in (ord("e"), ord("E")):
                        effect_state.next_effect()

                frame_count += 1
                if max_frames and frame_count >= max_frames:
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()


def main() -> int:
    args = parse_args()

    try:
        if not args.desktop:
            ensure_model(MODEL_PATH)
            ensure_model(FACE_MODEL_PATH, FACE_MODEL_URL)
            run_web_server(args.host, args.port)
            return 0

        model_path = ensure_model(MODEL_PATH)
        if args.self_test:
            run_self_test(model_path)
            return 0

        run_camera(
            args.camera_index,
            args.max_frames,
            args.no_display,
            args.fullscreen,
            args.window_width,
            args.window_height,
            model_path,
        )
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
