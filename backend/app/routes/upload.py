from flask import Blueprint, request, jsonify, current_app
import csv
import json
import os
from werkzeug.utils import secure_filename
from ..models import Device

upload_bp = Blueprint('upload', __name__)

def allowed_file(filename):
    """Verifica si el archivo tiene extensión permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'

def validate_csv_file(file_path):
    """Valida que el archivo CSV sea correcto"""
    try:
        # Intentar leer el CSV
        with open(file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            rows = list(csv_reader)
        
        # Verificar que tenga al menos una fila de datos (cabecera + 1 fila)
        if len(rows) < 2:
            return False, "El archivo CSV debe tener al menos una fila de datos además de la cabecera"
        
        return True, None
        
    except UnicodeDecodeError:
        return False, "Error de encoding. El archivo debe estar en UTF-8"
    except Exception as e:
        return False, f"Error al leer el archivo CSV: {str(e)}"

def process_csv_preview(file_path):
    """Procesa el CSV y retorna previsualización"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            rows = list(csv_reader)
        
        # Obtener cabecera
        headers = rows[0]
        
        # Obtener primeras 5 filas de datos (excluyendo cabecera)
        data_rows = rows[1:]
        preview_rows = data_rows[:5]
        
        # Convertir a JSON las primeras 5 filas
        json_preview = []
        for row in preview_rows:
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i] if i < len(row) else ""
            json_preview.append(row_dict)
        
        return {
            'headers': headers,
            'csv_preview': preview_rows,
            'json_preview': json_preview,
            'total_rows': len(data_rows)
        }
        
    except Exception as e:
        raise Exception(f"Error al procesar CSV: {str(e)}")

@upload_bp.route('/devices/<int:device_id>/upload', methods=['POST'])
def upload_csv(device_id):
    """Subir y procesar archivo CSV"""
    try:
        # Verificar que el dispositivo existe
        device = Device.get_by_id(device_id)
        if not device:
            return jsonify({'error': 'Dispositivo no encontrado'}), 404
        
        # Verificar que se envió un archivo
        if 'file' not in request.files:
            return jsonify({'error': 'No se envió ningún archivo'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Solo se permiten archivos CSV'}), 400
        
        # Guardar archivo temporalmente
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Validar archivo CSV
        is_valid, error_msg = validate_csv_file(file_path)
        if not is_valid:
            os.remove(file_path)  # Limpiar archivo temporal
            return jsonify({'error': error_msg}), 400
        
        # Procesar previsualización
        preview_data = process_csv_preview(file_path)
        
        # Limpiar archivo temporal
        os.remove(file_path)
        
        return jsonify({
            'message': 'Archivo procesado correctamente',
            'preview': preview_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@upload_bp.route('/devices/<int:device_id>/save', methods=['POST'])
def save_csv_data(device_id):
    """Guardar datos CSV procesados en el dispositivo"""
    try:
        # Verificar que el dispositivo existe
        device = Device.get_by_id(device_id)
        if not device:
            return jsonify({'error': 'Dispositivo no encontrado'}), 404
        
        data = request.get_json()
        
        if not data or 'csv_data' not in data:
            return jsonify({'error': 'Datos CSV requeridos'}), 400
        
        # Guardar datos CSV en el dispositivo
        device.update_csv_data(data['csv_data'])
        
        return jsonify({
            'message': 'Datos guardados correctamente',
            'device': device.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
