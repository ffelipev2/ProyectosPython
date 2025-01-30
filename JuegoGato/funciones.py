# funciones.py

import cv2
import random


def inicializar_tablero():
    """Inicializa un tablero vacío de 3x3"""
    return [["" for _ in range(3)] for _ in range(3)]


def verificar_empate(board):
    """Verifica si hay un empate en el tablero"""
    for fila in board:
        for casilla in fila:
            if casilla == "":  # Si hay alguna casilla vacía, no hay empate
                return False
    return True  # Si no hay casillas vacías y no hay ganador, es empate


def verificar_ganador(board):
    """Verifica si hay un ganador en el tablero actual"""
    # Revisar filas, columnas y diagonales
    for i in range(3):
        # Revisar filas
        if board[i][0] == board[i][1] == board[i][2] != "":
            return board[i][0], [(i, 0), (i, 1), (i, 2)]
        # Revisar columnas
        if board[0][i] == board[1][i] == board[2][i] != "":
            return board[0][i], [(0, i), (1, i), (2, i)]

    # Revisar diagonales
    if board[0][0] == board[1][1] == board[2][2] != "":
        return board[0][0], [(0, 0), (1, 1), (2, 2)]
    if board[0][2] == board[1][1] == board[2][0] != "":
        return board[0][2], [(0, 2), (1, 1), (2, 0)]

    return None, []


def verificar_jugada_ganadora(board, ficha):
    """Verifica si hay una jugada ganadora disponible para la ficha dada"""
    for i in range(3):
        for j in range(3):
            if board[i][j] == "":
                board[i][j] = ficha
                ganador, _ = verificar_ganador(board)
                board[i][j] = ""
                if ganador == ficha:
                    return (i, j)
    return None


def crear_fork(board):
    """Busca oportunidades para crear un fork (dos caminos para ganar)"""
    for i in range(3):
        for j in range(3):
            if board[i][j] == "":
                board[i][j] = "O"
                victorias_posibles = 0
                for x in range(3):
                    for y in range(3):
                        if board[x][y] == "":
                            board[x][y] = "O"
                            if verificar_ganador(board)[0] == "O":
                                victorias_posibles += 1
                            board[x][y] = ""
                board[i][j] = ""
                if victorias_posibles > 1:
                    return (i, j)
    return None


def mejor_jugada_mejorada(board):
    """Implementa la estrategia perfecta para el juego"""
    # 1. Ganar si es posible
    jugada = verificar_jugada_ganadora(board, "O")
    if jugada:
        return jugada

    # 2. Bloquear victoria del oponente
    jugada = verificar_jugada_ganadora(board, "X")
    if jugada:
        return jugada

    # 3. Crear un fork
    jugada = crear_fork(board)
    if jugada:
        return jugada

    # 4. Bloquear fork del oponente
    for i in range(3):
        for j in range(3):
            if board[i][j] == "":
                board[i][j] = "X"
                if crear_fork(board):
                    board[i][j] = ""
                    if board[1][1] == "":
                        return (1, 1)
                    lados = [(0, 1), (1, 0), (1, 2), (2, 1)]
                    for lado in lados:
                        if board[lado[0]][lado[1]] == "":
                            return lado
                board[i][j] = ""

    # 5. Centro
    if board[1][1] == "":
        return (1, 1)

    # 6. Esquina opuesta
    esquinas = [(0, 0), (0, 2), (2, 0), (2, 2)]
    esquinas_opuestas = {(0, 0): (2, 2), (0, 2): (2, 0), (2, 0): (0, 2), (2, 2): (0, 0)}
    for esquina in esquinas:
        if board[esquina[0]][esquina[1]] == "X":
            opuesta = esquinas_opuestas[esquina]
            if board[opuesta[0]][opuesta[1]] == "":
                return opuesta

    # 7. Cualquier esquina
    for esquina in esquinas:
        if board[esquina[0]][esquina[1]] == "":
            return esquina

    # 8. Cualquier lado
    lados = [(0, 1), (1, 0), (1, 2), (2, 1)]
    for lado in lados:
        if board[lado[0]][lado[1]] == "":
            return lado

    return None


def dibujar_tablero(frame, x_min, y_min, x_max, y_max):
    """Dibuja la grilla del tablero"""
    cell_width = (x_max - x_min) / 3
    cell_height = (y_max - y_min) / 3

    for i in range(1, 3):
        cv2.line(frame, (int(x_min + i * cell_width), int(y_min)),
                 (int(x_min + i * cell_width), int(y_max)), (0, 255, 0), 2)
        cv2.line(frame, (int(x_min), int(y_min + i * cell_height)),
                 (int(x_max), int(y_min + i * cell_height)), (0, 255, 0), 2)


def dibujar_fichas(frame, board, x_min, y_min, x_max, y_max):
    """Dibuja las fichas (X/O) en el tablero"""
    for r in range(3):
        for c in range(3):
            if board[r][c] != "":
                ficha = board[r][c]
                cv2.putText(frame, ficha,
                            (int(x_min + c * ((x_max - x_min) / 3) + 20),
                             int(y_min + r * ((y_max - y_min) / 3) + 50)),
                            cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0), 4)


def dibujar_linea_ganadora(frame, linea, x_min, y_min, x_max, y_max):
    """Dibuja la línea que marca la victoria"""
    puntos = [(int(x_min + (linea[i][1] + 0.5) * (x_max - x_min) / 3),
               int(y_min + (linea[i][0] + 0.5) * (y_max - y_min) / 3)) for i in range(3)]
    cv2.line(frame, puntos[0], puntos[2], (0, 255, 255), 5)


def mostrar_mensaje(frame, mensaje, posicion=(50, 50), color=(0, 0, 255)):
    """Muestra un mensaje en la pantalla"""
    cv2.putText(frame, mensaje, posicion, cv2.FONT_HERSHEY_SIMPLEX, 2, color, 3)