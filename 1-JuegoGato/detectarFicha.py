import cv2
import cv2.aruco as aruco

# Cargar diccionario ArUco
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Convertir a escala de grises
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Detectar marcadores ArUco
    corners, ids, _ = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            # Dibujar cuadro alrededor del ArUco
            aruco.drawDetectedMarkers(frame, corners)

            # Determinar si es "X" o "O" según su ID
            ficha = "X" if marker_id == 10 else "O" if marker_id == 20 else "Desconocida"
            cv2.putText(frame, f"Ficha: {ficha}", (50, 50 + i * 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

    # Mostrar imagen
    cv2.imshow("Tic Tac Toe - ArUco", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
