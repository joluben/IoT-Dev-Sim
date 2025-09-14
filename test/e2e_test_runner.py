#!/usr/bin/env python3
"""
Script automatizado para ejecutar test End-to-End completo
Aplicación de Gestión IoT - Device Simulator
"""

import requests
import json
import time
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

class E2ETestRunner:
    def __init__(self):
        self.base_url = "http://127.0.0.1:5000"
        self.api_url = f"{self.base_url}/api"
        self.test_results = []
        self.start_time = datetime.now()
        self.server_process = None
        
        # IDs para limpieza posterior
        self.connection_id = None
        self.device_ids = []
        self.project_id = None
        
    def log_step(self, step_num, name, status, details, observations="", duration=0):
        """Registra el resultado de un paso del test"""
        result = {
            'step': step_num,
            'name': name,
            'status': status,
            'details': details,
            'observations': observations,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_icon = "✅" if status == "ÉXITO" else "❌"
        print(f"\nPASO {step_num}: {name}")
        print(f"Estado: {status_icon} {status}")
        print(f"Detalles: {details}")
        if observations:
            print(f"Observaciones: {observations}")
        print(f"Tiempo: {duration:.2f}s")
        print("-" * 80)
    
    def start_server(self):
        """Inicia el servidor backend"""
        print("🚀 Iniciando servidor backend...")
        backend_dir = Path(__file__).parent / "backend"
        
        try:
            # Cambiar al directorio backend
            os.chdir(backend_dir)
            
            # Iniciar servidor en background
            self.server_process = subprocess.Popen(
                [sys.executable, "run.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Esperar a que el servidor esté listo
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    response = requests.get(f"{self.base_url}/api/health", timeout=2)
                    if response.status_code == 200:
                        print("✅ Servidor iniciado correctamente")
                        return True
                except requests.exceptions.RequestException:
                    pass
                
                time.sleep(1)
                print(f"Esperando servidor... ({attempt + 1}/{max_attempts})")
            
            print("❌ Error: Servidor no respondió en tiempo esperado")
            return False
            
        except Exception as e:
            print(f"❌ Error iniciando servidor: {e}")
            return False
    
    def stop_server(self):
        """Detiene el servidor backend"""
        if self.server_process:
            print("🛑 Deteniendo servidor...")
            self.server_process.terminate()
            self.server_process.wait()
    
    def make_request(self, method, endpoint, data=None, timeout=10):
        """Realiza petición HTTP con manejo de errores"""
        url = f"{self.api_url}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=timeout)
            elif method == "PUT":
                response = requests.put(url, json=data, timeout=timeout)
            elif method == "DELETE":
                response = requests.delete(url, timeout=timeout)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")
            
            return response
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error en petición {method} {url}: {e}")
            return None
    
    def step_1_create_mqtt_connection(self):
        """PASO 1: Crear Conexión MQTT"""
        step_start = time.time()
        
        connection_data = {
            "name": "conexión test",
            "type": "MQTT",
            "host": "broker.mqtt.cool",
            "port": 1883,
            "endpoint": "tes655",
            "auth_type": "NONE",
            "description": "Conexión de prueba para test E2E"
        }
        
        response = self.make_request("POST", "/connections", connection_data)
        
        if response and response.status_code == 201:
            result = response.json()
            self.connection_id = result.get('id')
            
            # Verificar que aparece en la lista
            list_response = self.make_request("GET", "/connections")
            if list_response and list_response.status_code == 200:
                connections = list_response.json()
                # Manejar respuesta paginada o lista directa
                items = connections.get('items', connections) if isinstance(connections, dict) else connections
                
                found = any(conn['name'] == "conexión test" for conn in items)
                
                if found:
                    duration = time.time() - step_start
                    self.log_step(1, "Crear Conexión MQTT", "ÉXITO", 
                                f"Conexión 'conexión test' creada con ID {self.connection_id}",
                                "Conexión MQTT configurada para broker.mqtt.cool:1883", duration)
                    return True
        
        duration = time.time() - step_start
        self.log_step(1, "Crear Conexión MQTT", "ERROR", 
                    f"Error creando conexión: {response.status_code if response else 'Sin respuesta'}",
                    "Verificar configuración del servidor", duration)
        return False
    
    def step_2_create_sensor_device(self):
        """PASO 2: Crear y Configurar Dispositivo Sensor"""
        step_start = time.time()
        
        # Crear dispositivo
        device_data = {
            "name": "sensor test",
            "description": "Dispositivo sensor para test E2E"
        }
        
        response = self.make_request("POST", "/devices", device_data)
        
        if response and response.status_code == 201:
            device = response.json()
            device_id = device.get('id')
            self.device_ids.append(device_id)
            
            # Configurar transmisión
            transmission_config = {
                "device_type": "Sensor",
                "transmission_frequency": 10,
                "transmission_enabled": False,  # Inicialmente deshabilitado
                "connection_id": self.connection_id,
                "include_device_id_in_payload": True
            }
            
            config_response = self.make_request("PUT", f"/devices/{device_id}/transmission-config", transmission_config)
            
            if config_response and config_response.status_code == 200:
                # Ejecutar transmisión manual
                transmit_response = self.make_request("POST", f"/devices/{device_id}/transmit-now/{self.connection_id}")
                
                duration = time.time() - step_start
                
                if transmit_response and transmit_response.status_code == 200:
                    self.log_step(2, "Crear y Configurar Dispositivo Sensor", "ÉXITO",
                                f"Dispositivo 'sensor test' creado con ID {device_id} y transmisión manual ejecutada",
                                "Dispositivo configurado como Sensor con frecuencia 10s", duration)
                    return True
                else:
                    self.log_step(2, "Crear y Configurar Dispositivo Sensor", "ÉXITO PARCIAL",
                                f"Dispositivo creado pero error en transmisión manual",
                                "Dispositivo funcional pero transmisión falló", duration)
                    return True
        
        duration = time.time() - step_start
        self.log_step(2, "Crear y Configurar Dispositivo Sensor", "ERROR",
                    f"Error creando dispositivo: {response.status_code if response else 'Sin respuesta'}",
                    "Verificar API de dispositivos", duration)
        return False
    
    def step_3_duplicate_devices(self):
        """PASO 3: Duplicar Dispositivos"""
        step_start = time.time()
        
        if not self.device_ids:
            duration = time.time() - step_start
            self.log_step(3, "Duplicar Dispositivos", "ERROR",
                        "No hay dispositivo base para duplicar",
                        "Paso 2 debe completarse exitosamente primero", duration)
            return False
        
        original_device_id = self.device_ids[0]
        duplicate_data = {"count": 4}
        
        response = self.make_request("POST", f"/devices/{original_device_id}/duplicate", duplicate_data)
        
        if response and response.status_code == 201:
            result = response.json()
            duplicates_created = result.get('duplicates_created', 0)
            duplicated_devices = result.get('duplicated_devices', [])
            
            # Agregar IDs de duplicados para limpieza posterior
            for device in duplicated_devices:
                self.device_ids.append(device.get('id'))
            
            duration = time.time() - step_start
            self.log_step(3, "Duplicar Dispositivos", "ÉXITO",
                        f"Creados {duplicates_created} duplicados del dispositivo original",
                        f"Total de dispositivos: {len(self.device_ids)} (1 original + {duplicates_created} duplicados)", duration)
            return True
        
        duration = time.time() - step_start
        self.log_step(3, "Duplicar Dispositivos", "ERROR",
                    f"Error duplicando dispositivo: {response.status_code if response else 'Sin respuesta'}",
                    "Verificar API de duplicación", duration)
        return False
    
    def step_4_create_project_and_transmission(self):
        """PASO 4: Crear Proyecto y Gestionar Transmisión"""
        step_start = time.time()
        
        # Crear proyecto
        project_data = {
            "name": "proyecto test",
            "description": "Proyecto de prueba para test E2E"
        }
        
        response = self.make_request("POST", "/projects", project_data)
        
        if response and response.status_code == 201:
            project = response.json()
            self.project_id = project.get('id')
            
            # Añadir todos los dispositivos al proyecto
            devices_added = 0
            for device_id in self.device_ids:
                add_response = self.make_request("POST", f"/projects/{self.project_id}/devices", 
                                               {"device_ids": [device_id]})
                if add_response and add_response.status_code == 200:
                    devices_added += 1
            
            # Iniciar transmisión del proyecto
            transmission_response = self.make_request("POST", f"/projects/{self.project_id}/start-transmission",
                                                    {"connection_id": self.connection_id})
            
            duration = time.time() - step_start
            
            if transmission_response and transmission_response.status_code == 200:
                self.log_step(4, "Crear Proyecto y Gestionar Transmisión", "ÉXITO",
                            f"Proyecto 'proyecto test' creado con {devices_added} dispositivos y transmisión iniciada",
                            f"Proyecto ID: {self.project_id}, usando conexión test", duration)
                return True
            else:
                self.log_step(4, "Crear Proyecto y Gestionar Transmisión", "ÉXITO PARCIAL",
                            f"Proyecto creado con {devices_added} dispositivos pero error iniciando transmisión",
                            "Proyecto funcional pero transmisión falló", duration)
                return True
        
        duration = time.time() - step_start
        self.log_step(4, "Crear Proyecto y Gestionar Transmisión", "ERROR",
                    f"Error creando proyecto: {response.status_code if response else 'Sin respuesta'}",
                    "Verificar API de proyectos", duration)
        return False
    
    def step_5_stop_and_clean_project(self):
        """PASO 5: Detener y Limpiar Proyecto"""
        step_start = time.time()
        
        if not self.project_id:
            duration = time.time() - step_start
            self.log_step(5, "Detener y Limpiar Proyecto", "OMITIDO",
                        "No hay proyecto para limpiar",
                        "Paso 4 no se completó exitosamente", duration)
            return True
        
        # Detener transmisión
        stop_response = self.make_request("POST", f"/projects/{self.project_id}/stop-transmission")
        
        # Esperar un momento para que se detenga
        time.sleep(2)
        
        # Eliminar proyecto
        delete_response = self.make_request("DELETE", f"/projects/{self.project_id}")
        
        duration = time.time() - step_start
        
        if delete_response and delete_response.status_code == 200:
            self.log_step(5, "Detener y Limpiar Proyecto", "ÉXITO",
                        f"Proyecto {self.project_id} detenido y eliminado correctamente",
                        "Transmisión detenida y proyecto removido del sistema", duration)
            self.project_id = None
            return True
        else:
            self.log_step(5, "Detener y Limpiar Proyecto", "ERROR",
                        f"Error eliminando proyecto: {delete_response.status_code if delete_response else 'Sin respuesta'}",
                        "Proyecto puede requerir limpieza manual", duration)
            return False
    
    def step_6_clean_devices(self):
        """PASO 6: Limpiar Dispositivos"""
        step_start = time.time()
        
        devices_deleted = 0
        errors = 0
        
        for device_id in self.device_ids:
            response = self.make_request("DELETE", f"/devices/{device_id}")
            if response and response.status_code == 200:
                devices_deleted += 1
            else:
                errors += 1
        
        duration = time.time() - step_start
        
        if errors == 0:
            self.log_step(6, "Limpiar Dispositivos", "ÉXITO",
                        f"Eliminados {devices_deleted} dispositivos de prueba",
                        "Todos los dispositivos de test removidos del sistema", duration)
            self.device_ids = []
            return True
        else:
            self.log_step(6, "Limpiar Dispositivos", "ÉXITO PARCIAL",
                        f"Eliminados {devices_deleted} dispositivos, {errors} errores",
                        "Algunos dispositivos pueden requerir limpieza manual", duration)
            return False
    
    def step_7_clean_connection(self):
        """PASO 7: Limpiar Conexión"""
        step_start = time.time()
        
        if not self.connection_id:
            duration = time.time() - step_start
            self.log_step(7, "Limpiar Conexión", "OMITIDO",
                        "No hay conexión para limpiar",
                        "Paso 1 no se completó exitosamente", duration)
            return True
        
        response = self.make_request("DELETE", f"/connections/{self.connection_id}")
        
        duration = time.time() - step_start
        
        if response and response.status_code == 200:
            self.log_step(7, "Limpiar Conexión", "ÉXITO",
                        f"Conexión {self.connection_id} eliminada correctamente",
                        "Conexión de prueba removida del sistema", duration)
            self.connection_id = None
            return True
        else:
            self.log_step(7, "Limpiar Conexión", "ERROR",
                        f"Error eliminando conexión: {response.status_code if response else 'Sin respuesta'}",
                        "Conexión puede requerir limpieza manual", duration)
            return False
    
    def step_8_generate_final_report(self):
        """PASO 8: Generar Reporte Final"""
        step_start = time.time()
        
        total_duration = time.time() - self.start_time.timestamp()
        successful_steps = sum(1 for result in self.test_results if result['status'] == 'ÉXITO')
        total_steps = len(self.test_results)
        
        # Generar reporte
        report = {
            'test_summary': {
                'start_time': self.start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'total_duration': f"{total_duration:.2f}s",
                'successful_steps': successful_steps,
                'total_steps': total_steps,
                'success_rate': f"{(successful_steps/total_steps)*100:.1f}%" if total_steps > 0 else "0%"
            },
            'steps': self.test_results,
            'recommendations': []
        }
        
        # Agregar recomendaciones basadas en resultados
        if successful_steps == total_steps:
            report['recommendations'].append("✅ Test completado exitosamente - Sistema funcionando correctamente")
        else:
            report['recommendations'].append("⚠️ Algunos pasos fallaron - Revisar logs para identificar problemas")
            
        if any(result['status'] == 'ERROR' for result in self.test_results):
            report['recommendations'].append("🔍 Errores detectados - Revisar configuración de API y base de datos")
        
        # Guardar reporte
        report_file = Path(__file__).parent / "e2e_test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        duration = time.time() - step_start
        self.log_step(8, "Generar Reporte Final", "ÉXITO",
                    f"Reporte generado: {successful_steps}/{total_steps} pasos exitosos",
                    f"Reporte guardado en {report_file}", duration)
        
        return report
    
    def run_complete_test(self):
        """Ejecuta el test end-to-end completo"""
        print("=" * 80)
        print("🧪 INICIANDO TEST END-TO-END - Aplicación de Gestión IoT")
        print("=" * 80)
        
        # Iniciar servidor
        if not self.start_server():
            print("❌ Error crítico: No se pudo iniciar el servidor")
            return False
        
        try:
            # Ejecutar todos los pasos
            steps = [
                self.step_1_create_mqtt_connection,
                self.step_2_create_sensor_device,
                self.step_3_duplicate_devices,
                self.step_4_create_project_and_transmission,
                self.step_5_stop_and_clean_project,
                self.step_6_clean_devices,
                self.step_7_clean_connection,
                self.step_8_generate_final_report
            ]
            
            for step_func in steps:
                try:
                    step_func()
                except Exception as e:
                    print(f"❌ Error inesperado en {step_func.__name__}: {e}")
                    
                # Pequeña pausa entre pasos
                time.sleep(1)
            
            # Mostrar resumen final
            print("\n" + "=" * 80)
            print("📊 RESUMEN FINAL DEL TEST")
            print("=" * 80)
            
            successful = sum(1 for r in self.test_results if r['status'] == 'ÉXITO')
            total = len(self.test_results)
            
            print(f"✅ Pasos exitosos: {successful}/{total}")
            print(f"⏱️ Tiempo total: {time.time() - self.start_time.timestamp():.2f}s")
            print(f"📈 Tasa de éxito: {(successful/total)*100:.1f}%")
            
            if successful == total:
                print("🎉 ¡TEST COMPLETADO EXITOSAMENTE!")
            else:
                print("⚠️ Test completado con errores - Revisar detalles arriba")
            
            return successful == total
            
        finally:
            # Asegurar limpieza del servidor
            self.stop_server()

if __name__ == "__main__":
    runner = E2ETestRunner()
    success = runner.run_complete_test()
    sys.exit(0 if success else 1)
