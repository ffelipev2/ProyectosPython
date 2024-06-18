from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from controllers import *
import os


app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'gatito1234578'

db = SQLAlchemy(app)
migrate = Migrate(app, db)


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

    def __repr__(self):
        return f'<PDFData {self.id}>'


admin = Admin(app, name='Base de datos PDF', template_mode='bootstrap3')
admin.add_view(ModelView(PDFData, db.session))

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    success = False
    lista = []
    if request.method == 'POST':
        if 'file[]' not in request.files:
            message = 'No se encontró ningún archivo'
            success = False
        else:
            files = request.files.getlist('file[]')
            for file in files:
                if file.filename == '':
                    message = 'No se seleccionó ningún archivo'
                    success = False
                elif file and file.filename.endswith('.pdf'):
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
                    nombre = 'uploads/' + file.filename
                    tokens = leerDocumentoYtokenizar(nombre)
                    data = [
                        imprimir_texto_entre_tokens(tokens, [',', 'RUT', 'N°'], [',', 'representada', 'por'],
                                                    ocurrencia=1),
                        imprimir_texto_entre_tokens(tokens, [',', 'entre', ], [',', 'RUT', 'N°'], ocurrencia=1),
                        imprimir_texto_entre_tokens(tokens, [',', 'RUT', 'N°'], [',', 'representada', 'por'],
                                                    ocurrencia=2),
                        imprimir_texto_entre_tokens(tokens, ['E'], ['En'], ocurrencia=1),
                        imprimir_texto_entre_tokens(tokens,
                                                    ['funcionamiento', 'de', 'sus', 'instalaciones', 'ubicadas', 'en'],
                                                    ['.', 'El', 'CLIENTE'], ocurrencia=1),
                        imprimir_texto_entre_tokens(tokens, ['se', 'obliga', ',', 'a', 'contar', 'del', 'día'],
                                                    [',', 'a', 'suministrar'], ocurrencia=1),
                        imprimir_texto_entre_tokens(tokens, ['y', 'hasta', 'el'], ['.', 'El'], ocurrencia=1),
                        imprimir_texto_entre_tokens(tokens, ["[", "GWh/año", "]"], ["CUARTO", ":", "PRECIO"],
                                                    ocurrencia=1),
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

    pdf_data_list = PDFData.query.all()
    return render_template('index.html', message=message, success=success, pdf_data_list=pdf_data_list, var=lista)


@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    pdf_data = PDFData.query.get(id)
    if pdf_data:
        db.session.delete(pdf_data)
        db.session.commit()
    return redirect(url_for('index'))


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    pdf_data = PDFData.query.get(id)
    if request.method == 'POST':
        pdf_data.rut_suministrador = request.form['rut_suministrador']
        pdf_data.razon_social_suministrador = request.form['razon_social_suministrador']
        pdf_data.rut_cliente = request.form['rut_cliente']
        pdf_data.razon_social_cliente = request.form['razon_social_cliente']
        pdf_data.nombre_instalacion = request.form['nombre_instalacion']
        pdf_data.fecha_inicio = request.form['fecha_inicio']
        pdf_data.fecha_termino = request.form['fecha_termino']
        pdf_data.energia_contratada = request.form['energia_contratada']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit.html', pdf_data=pdf_data)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
