# main.py

import cv2
import numpy as np
import  time
import time
from funciones import *

# Cargar el diccionario ArUco
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
parameters = cv2.aruco.DetectorParameters()

# Inicializar la cámara
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# Inicializar variables
board = inicializar_tablero()
turno_maquina = False
tablero_determinado = False
x_min, y_min, x_max, y_max = 0, 0, 0, 0
juego_terminado = False
tiempo_fin = None

while True:
    ret, frame = cap.read()
    if not ret:
        print("No se puede acceder a la cámara.")
        break

    # Convertir a escala de grises y detectar marcadores
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

    if ids is not None:
        cv2.aruco.drawDetectedMarkers(frame, corners)

        # Determinar tablero si no se ha hecho
        if not tablero_determinado and len(ids) >= 2:
            corner1 = corners[0][0]
            corner2 = corners[1][0]
            x_min = min(corner1[0][0], corner2[0][0])
            y_min = min(corner1[0][1], corner2[0][1])
            x_max = max(corner1[2][0], corner2[2][0])
            y_max = max(corner1[2][1], corner2[2][1])
            tablero_determinado = True

        if tablero_determinado and not juego_terminado:
            # Detectar fichas
            for i, marker_id in enumerate(ids.flatten()):
                if marker_id in [10, 20]:
                    ficha = "X" if marker_id == 10 else "O"
                    cx = int(corners[i][0][:, 0].mean())
                    cy = int(corners[i][0][:, 1].mean())

                    if x_min <= cx <= x_max and y_min <= cy <= y_max:
                        col = int((cx - x_min) / ((x_max - x_min) / 3))
                        row = int((cy - y_min) / ((y_max - y_min) / 3))

                        if 0 <= row < 3 and 0 <= col < 3 and board[row][col] == "":
                            board[row][col] = ficha
                            if ficha == "X":
                                turno_maquina = True

            # Turno de la máquina
            if turno_maquina and not verificar_empate(board):
                jugada = mejor_jugada_mejorada(board)
                if jugada:
                    r, c = jugada
                    board[r][c] = "O"
                turno_maquina = False

            # Dibujar tablero y fichas
            dibujar_tablero(frame, x_min, y_min, x_max, y_max)
            dibujar_fichas(frame, board, x_min, y_min, x_max, y_max)

            # Verificar ganador o empate
            ganador, linea = verificar_ganador(board)
            if ganador:
                dibujar_linea_ganadora(frame, linea, x_min, y_min, x_max, y_max)
                mostrar_mensaje(frame, f"{ganador} gana!")
                if not juego_terminado:
                    juego_terminado = True
                    tiempo_fin = time.time()
            elif verificar_empate(board):
                mostrar_mensaje(frame, "¡Empate!")
                if not juego_terminado:
                    juego_terminado = True
                    tiempo_fin = time.time()

    # Si el juego terminó, mantener el mensaje y la línea ganadora
    if juego_terminado:
        dibujar_tablero(frame, x_min, y_min, x_max, y_max)
        dibujar_fichas(frame, board, x_min, y_min, x_max, y_max)
        if ganador:
            dibujar_linea_ganadora(frame, linea, x_min, y_min, x_max, y_max)
            mostrar_mensaje(frame, f"{ganador} gana!")
        else:
            mostrar_mensaje(frame, "¡Empate!")

    cv2.imshow("Juego de Gato", frame)

    # Si el juego terminó, esperar 4 segundos y cerrar
    if juego_terminado and tiempo_fin is not None:
        if time.time() - tiempo_fin >= 4:
            break

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()