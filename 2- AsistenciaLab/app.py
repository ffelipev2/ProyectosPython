from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
import os
import shutil
from datetime import datetime, timedelta
import schedule
import time
import threading

app = Flask(__name__)
app.secret_key = 'clave_secreta'

archivo_estudiantes = 'registros_laboratorio.xlsx'
archivo_visitas = 'visitas_laboratorio.xlsx'

# Ruta de respaldo en OneDrive
BACKUP_PATH = r'C:\Users\ffeli\OneDrive\RespaldoAsistencia'
LOCK_FILE = "backup.lock"  # Evita ejecuciones simultáneas

def is_another_instance_running():
    return os.path.exists(LOCK_FILE)

def create_lock():
    with open(LOCK_FILE, "w") as f:
        f.write("running")

def remove_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

def backup_files():
    """Copia los archivos a la carpeta de OneDrive y limpia los antiguos"""
    if is_another_instance_running():
        print("Ya hay una instancia corriendo. Se omite este respaldo.")
        return

    create_lock()
    try:
        if not os.path.exists(archivo_estudiantes) or not os.path.exists(archivo_visitas):
            print("Error: Los archivos originales no existen")
            return

        os.makedirs(BACKUP_PATH, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        estudiantes_backup = f"registros_laboratorio_{timestamp}.xlsx"
        visitas_backup = f"visitas_laboratorio_{timestamp}.xlsx"

        shutil.copy2(archivo_estudiantes, os.path.join(BACKUP_PATH, estudiantes_backup))
        shutil.copy2(archivo_visitas, os.path.join(BACKUP_PATH, visitas_backup))

        print(f"Respaldo completado: {estudiantes_backup} y {visitas_backup}")
    except Exception as e:
        print(f"Error en respaldo: {str(e)}")
    finally:
        remove_lock()
        limpiar_respaldos_antiguos()

def limpiar_respaldos_antiguos():
    """Mantiene solo los respaldos del día actual y del anterior."""
    try:
        archivos = os.listdir(BACKUP_PATH)
        archivos = [f for f in archivos if f.startswith(('registros_laboratorio_', 'visitas_laboratorio_'))]

        def get_fecha(nombre):
            try:
                return nombre.split("_")[2]
            except IndexError:
                return None

        hoy = datetime.now().strftime("%Y%m%d")
        ayer = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        fechas_validas = {hoy, ayer}

        for archivo in archivos:
            fecha = get_fecha(archivo)
            if fecha and fecha not in fechas_validas:
                os.remove(os.path.join(BACKUP_PATH, archivo))
                print(f"Archivo eliminado: {archivo}")
    except Exception as e:
        print(f"Error al limpiar respaldos antiguos: {str(e)}")

def schedule_backup():
    """Programa el respaldo diario a las 17:30"""
    schedule.every().day.at("17:30").do(backup_files)

    while True:
        schedule.run_pending()
        time.sleep(60)  # Revisa cada minuto

# Iniciar el programador en un hilo separado
backup_thread = threading.Thread(target=schedule_backup)
backup_thread.daemon = True
backup_thread.start()


def validar_rut(rut):
    # Verificar que el RUT tenga exactamente un guión
    if rut.count('-') != 1:
        return False

    # Separar el número y el dígito verificador
    numero, dv = rut.split("-")

    # Verificar que el número tenga entre 7 y 8 dígitos y que el dígito verificador sea válido
    if not numero.isdigit() or len(numero) < 7 or len(numero) > 8:
        return False
    if not (dv.isdigit() or dv.upper() == 'K'):
        return False

    # Convertir el dígito verificador a mayúsculas
    dv = dv.upper()

    # Calcular el dígito verificador esperado
    suma = 0
    multiplicador = 2
    for c in reversed(numero):
        suma += int(c) * multiplicador
        multiplicador += 1
        if multiplicador > 7:
            multiplicador = 2
    dv_esperado = 11 - (suma % 11)
    if dv_esperado == 11:
        dv_esperado = '0'
    elif dv_esperado == 10:
        dv_esperado = 'K'
    else:
        dv_esperado = str(dv_esperado)

    # Comparar el dígito verificador ingresado con el esperado
    return dv == dv_esperado

# Asegurar que los archivos existen con las columnas correctas
if not os.path.exists(archivo_estudiantes):
    df = pd.DataFrame(columns=['RUT', 'Nombre', 'Apellido', 'Carrera', 'Asignatura'])
    df.to_excel(archivo_estudiantes, index=False)

if not os.path.exists(archivo_visitas):
    df = pd.DataFrame(columns=['RUT', 'Nombre', 'Apellido', 'Carrera', 'Asignatura', 'Motivo', 'Fecha', 'Hora', 'Minutos'])
    df.to_excel(archivo_visitas, index=False)

@app.route('/')
def formulario():
    return render_template('formulario.html')

@app.route('/registrar', methods=['POST'])
def registrar():
    rut = request.form['rut'].strip()  # Eliminar espacios en blanco
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    carrera = request.form['carrera']
    asignatura = request.form['asignatura']

    # Validar el RUT
    if not validar_rut(rut):
        flash('RUT inválido. Ingrese un RUT válido en formato 12345678-9 o 12345678-K.', 'error')
        return redirect(url_for('formulario'))

    df = pd.read_excel(archivo_estudiantes, dtype={'RUT': str})

    # Verificar si el RUT ya está registrado
    if df['RUT'].str.strip().str.lower().eq(rut.lower()).any():
        flash('El estudiante ya está registrado.', 'error')
    else:
        nuevo_registro = pd.DataFrame([[rut, nombre, apellido, carrera, asignatura]],
                                      columns=['RUT', 'Nombre', 'Apellido', 'Carrera', 'Asignatura'])
        df = pd.concat([df, nuevo_registro], ignore_index=True)
        df.to_excel(archivo_estudiantes, index=False)
        flash('Registro exitoso.', 'success')

    return redirect(url_for('formulario'))

@app.route('/visita', methods=['POST'])
def visita():
    rut = request.form['buscar_rut'].strip()  # Eliminar espacios en blanco
    motivo = request.form['motivo']
    minutos = request.form['minutos']

    # Validar el RUT
    if not validar_rut(rut):
        flash('RUT inválido. Ingrese un RUT válido en formato 12345678-9 o 12345678-K.', 'error')
        return redirect(url_for('formulario'))

    df_estudiantes = pd.read_excel(archivo_estudiantes, dtype={'RUT': str})

    # Verificar si el RUT está registrado
    if not df_estudiantes['RUT'].str.strip().str.lower().eq(rut.lower()).any():
        flash('RUT no registrado. Primero debe registrarse.', 'error')
    else:
        try:
            df_visitas = pd.read_excel(archivo_visitas, dtype={'RUT': str})
            estudiante = df_estudiantes[df_estudiantes['RUT'].str.strip().str.lower() == rut.lower()].iloc[0]
            fecha = datetime.now().strftime('%Y-%m-%d')
            hora = datetime.now().strftime('%H:%M:%S')

            # Crear el nuevo registro con el orden especificado
            nueva_visita = pd.DataFrame([[rut, estudiante['Nombre'], estudiante['Apellido'], estudiante['Carrera'], estudiante['Asignatura'], motivo, fecha, hora, minutos]],
                                        columns=['RUT', 'Nombre', 'Apellido', 'Carrera', 'Asignatura', 'Motivo', 'Fecha', 'Hora', 'Minutos'])
            df_visitas = pd.concat([df_visitas, nueva_visita], ignore_index=True)
            df_visitas.to_excel(archivo_visitas, index=False)
            flash('Visita registrada con éxito.', 'success')
        except Exception as e:
            flash(f'Error al registrar la visita: {str(e)}', 'error')

    return redirect(url_for('formulario'))

if __name__ == '__main__':
    app.run(debug=False)