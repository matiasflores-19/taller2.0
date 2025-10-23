from flask import Flask, render_template, request, jsonify
import cv2
import pytesseract
import sqlite3
import numpy as np
import re
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'taller_mecanico_secret'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Crear carpeta de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configurar Tesseract
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def conectar_db():
    conn = sqlite3.connect("taller.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patente TEXT UNIQUE,
            duenio TEXT,
            vehiculo TEXT,
            falla TEXT,
            email TEXT,
            fecha_ingreso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            estado TEXT DEFAULT 'En taller'
        )
    """)
    conn.commit()
    return conn, cursor

def preprocesar_imagen(frame):
    """Preprocesamiento para patentes"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    
    # Mejorar contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    # Binarización adaptativa
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY, 11, 2)
    
    # Operaciones morfológicas
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    return thresh

def detectar_patente(frame):
    """Detectar patente en la imagen"""
    try:
        processed = preprocesar_imagen(frame)
        
        configs = [
            '--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
            '--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
            '--psm 11 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        ]
        
        for config in configs:
            texto = pytesseract.image_to_string(processed, config=config)
            texto_limpio = re.sub(r'[^A-Z0-9]', '', texto.upper())
            
            patrones = [
                r'[A-Z]{2}[0-9]{3}[A-Z]{2}',      # AA123BB
                r'[A-Z]{3}[0-9]{3}',              # AAA123
                r'[A-Z]{2}[0-9]{3}[A-Z]{1}',      # AA123B
                r'[0-9]{3}[A-Z]{3}',              # 123AAA
                r'[A-Z]{1}[0-9]{3}[A-Z]{3}',      # A123AAA
                r'[A-Z]{3}[0-9]{2}[A-Z]{1}',      # AAA12B
                r'[A-Z]{1}[0-9]{2}[A-Z]{3}',      # A12AAA
            ]
            
            for patron in patrones:
                coincidencias = re.findall(patron, texto_limpio)
                if coincidencias and len(coincidencias[0]) >= 5:
                    return coincidencias[0]
        
        return None
        
    except Exception as e:
        print(f"Error en OCR: {e}")
        return None

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/scan')
def scan():
    """Página de escaneo"""
    return render_template('scan.html')

@app.route('/vehiculos')
def vehiculos():
    """Página de listado de vehículos"""
    conn, cursor = conectar_db()
    cursor.execute("SELECT * FROM vehiculos ORDER BY fecha_ingreso DESC")
    vehiculos = cursor.fetchall()
    conn.close()
    
    return render_template('vehiculos.html', vehiculos=vehiculos)

@app.route('/api/upload_image', methods=['POST'])
def upload_image():
    """Procesar imagen subida desde el ordenador"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No se seleccionó ninguna imagen'})
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó ningún archivo'})
        
        if file and allowed_file(file.filename):
            # Leer imagen
            file_bytes = np.frombuffer(file.read(), np.uint8)
            frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
            if frame is None:
                return jsonify({'success': False, 'error': 'Error al procesar la imagen'})
            
            # Detectar patente
            patente = detectar_patente(frame)
            
            if patente:
                # Verificar si ya existe en la base de datos
                conn, cursor = conectar_db()
                cursor.execute("SELECT * FROM vehiculos WHERE patente=?", (patente,))
                vehiculo_existente = cursor.fetchone()
                conn.close()
                
                if vehiculo_existente:
                    return jsonify({
                        'success': True,
                        'patente': patente,
                        'existe': True,
                        'vehiculo': {
                            'duenio': vehiculo_existente[2],
                            'vehiculo': vehiculo_existente[3],
                            'falla': vehiculo_existente[4],
                            'email': vehiculo_existente[5],
                            'estado': vehiculo_existente[7]
                        }
                    })
                else:
                    return jsonify({
                        'success': True,
                        'patente': patente,
                        'existe': False
                    })
            else:
                return jsonify({
                    'success': True,
                    'patente': None,
                    'mensaje': 'No se detectó ninguna patente en la imagen'
                })
        else:
            return jsonify({'success': False, 'error': 'Tipo de archivo no permitido'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/guardar_vehiculo', methods=['POST'])
def guardar_vehiculo():
    """Guardar nuevo vehículo en la base de datos"""
    try:
        data = request.json
        patente = data.get('patente', '').upper()
        duenio = data.get('duenio', '')
        vehiculo = data.get('vehiculo', '')
        falla = data.get('falla', '')
        email = data.get('email', '')
        
        if not all([patente, duenio, vehiculo, email]):
            return jsonify({'success': False, 'error': 'Faltan campos obligatorios'})
        
        conn, cursor = conectar_db()
        cursor.execute("""
            INSERT INTO vehiculos (patente, duenio, vehiculo, falla, email)
            VALUES (?, ?, ?, ?, ?)
        """, (patente, duenio, vehiculo, falla, email))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'mensaje': 'Vehículo guardado correctamente'})
        
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'La patente ya existe'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/vehiculos', methods=['GET'])
def api_vehiculos():
    """API para obtener vehículos"""
    conn, cursor = conectar_db()
    cursor.execute("SELECT * FROM vehiculos ORDER BY fecha_ingreso DESC")
    vehiculos = cursor.fetchall()
    conn.close()
    
    vehiculos_json = []
    for v in vehiculos:
        vehiculos_json.append({
            'id': v[0],
            'patente': v[1],
            'duenio': v[2],
            'vehiculo': v[3],
            'falla': v[4],
            'email': v[5],
            'fecha_ingreso': v[6],
            'estado': v[7]
        })
    
    return jsonify(vehiculos_json)

if __name__ == '__main__':
    # Crear carpeta de templates si no existe
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("🚀 Taller Mecánico - Sistema de Carga de Imágenes")
    print("📁 Sube imágenes de patentes desde tu ordenador")
    print("🌐 Servidor: http://localhost:5000")
    print("🔓 Usando HTTP (sin problemas de certificados)")
    
    # ✅ EJECUTAR SOLO CON HTTP - SIN SSL
    app.run(debug=True, host='0.0.0.0', port=5000)