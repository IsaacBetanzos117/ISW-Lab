from django.contrib import messages
from django.shortcuts import redirect
import shutil
import subprocess
from django.http import HttpResponse, Http404
from django.utils import timezone
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from config import settings

# Create your views here.

# Esta clase restringe el acceso solo a Administradores para el respaldo de la BD
class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    
    # Este metodo verifica que el usuario sea superusuario o pertenezca al grupo Administrador.
    def test_func(self):
        is_admin = self.request.user.groups.filter(name='Administrador').exists()
        
        return self.request.user.is_superuser or is_admin

# Esta clase muestra el panel con las opciones de Respaldo y Restauración.
class DatabaseMaintenanceView(AdminRequiredMixin, TemplateView):
    template_name = 'backups/db_maintenance.html'

    # Este metodo protege la carga de la plantilla contra errores 404 o fallos internos 500.
    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Http404:
            messages.warning(request, "El recurso de mantenimiento solicitado no fue encontrado (Error 404).")
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f"Ocurrió un error interno al cargar el panel de mantenimiento (Error 500): {str(e)}")
            
            return redirect('dashboard')

# Esta clase genera el volcado .sql en memoria y lo envía como descarga al navegador.
class DatabaseBackupDownloadView(AdminRequiredMixin, View):

    # Este metodo evita error 405 si alguien intenta entrar escribiendo la URL directa (GET) en lugar de usar el botón (POST).
    def get(self, request, *args, **kwargs):
        messages.warning(request, "Usa el botón de descarga para generar el respaldo.")
        
        return redirect('db_maintenance')
    
    # Este metodo hace el respaldo de la BD.
    def post(self, request, *args, **kwargs):
        try:
            db = settings.DATABASES['default'] # Obtiene la configuración de la BD
            
            # Busca el comando mysqldump dentro de las carpetas registradas en la variable de entorno PATH del SO y apunta al del directorio de linux donde XAMPP instala sus binarios
            mysqldump_bin = shutil.which('mysqldump') or '/opt/lampp/bin/mysqldump'
            
            cmd = [
                mysqldump_bin,
                f"--host={db.get('HOST') or '127.0.0.1'}", # Obtiene el servidor.
                f"--port={str(db.get('PORT') or '3306')}", # Obtiene el puerto.
                f"--user={db.get('USER', 'root')}", # Obtiene el usuario.
            ]
            
            # Comprueba si existe una contraseña
            if db.get('PASSWORD'):
                cmd.append(f"--password={db['PASSWORD']}")
            
            # Excluye sesiones activas y logs del admin para no cerrar la sesión actual ni inflar el respaldo
            ignored_tables = ['django_session', 'django_admin_log']
            for table in ignored_tables:
                cmd.append(f"--ignore-table={db['NAME']}.{table}")
            
            cmd.append(db['NAME'])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True) # subprocess lanza comando de consola
            timestamp = timezone.localtime().strftime('%Y%m%d_%H%M%S') # Obtiene la fecha y hora local actual formateada para el nombre del archivo.
            filename = f"respaldo_{db['NAME']}_{timestamp}.sql" # Nombra el archivo .sql
            response = HttpResponse(result.stdout, content_type='application/sql') # captura todo el texto SQL como string, content_type='application/sql' le avisa al navegador qué tipo de datos está recibiendo
            response['Content-Disposition'] = f'attachment; filename="{filename}"' # attachment indica que se trate el recurso como un archivo adjunto y activar la descarga en lugar de mostrarlo en pantalla.
            
            return response
        except Http404:
            messages.warning(request, "No se encontró el recurso solicitado para generar el respaldo (Error 404).")
        except FileNotFoundError:
            messages.error(request, "No se encontró el comando 'mysqldump' en el servidor.")
        except subprocess.CalledProcessError as e:
            messages.error(request, f"Error al generar el respaldo: {e.stderr}")
        except Exception as e:
            messages.error(request, f"Ocurrió un error interno inesperado al respaldar la BD (Error 500): {str(e)}")
        
        return redirect('db_maintenance')

# Esta clase recibe el archivo .sql y restaura la BD.
class DatabaseRestoreView(AdminRequiredMixin, View):

    # Este metodo evita error 405 si alguien intenta entrar escribiendo la URL directa (GET) en lugar de enviar el formulario (POST).
    def get(self, request, *args, **kwargs):
        messages.warning(request, "Selecciona un archivo .sql desde el formulario para restaurar.")
        
        return redirect('db_maintenance')
    
    # Este metodo es para restaurar la BD.
    def post(self, request, *args, **kwargs):
        try:
            sql_file = request.FILES.get('backup_file') # Obtiene un archivo subido a través de un formulario web.
            
            # Valida que se haya subido un archivo y que tenga extensión .sql antes de procesarlo.
            if not sql_file or not sql_file.name.endswith('.sql'):
                messages.error(request, "Por favor selecciona un archivo válido con extensión .sql.")
                
                return redirect('db_maintenance')
            
            db = settings.DATABASES['default'] # Obtiene la configuración de la BD
            mysql_bin = shutil.which('mysql') or '/opt/lampp/bin/mysql' # Ruta exacta del ejecutable de MySQL en el sistema o asume que está en la carpeta de XAMPP de linux.
            
            cmd = [
                mysql_bin,
                f"--host={db.get('HOST') or '127.0.0.1'}", # Obtiene el servidor.
                f"--port={str(db.get('PORT') or '3306')}", # Obtiene el puerto.
                f"--user={db.get('USER', 'root')}", # Obtiene el usuario.
            ]
            
            # Comprueba si existe una contraseña
            if db.get('PASSWORD'):
                cmd.append(f"--password={db['PASSWORD']}")
            
            cmd.append(db['NAME'])

            sql_content = sql_file.read() # Lee el .sql
            subprocess.run(cmd, input=sql_content, capture_output=True, check=True) # Lanza comando de consola para restaurar.
            messages.success(request, f"Base de datos restaurada exitosamente desde '{sql_file.name}'.")
        except Http404:
            messages.warning(request, "El recurso solicitado para la restauración no existe (Error 404).")
        except FileNotFoundError:
            messages.error(request, "No se encontró el comando 'mysql' en el servidor.")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8', errors='ignore') # Convierte los bytes de error capturados por el subproceso en una cadena de texto legible
            messages.error(request, f"Error al restaurar la base de datos: {error_msg}")
        except Exception as e:
            messages.error(request, f"Ocurrió un error interno inesperado al restaurar la BD (Error 500): {str(e)}")
        
        return redirect('db_maintenance')