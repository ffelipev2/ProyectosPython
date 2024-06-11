from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import fitz  # PyMuPDF
import nltk
from nltk.tokenize import word_tokenize

app = Flask(__name__)

# Configuración de la carpeta de subida
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
                    lista.append(imprimir_texto_entre_tokens(tokens, [',', 'RUT', 'N°'], [',', 'representada', 'por'], ocurrencia=1))
                    lista.append(imprimir_texto_entre_tokens(tokens, [',', 'entre', ], [',', 'RUT', 'N°'], ocurrencia=1))
                    lista.append(imprimir_texto_entre_tokens(tokens, [',', 'RUT', 'N°'], [',', 'representada', 'por'], ocurrencia=2))
                    lista.append(imprimir_texto_entre_tokens(tokens, ['E'], ['En'], ocurrencia=1))
                    lista.append(imprimir_texto_entre_tokens(tokens, ['funcionamiento', 'de', 'sus', 'instalaciones', 'ubicadas', 'en'], ['.', 'El', 'CLIENTE'], ocurrencia=1))
                    lista.append(imprimir_texto_entre_tokens(tokens, ['se', 'obliga', ',', 'a', 'contar', 'del', 'día'], [',', 'a', 'suministrar'], ocurrencia=1))
                    lista.append(imprimir_texto_entre_tokens(tokens, ['y', 'hasta', 'el'], ['.', 'El'], ocurrencia=1))
                    lista.append(imprimir_texto_entre_tokens(tokens, ["[", "GWh/año", "]"], ["CUARTO", ":", "PRECIO"], ocurrencia=1))
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
    app.run(debug=True)