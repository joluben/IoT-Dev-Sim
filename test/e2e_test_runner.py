#!/usr/bin/env python3
"""
E2E Test Runner for DevSim
Runs comprehensive end-to-end tests using Selenium WebDriver
"""

import os
import sys
import time
import json
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DevSimE2ETest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Initialize Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 15)
            logger.info("Chrome WebDriver initialized successfully")
        except WebDriverException as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise
            
    def teardown_driver(self):
        """Clean up WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")
            
    def test_application_loads(self):
        """Test that the main application loads without errors"""
        logger.info("Testing application load...")
        
        try:
            self.driver.get(self.base_url)
            
            # Wait for the main navigation to load
            nav_element = self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "nav-btn"))
            )
            
            # Check page title
            title = self.driver.title
            assert "DevSim" in title or "Device" in title, f"Expected 'DevSim' or 'Device' in title, got: {title}"
            
            # Check that navigation buttons are present
            nav_buttons = self.driver.find_elements(By.CLASS_NAME, "nav-btn")
            assert len(nav_buttons) >= 3, f"Expected at least 3 nav buttons, found: {len(nav_buttons)}"
            
            logger.info("✓ Application loads successfully")
            return True
            
        except TimeoutException:
            logger.error("✗ Application failed to load within timeout")
            # Take screenshot for debugging
            if self.driver:
                self.driver.save_screenshot("app_load_failure.png")
            return False
        except AssertionError as e:
            logger.error(f"✗ Application load test failed: {e}")
            return False
            
    def test_devices_page(self):
        """Test devices page functionality"""
        logger.info("Testing devices page...")
        
        try:
            # Navigate to devices page
            devices_nav = self.wait.until(
                EC.element_to_be_clickable((By.ID, "nav-devices"))
            )
            devices_nav.click()
            
            # Wait for devices grid to load or loading message
            try:
                devices_grid = self.wait.until(
                    EC.presence_of_element_located((By.ID, "devices-grid"))
                )
            except TimeoutException:
                # Check if there's a loading message
                try:
                    loading_element = self.driver.find_element(By.ID, "devices-loading")
                    if loading_element and loading_element.is_displayed():
                        logger.info("Devices are loading...")
                        # Wait a bit more for loading to complete
                        time.sleep(3)
                        devices_grid = self.driver.find_element(By.ID, "devices-grid")
                    else:
                        raise
                except:
                    raise
            
            # Check if devices are displayed or empty state message
            grid_text = devices_grid.text
            assert grid_text is not None, "Devices grid should have content"
            
            # Check that we're not stuck on "Cargando dispositivos..."
            if "Cargando dispositivos" in grid_text:
                logger.warning("Devices still loading after timeout - this may indicate an API issue")
                return False
            
            logger.info("✓ Devices page loads successfully")
            return True
            
        except TimeoutException:
            logger.error("✗ Devices page failed to load")
            if self.driver:
                self.driver.save_screenshot("devices_page_failure.png")
            return False
        except AssertionError as e:
            logger.error(f"✗ Devices page test failed: {e}")
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
