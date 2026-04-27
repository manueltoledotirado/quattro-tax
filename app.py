"""
Quattro Tax Consulting — Web App Backend
"""
import os, json, zipfile, tempfile, shutil, subprocess, sys
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import anthropic
from quattro_autofill import (
    map_individual_1040, map_schedule_c, map_1120s,
    map_1065, map_8962, determinar_forms
)

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def fill_form(input_pdf, field_values, output_pdf):
    values_file = output_pdf.replace('.pdf', '_vals.json')
    with open(values_file, 'w') as f:
        json.dump(field_values, f)
    result = subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, 'fill_fillable_fields.py'),
         input_pdf, values_file, output_pdf],
        capture_output=True, text=True
    )
    try: os.remove(values_file)
    except: pass
    return result.returncode == 0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
def extract_documents():
    api_key = request.headers.get('X-Api-Key', '')
    if not api_key:
        return jsonify({'error': 'API key requerida'}), 401
    data = request.json
    documents = data.get('documents', [])
    client_type = data.get('client_type', 'individual')
    if not documents:
        return jsonify({'error': 'No se enviaron documentos'}), 400
    try:
        client = anthropic.Anthropic(api_key=api_key)
        content = []
        for doc in documents:
            mime = doc['type']
            if mime.startswith('image/'):
                content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': mime, 'data': doc['base64']}})
            elif mime == 'application/pdf':
                content.append({'type': 'document', 'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': doc['base64']}})
            content.append({'type': 'text', 'text': f"(Archivo: {doc['name']}, tipo: {doc.get('category','general')})"})

        if client_type == 'individual':
            schema = '{"nombre":"","apellido":"","ssn":"","address":"","city":"","state":"TX","zip":"","employer_name":"","w2_wages":0,"federal_withheld":0,"ss_withheld":0,"medicare_withheld":0,"income_1099_nec":0,"income_1099_misc":0,"interest_1099_int":0,"dividends_1099_div":0,"ira_1099_r":0,"unemployment_1099_g":0,"oc_premiums":0,"oc_slcsp":0,"oc_advance_ptc":0,"oc_magi":0,"oc_family_size":1,"k1_income":0,"rental_income":0,"tiene_obamacare":false,"tiene_negocio":false,"tiene_renta":false,"tiene_cripto":false,"notas":""}'
        else:
            schema = '{"nombre_empresa":"","ein":"","tipo_entidad":"S-Corp","address":"","actividad":"","gross_receipts":0,"cogs":0,"wages":0,"officer_comp":0,"rent":0,"advertising":0,"utilities":0,"insurance":0,"repairs":0,"taxes_licenses":0,"interest":0,"depreciation":0,"other_expenses":0,"total_assets":0,"notas":""}'

        content.append({'type': 'text', 'text': f'Analiza estos documentos fiscales 2025 de un cliente {client_type}. Extrae todos los números exactamente como aparecen. Responde SOLO con JSON sin markdown:\n{schema}'})

        message = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=2000,
            messages=[{'role': 'user', 'content': content}]
        )
        raw = message.content[0].text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        extracted = json.loads(raw)
        return jsonify({'success': True, 'data': extracted})
    except anthropic.AuthenticationError:
        return jsonify({'error': 'API key inválida'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate', methods=['POST'])
def generate_pdfs():
    data = request.json
    client_type = data.get('client_type', 'individual')
    client_data = data.get('client_data', {})
    tmp_dir = tempfile.mkdtemp()
    try:
        if client_type == 'individual':
            nombre = f"{client_data.get('nombre','')}{client_data.get('apellido','')}".strip().replace(' ','_') or 'cliente'
        else:
            nombre = (client_data.get('empresa', {}).get('nombre', 'empresa') or 'empresa').replace(' ','_')

        forms = determinar_forms(client_data, client_type)
        form_map = {
            '1040':       (os.path.join(BASE_DIR, 'f1040.pdf'),   map_individual_1040, 'Form_1040'),
            'schedule_c': (os.path.join(BASE_DIR, 'f1040sc.pdf'), map_schedule_c,      'Schedule_C'),
            'schedule_e': (os.path.join(BASE_DIR, 'f1040se.pdf'), lambda d: [],        'Schedule_E'),
            'schedule_d': (os.path.join(BASE_DIR, 'f1040sd.pdf'), lambda d: [],        'Schedule_D'),
            '8962':       (os.path.join(BASE_DIR, 'f8962.pdf'),   map_8962,            'Form_8962'),
            '1120s':      (os.path.join(BASE_DIR, 'f1120s.pdf'),  map_1120s,           'Form_1120S'),
            '1120':       (os.path.join(BASE_DIR, 'f1120.pdf'),   lambda d: [],        'Form_1120'),
            '1065':       (os.path.join(BASE_DIR, 'f1065.pdf'),   map_1065,            'Form_1065'),
            'tx_05158a':  (os.path.join(BASE_DIR, 'f1120s.pdf'),  lambda d: [],        'TX_Franchise'),
            'tx_05102':   (os.path.join(BASE_DIR, 'f1120s.pdf'),  lambda d: [],        'TX_PIR'),
        }
        generated = []
        for form_key in forms:
            if form_key not in form_map: continue
            input_pdf, mapper, label = form_map[form_key]
            if not os.path.exists(input_pdf): continue
            field_values = mapper(client_data)
            out_pdf = os.path.join(tmp_dir, f'{nombre}_{label}.pdf')
            if field_values:
                fill_form(input_pdf, field_values, out_pdf)
            else:
                shutil.copy(input_pdf, out_pdf)
            if os.path.exists(out_pdf):
                generated.append(out_pdf)

        if not generated:
            return jsonify({'error': 'No se generaron PDFs'}), 500

        zip_name = f'{nombre}_declaracion_2025.zip'
        zip_path = os.path.join(tmp_dir, zip_name)
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for pdf in generated:
                zf.write(pdf, os.path.basename(pdf))

        return send_file(zip_path, mimetype='application/zip',
                         as_attachment=True, download_name=zip_name)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'service': 'Quattro Tax API 2025'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
