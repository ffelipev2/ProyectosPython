import nltk
from nltk.tokenize import word_tokenize
import fitz  # PyMuPDF
def contrato_1(tokens):
    data = [
        imprimir_texto_entre_tokens(tokens, [',', 'RUT', 'N°'], [',', 'representada', 'por'], ocurrencia=1),
        imprimir_texto_entre_tokens(tokens, [',', 'entre'], [',', 'RUT', 'N°'], ocurrencia=1),
        imprimir_texto_entre_tokens(tokens, [',', 'RUT', 'N°'], [',', 'representada', 'por'], ocurrencia=2),
        imprimir_texto_entre_tokens(tokens, ['E'], ['En'], ocurrencia=1),
        imprimir_texto_entre_tokens(tokens, ['funcionamiento', 'de', 'sus', 'instalaciones', 'ubicadas', 'en'],
                                    ['.', 'El', 'CLIENTE'], ocurrencia=1),
        imprimir_texto_entre_tokens(tokens, ['se', 'obliga', ',', 'a', 'contar', 'del', 'día'],
                                    [',', 'a', 'suministrar'], ocurrencia=1),
        imprimir_texto_entre_tokens(tokens, ['y', 'hasta', 'el'], ['.', 'El'], ocurrencia=1),
        imprimir_texto_entre_tokens(tokens, ["[", "GWh/año", "]"], ["CUARTO", ":", "PRECIO"], ocurrencia=1),
    ]
    return data



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
    resultado = ""
    ocurrencias_encontradas = 0

    for i in range(len(lista_tokens) - len(tokens_inicio) + 1):
        if lista_tokens[i:i + len(tokens_inicio)] == tokens_inicio:
            ocurrencias_encontradas += 1
            if ocurrencias_encontradas == ocurrencia:
                indice_inicio = i

                for j in range(i + len(tokens_inicio), len(lista_tokens) - len(tokens_fin) + 1):
                    if lista_tokens[j:j + len(tokens_fin)] == tokens_fin:
                        indice_fin = j
                        texto_entre_tokens = lista_tokens[indice_inicio + len(tokens_inicio):indice_fin]
                        resultado = ' '.join(texto_entre_tokens)
                        break
                break

    return resultado