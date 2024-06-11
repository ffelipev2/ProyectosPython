import fitz  # PyMuPDF
import nltk
from nltk.tokenize import word_tokenize

pdf_path = 'uploads/contrato_1.pdf'

# Abre el archivo PDF
pdf_document = fitz.open(pdf_path)

# Variable para almacenar el contenido del PDF
pdf_text = ""

# Itera sobre cada página del documento
for page_num in range(pdf_document.page_count):
    # Obtiene la página
    page = pdf_document.load_page(page_num)
    # Extrae el texto de la página
    pdf_text += page.get_text()

# Cierra el documento PDF
pdf_document.close()

# Tokenizar el texto extraído del PDF
tokens = word_tokenize(pdf_text)

# Imprimir los tokens resultantes (opcional)
print(tokens)

#Este algoritmo permite colocar un numero de tokens de inicio y un numero de tokens final y encuentra el tokens que este entre el inicio y el final
#La cantidad de tokens de inicio y final se pueden variar.
#La ocurrencia es una entrada al algoritmo que permite imprimir una palabra que pueda tener un mismo
#texto de inicio y Final . En el caso del documento de este ejemplo hay 2 rut que tienen esta forma:
# RUT N° 19.689.123-4 , representada por
# RUT N° 20.689.123-4 , representada por
# Si quiero encontrar el segundo rut , cambio ocurrencia 1 por ocurrencia 2, es decir , el segundo que aparece

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


print(imprimir_texto_entre_tokens(tokens, [',', 'RUT', 'N°'], [',', 'representada', 'por'],ocurrencia=1))
imprimir_texto_entre_tokens(tokens, [',', 'entre', ], [',', 'RUT', 'N°'],ocurrencia=1)
imprimir_texto_entre_tokens(tokens, [',', 'RUT', 'N°'], [',', 'representada', 'por'],ocurrencia=2) # ocurrencia 2 , que es el segundo rut donde los textos que se anteponen y lo preceden son iguales.
imprimir_texto_entre_tokens(tokens, ['E'], ['En'],ocurrencia=1)
imprimir_texto_entre_tokens(tokens, ['funcionamiento', 'de', 'sus', 'instalaciones', 'ubicadas', 'en'], ['.', 'El', 'CLIENTE'],ocurrencia=1)
imprimir_texto_entre_tokens(tokens, ['se', 'obliga', ',', 'a', 'contar', 'del', 'día'], [',', 'a', 'suministrar'],ocurrencia=1)
imprimir_texto_entre_tokens(tokens, ['y', 'hasta', 'el'], ['.', 'El'],ocurrencia=1)
imprimir_texto_entre_tokens(tokens, ["[", "GWh/año", "]"], ["CUARTO", ":", "PRECIO"],ocurrencia=1)