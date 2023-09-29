from flask import Flask, render_template, request, send_file, redirect, url_for, session
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, validators
import random, os, pickle, logging
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, PageBreak
from io import BytesIO


logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretkey'

tablas_generadas = set()

# Funciones
def generar_tabla():
    rangos = [(1, 16), (16, 31), (31, 46), (46, 61), (61, 76)]
    tabla = [random.sample(range(start, end), 5) for start, end in rangos]
    tabla[2][2] = 'X'
    return list(zip(*tabla))

def generar_serie():
    series = []
    for _ in range(8):
        tabla = generar_tabla()
        tabla_tuple = tuple(tuple(row) for row in tabla)
        while tabla_tuple in tablas_generadas:
            tabla = generar_tabla()
            tabla_tuple = tuple(tuple(row) for row in tabla)
        tablas_generadas.add(tabla_tuple)
        series.append(tabla)
    return series

def generar_series(n):
    return [generar_serie() for _ in range(n)]

def generate_pdf(form, series):
    buffer = BytesIO()
    
    # Ajuste de márgenes
    top_margin = 36
    bottom_margin = 36
    left_margin = 72
    right_margin = 72

    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=top_margin, leftMargin=left_margin, rightMargin=right_margin, bottomMargin=bottom_margin)
    story = []
    page_width, page_height = A4
    usable_width = page_width - doc.leftMargin - doc.rightMargin
    usable_height = page_height - doc.topMargin - doc.bottomMargin

    # Ajustamos el ancho y alto de las celdas
    col_width = usable_width / 12
    row_height = usable_height / 32

    for serie in series:  # Recorremos todas las series
        # Encabezado
        header_data = [
            [form.titulo.data, "Valor: $" + form.valor.data],
            [form.subtitulo.data, ""],
            ["Organizado por: " + form.organizador.data, ""],
            ["Dirección: " + form.direccion.data, ""],
            ["Fecha y hora: " + form.fecha_hora.data, ""]
        ]
        header_table = Table(header_data, colWidths=[0.7 * usable_width, 0.3 * usable_width])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        story.append(header_table)
        story.append(Spacer(0, 5))

        # Tablas
        for i in range(0, 8, 2):
            fila_data = []
            for j in range(2):
                idx = i + j
                tabla = serie[idx]
                bingo_data = [
                    ['B', 'I', 'N', 'G', 'O'],
                    tabla[0], tabla[1], tabla[2], tabla[3], tabla[4]
                ]

                for idx, fila in enumerate(bingo_data):
                    fila_list = list(fila)
                    for k, celda in enumerate(fila_list):
                        if celda == 'X':
                            fila_list[k] = form.organizador.data
                    bingo_data[idx] = fila_list

                bingo_table = Table(bingo_data, colWidths=[col_width] * 5, rowHeights=[row_height] * 6)
                bingo_table.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BOX', (0, 0), (-1, -1), 2, colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('BOLD', (0, 0), (4, 0), True)
                ]))
                fila_data.append(bingo_table)

                if j == 0:
                    fila_data.append(Spacer(col_width, 0))

            fila_table = Table([fila_data], colWidths=[col_width * 5, col_width, col_width * 5], hAlign='LEFT')
            story.append(fila_table)
            if i != 6:
                story.append(Spacer(0, 5))

        if serie != series[-1]:
            story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return buffer

class ConfiguracionForm(FlaskForm):
    titulo = StringField('Título', [validators.DataRequired()])
    subtitulo = StringField('Subtítulo', [validators.DataRequired()])
    organizador = StringField('Organizado por', [validators.DataRequired()])
    direccion = StringField('Dirección', [validators.DataRequired()])
    fecha_hora = StringField('Fecha y Hora', [validators.DataRequired()])
    valor = StringField('Valor $', [validators.DataRequired()])
    cantidad_series = IntegerField('Número de Series a generar', [validators.NumberRange(min=1, max=1000)])
    submit = SubmitField('Previsualizar')

@app.route('/', methods=['GET', 'POST'])
def index():
    form = ConfiguracionForm()
    if form.validate_on_submit():
        series = generar_series(form.cantidad_series.data)
        
        # Guardar las series directamente en la sesión
        session['series'] = [list(map(list, serie)) for serie in series]
        session['form_data'] = form.data
        
        return redirect(url_for('preview'))
    return render_template('index.html', form=form)

@app.route('/preview', methods=['POST'])
def preview():
    form_data = request.form
    series = generar_series(int(form_data['cantidad_series']))
    form = ConfiguracionForm(data=form_data)
    series = [list(map(tuple, serie)) for serie in series]
    return render_template('bingo_content.html', form=form, series=series)

@app.route('/download')
def download():
    form_data = session.get('form_data')
    series = session.get('series')
    if not form_data or not series:
        return redirect(url_for('index'))
    form = ConfiguracionForm(data=form_data)
    series = [list(map(tuple, serie)) for serie in series]
    pdf_stream = generate_pdf(form, series)
    return send_file(pdf_stream, as_attachment=True, download_name="bingo.pdf", mimetype="application/pdf")

if __name__ == "__main__":
    app.run(debug=True)