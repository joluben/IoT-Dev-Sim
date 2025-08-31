const puppeteer = require('puppeteer');

async function runE2ETest() {
    const browser = await puppeteer.launch({ headless: false, slowMo: 500 });
    const page = await browser.newPage();
    
    try {
        console.log('🚀 Iniciando prueba E2E...');
        
        // 1. Navegar a la aplicación
        await page.goto('http://127.0.0.1:5000');
        await page.waitForSelector('#nav-projects');
        
        // 2. Probar GET /api/projects desde el navegador
        console.log('📡 Probando GET /api/projects...');
        const projectsResponse = await page.evaluate(async () => {
            try {
                const response = await fetch('/api/projects');
                return {
                    status: response.status,
                    ok: response.ok,
                    text: await response.text()
                };
            } catch (error) {
                return { error: error.message };
            }
        });
        console.log('Respuesta GET /api/projects:', projectsResponse);
        
        // 3. Ir a la sección de proyectos
        await page.click('#nav-projects');
        await page.waitForSelector('#projects-grid', { timeout: 5000 });
        await page.screenshot({ path: 'screenshot_projects_list.png' });
        
        // 4. Intentar crear un proyecto
        console.log('📁 Creando proyecto...');
        await page.click('#btn-new-project');
        await page.waitForSelector('#project-name');
        
        await page.type('#project-name', 'Proyecto E2E Test');
        await page.type('#project-description', 'Creado por prueba automatizada');
        
        await page.screenshot({ path: 'screenshot_project_form.png' });
        
        // 5. Enviar formulario y capturar respuesta
        const createResponse = await page.evaluate(async () => {
            try {
                const response = await fetch('/api/projects', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: 'Proyecto E2E Test',
                        description: 'Creado por prueba automatizada'
                    })
                });
                return {
                    status: response.status,
                    ok: response.ok,
                    text: await response.text()
                };
            } catch (error) {
                return { error: error.message };
            }
        });
        console.log('Respuesta POST /api/projects:', createResponse);
        
        await page.click('#project-form button[type="submit"]');
        await new Promise(resolve => setTimeout(resolve, 2000));
        await page.screenshot({ path: 'screenshot_after_submit.png' });
        
        // 6. Verificar si hay dispositivos para asignar
        console.log('📱 Verificando dispositivos...');
        const devicesResponse = await page.evaluate(async () => {
            try {
                const response = await fetch('/api/devices');
                return {
                    status: response.status,
                    ok: response.ok,
                    data: JSON.parse(await response.text())
                };
            } catch (error) {
                return { error: error.message };
            }
        });
        console.log('Dispositivos disponibles:', devicesResponse);
        
        // 7. Crear un dispositivo si no hay ninguno
        if (devicesResponse.ok && devicesResponse.data.length === 0) {
            console.log('🔧 Creando dispositivo...');
            await page.click('#nav-devices');
            await page.waitForSelector('#btn-new-device');
            await page.click('#btn-new-device');
            
            await page.waitForSelector('#device-name');
            await page.type('#device-name', 'Device E2E Test');
            await page.type('#device-description', 'Dispositivo para prueba E2E');
            
            await page.click('#create-device-form button[type="submit"]');
            await new Promise(resolve => setTimeout(resolve, 2000));
            await page.screenshot({ path: 'screenshot_device_created.png' });
        }
        
        console.log('✅ Prueba E2E completada');
        
    } catch (error) {
        console.error('❌ Error en prueba E2E:', error);
        await page.screenshot({ path: 'screenshot_error.png' });
    } finally {
        await browser.close();
    }
}

runE2ETest();
