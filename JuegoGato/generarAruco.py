import cv2
import cv2.aruco as aruco

# Crear un diccionario ArUco (PUEDES CAMBIAR EL DICT PARA MEJOR DETECCIÓN)
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)

# Crear imagen para "X" (ID 10)
marker_x = aruco.generateImageMarker(aruco_dict, 10, 200)
cv2.imwrite("aruco_x.png", marker_x)

# Crear imagen para "O" (ID 20)
marker_o = aruco.generateImageMarker(aruco_dict, 20, 200)
cv2.imwrite("aruco_o.png", marker_o)

print("Marcadores generados: 'aruco_x.png' y 'aruco_o.png'")