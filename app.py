from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
import os
import fitz  # PyMuPDF
import nltk
from nltk.tokenize import word_tokenize

app = Flask(__name__)

# Configuración de la carpeta de subida
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar la base de datos
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Modelo de datos
class PDFData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rut_suministrador = db.Column(db.String(100))
    razon_social_suministrador = db.Column(db.String(100))
    rut_cliente = db.Column(db.String(100))
    razon_social_cliente = db.Column(db.String(100))
    nombre_instalacion = db.Column(db.String(100))
    fecha_inicio = db.Column(db.String(100))
    fecha_termino = db.Column(db.String(100))
    energia_contratada = db.Column(db.String(100))
    energia_contratada2 = db.Column(db.String(100))

    def __repr__(self):
        return f'<PDFData {self.id}>'

# Configuración de Flask-Admin
admin = Admin(app, name='Base de datos PDF', template_mode='bootstrap3')
admin.add_view(ModelView(PDFData, db.session))

# Asegúrate de que la carpeta de subidas exista
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    success = False
    lista = []  # Inicializa la lista fuera del bloque condicional
    if request.method == 'POST':
        if 'file[]' not in request.files:
            message = 'No se encontró ningún archivo'
            success = False
        else:
            files = request.files.getlist('file[]')  # Obtener una lista de archivos
            for file in files:
                if file.filename == '':
                    message = 'No se seleccionó ningún archivo'
                    success = False
                elif file and file.filename.endswith('.pdf'):
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
                    nombre = 'uploads/' + file.filename
                    tokens = leerDocumentoYtokenizar(nombre)
                    data = [
                        imprimir_texto_entre_tokens(tokens, [',', 'RUT', 'N°'], [',', 'representada', 'por'], ocurrencia=1),
                        imprimir_texto_entre_tokens(tokens, [',', 'entre', ], [',', 'RUT', 'N°'], ocurrencia=1),
                        imprimir_texto_entre_tokens(tokens, [',', 'RUT', 'N°'], [',', 'representada', 'por'], ocurrencia=2),
                        imprimir_texto_entre_tokens(tokens, ['E'], ['En'], ocurrencia=1),
                        imprimir_texto_entre_tokens(tokens, ['funcionamiento', 'de', 'sus', 'instalaciones', 'ubicadas', 'en'], ['.', 'El', 'CLIENTE'], ocurrencia=1),
                        imprimir_texto_entre_tokens(tokens, ['se', 'obliga', ',', 'a', 'contar', 'del', 'día'], [',', 'a', 'suministrar'], ocurrencia=1),
                        imprimir_texto_entre_tokens(tokens, ['y', 'hasta', 'el'], ['.', 'El'], ocurrencia=1),
                        imprimir_texto_entre_tokens(tokens, ["[", "GWh/año", "]"], ["CUARTO", ":", "PRECIO"], ocurrencia=1),
                    ]
                    lista.extend(data)
                    # Guardar los datos en la base de datos
                    pdf_data = PDFData(
                        rut_suministrador=data[0],
                        razon_social_suministrador=data[1],
                        rut_cliente=data[2],
                        razon_social_cliente=data[3],
                        nombre_instalacion=data[4],
                        fecha_inicio=data[5],
                        fecha_termino=data[6],
                        energia_contratada=data[7]
                    )
                    db.session.add(pdf_data)
                    db.session.commit()
                    message = f"Los archivos se subieron correctamente"
                    success = True
                else:
                    message = 'Formato de archivo no permitido. Solo se permiten archivos PDF.'
                    success = False
        return render_template('index.html', message=message, success=success, var=lista)
    return render_template('index.html')


def leerDocumentoYtokenizar(nombre):
    pdf_path = str(nombre)
    pdf_document = fitz.open(pdf_path)
    pdf_text = ""
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        pdf_text += page.get_text()
    pdf_document.close()
    tokens = word_tokenize(pdf_text)
    return tokens

def imprimir_texto_entre_tokens(lista_tokens, tokens_inicio, tokens_fin, ocurrencia=1):
    # Variable para almacenar el resultado
    resultado = ""
    ocurrencias_encontradas = 0

    # Buscar todas las ocurrencias de la secuencia de tokens de inicio
    for i in range(len(lista_tokens) - len(tokens_inicio) + 1):
        if lista_tokens[i:i + len(tokens_inicio)] == tokens_inicio:
            ocurrencias_encontradas += 1

            # Verificar si esta es la ocurrencia que se quiere imprimir
            if ocurrencias_encontradas == ocurrencia:
                indice_inicio = i

                # Buscar el índice de la secuencia de tokens de fin
                for j in range(i + len(tokens_inicio), len(lista_tokens) - len(tokens_fin) + 1):
                    if lista_tokens[j:j + len(tokens_fin)] == tokens_fin:
                        indice_fin = j

                        # Obtener el texto entre las secuencias de tokens de inicio y fin
                        texto_entre_tokens = lista_tokens[indice_inicio + len(tokens_inicio):indice_fin]
                        resultado = ' '.join(texto_entre_tokens)
                        break
                break  # Romper el bucle externo si se encuentra la ocurrencia deseada

    return resultado

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Crear las tablas de la base de datos
    app.run(debug=True)
