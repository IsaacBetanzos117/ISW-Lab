from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
import pandas as pd # Pandas para manipulación de datos y exportación a Excel
from grupos.models import Academic_group
from .physics_engine import SimulationEngine
from .models import Simulation_configuration, Simulation_history
from .forms import SimulationConfigurationForm
import io # io sirve para gestionar operaciones de entrada y salida, permitiendo leer y escribir flujos de datos ya sea en archivos del disco
from django.views.generic import TemplateView
import re # Expresiones regulares para extraer base64 de HTML
from PIL import Image # Pillow para manipulación de imágenes
import base64 # Base64 para decodificar imágenes embebidas en HTML
import threading # Para manejar la ejecución de tareas en segundo plano
from django.core.mail import EmailMultiAlternatives # Para enviar correos electrónicos
from django.conf import settings # Para acceder a la configuración de Django, como el correo electrónico predeterminado
from django.template.loader import render_to_string # Para renderizar plantillas HTML a cadenas de texto
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# FN.3: Gestión de Parámetros de Simulación (Crear)
# Esta clase permite al estudiante o docente crear una nueva configuración de simulación desde un formulario vacío.
class SimulationConfigurationCreateView(LoginRequiredMixin, CreateView):
    model = Simulation_configuration
    form_class = SimulationConfigurationForm
    template_name = 'simulator/parameters_crud/simulation_configuration_form.html'
    success_url = reverse_lazy('config_list') 
    
    # Contextualiza el título y el texto del botón en la plantilla HTML
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear configuración de simulación'
        context['button_text'] = 'Guardar configuración'
        context['cancel_url'] = reverse('config_list') # ruta de cancelación fija para cuando es un nuevo registro
        return context
    
    # Valida el formulario y asigna automáticamente el usuario activo como autor antes de guardar en la base de datos
    def form_valid(self, form):
        try:
            # Asigna automáticamente el usuario activo antes de guardar en la base de datos
            form.instance.author = self.request.user
            group_id = self.request.session.get('ultimo_grupo_id')
            
            if group_id:
                group_obj = Academic_group.objects.get(pk=group_id)
                form.instance.academic_group = group_obj
            
            response = super().form_valid(form)
            messages.success(self.request, 'Los parámetros de simulación se han guardado correctamente.')
            
            return response
        except Exception as e:
            messages.error(self.request, f'Error al guardar los parámetros de simulación: {str(e)}')
            
            return super().form_invalid(form)

# FN.3 Actualizar configuración
# Esta clase permite a los usuarios modificar los parámetros físicos de una simulación.
class SimulationConfigurationUpdateView(LoginRequiredMixin, UpdateView):
    model = Simulation_configuration
    form_class = SimulationConfigurationForm
    template_name = 'simulator/parameters_crud/simulation_configuration_form.html'
    success_url = reverse_lazy('config_list')
    
    # Contextualiza el título y el texto del botón en la plantilla HTML
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Actualizar configuración de simulación'
        context['button_text'] = 'Actualizar configuración'
        
        # Captura 'next' ya sea por GET (al entrar) o por POST (si el formulario se recarga por error)
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if not next_url:
            next_url = reverse('config_list') # Si vino de la lista normal, regresa a la lista
        context['cancel_url'] = next_url
        
        context['cancel_url'] = next_url
        context['next_url'] = next_url  # Pasamos la variable para el input oculto
        
        return context
    
    # Restringe la consulta para que el usuario solo pueda editar sus propios experimentos
    def get_queryset(self):
        group_id = self.request.session.get('ultimo_grupo_id')
        queryset = Simulation_configuration.objects.filter(author=self.request.user) # Filtra por usuario
        
        # Blinda el acceso: solo permite editar/eliminar si pertenece a la clase actual
        if group_id:
            queryset = queryset.filter(academic_group_id=group_id)
            
        return queryset
    
    # Maneja el acceso no autorizado: Si intenta editar un registro ajeno o inexistente, retorna al historial
    def get(self, request, *args, **kwargs):
        # Maneja el acceso no autorizado: Si intenta editar un registro ajeno o inexistente, retorna al historial
        try:
            return super().get(request, *args, **kwargs)
        except Http404:
            messages.warning(request, "La configuración que intentas editar no existe o no tienes permiso para verla.")
            return redirect('simulation_history')
    
    # Valida y guarda los cambios, notificando al usuario del éxito o fallo
    def form_valid(self, form):
        # Valida y guarda los cambios, notificando al usuario del éxito o fallo
        try:
            form.instance.pk = None # Al poner el primary key en None, hace un INSERT en lugar de un UPDATE
            group_id = self.request.session.get('ultimo_grupo_id')
            
            if group_id:
                group_obj = Academic_group.objects.get(pk=group_id)
                form.instance.academic_group = group_obj
            
            super().form_valid(form)
            messages.success(self.request, 'Los parámetros de simulación se han actualizado correctamente.')
            next_url = self.request.POST.get('next')
            
            # Si en la URL de origen existe la ruta 'simular', sabemos que viene del botón amarillo, funciona asi "¿Existe un enlace de retorno Y además la palabra 'simular' forma parte del texto '/simular/x/'?"
            if next_url and 'simular' in next_url:
                return redirect('process_simulation', pk=self.object.pk)# Dispara ProcessSimulationView con el ID del nuevo
            else:
                return redirect('config_list') # Si viene de cualquier otro lado, lo regresa a su tabla de parámetros
            
        except Exception as e:
            messages.error(self.request, f'Error al actualizar los parámetros de simulación: {str(e)}')
            return super().form_invalid(form)


# FN.3 Eliminar configuración
# Esta clase permite al usuario borrar de forma definitiva una configuracion de parametros para una simulacion.
class SimulationConfigurationDeleteView(LoginRequiredMixin, DeleteView):
    model = Simulation_configuration
    template_name = 'simulator/parameters_crud/simulation_configuration_confirm_delete.html'
    success_url = reverse_lazy('simulation_history')
    
    # Esta función asegura que el usuario solo pueda eliminar configuraciones que le pertenecen, evitando errores de acceso no autorizado.
    def get_queryset(self):
        group_id = self.request.session.get('ultimo_grupo_id')
        queryset = Simulation_configuration.objects.filter(author=self.request.user) # Filtra por el usuario
        
        # Solo permite editar/eliminar si pertenece a la clase actual
        if group_id:
            queryset = queryset.filter(academic_group_id=group_id)
            
        return queryset
    
    # Maneja el caso en que la configuración ya fue borrada o pertenece a otra cuenta, redirigiendo al historial con un mensaje de advertencia.
    def get(self, request, *args, **kwargs):
        # Redirige de forma segura si la configuración ya fue borrada o pertenece a otra cuenta
        try:
            return super().get(request, *args, **kwargs)
        except Http404:
            messages.warning(request, "La configuración que intentas eliminar no existe o ya fue borrada.")
            return redirect('simulation_history')
    
    # Esta funcion notifica si se guardo correctamente o hay un error
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, 'La configuración de simulación se ha eliminado correctamente.')
            return response
        except Exception as e:
            messages.error(self.request, f'Error al eliminar la configuración de simulación: {str(e)}')
            return super().form_invalid(form)


# FN.3: Catálogo de Parámetros de Simulación del Usuario
# Esta vista sirve para mostrar los parametros creados para una simulacion
class SimulationConfigListView(LoginRequiredMixin, ListView):
    model = Simulation_configuration
    template_name = 'simulator/parameters_crud/simulation_configuration_list.html'
    context_object_name = 'configurations'
    
    # Permite ver los registros que según el usuario que está haciendo la petición
    def get_queryset(self):
        group_id = self.request.session.get('ultimo_grupo_id') # Filtra por autor
        queryset = Simulation_configuration.objects.filter(author=self.request.user)
        
        # Si hay un grupo activo en la sesión, filtra por ese grupo
        if group_id:
            queryset = queryset.filter(academic_group_id=group_id)
        
        morphological_type = self.request.GET.get('morfologia')
        
        if morphological_type:
            queryset = queryset.filter(morphological_type=morphological_type)
        
        return queryset.order_by('-saved_date')
    
    # Sirve para pasar variables adicionales a las plantillas (templates)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Mis parámetros de simulación'
        group_id = self.request.session.get('ultimo_grupo_id') # Recupera el ID del grupo de la sesión del usuario, si existe. Esto permite recordar la última clase visitada y regresar a ella fácilmente.
        
        # Busca si el usuario actual está inscrito como estudiante en algún grupo
        # .first() tomará el primer grupo que encuentre (ideal si solo está en 1 clase)
        if group_id:
            # Si hay un ID guardado, cargamos ese grupo exacto
            context['user_group'] = Academic_group.objects.filter(pk=group_id).first()
        
        context['morphological_types'] = [
            'Esférica',
            'Elíptica',
            'Bipolar',
            'Multipolar',
            'Proto-planetaria'
        ]
        
        context['current_morphology'] = self.request.GET.get('morfologia', '')
        
        return context


# FN.4 y FN.11. Ejecutar simulación, renderizado 3D y notificación
class ProcessSimulationView(LoginRequiredMixin, View):
    
    def get(self, request, pk):
        # Ejecuta la lógica matemática de la simulación
        configuration_obj = get_object_or_404(Simulation_configuration, pk=pk, author=request.user)
        engine = SimulationEngine(configuration_obj)
        simulation_result = engine.execute_simulation()
        active_group_id = request.session.get('ultimo_grupo_id')
        print(f"Grupo activo ID: {active_group_id}")
        
        # Guarda el historial en la DB
        history_record = Simulation_history.objects.create(
            configuration=configuration_obj,
            stability_status=simulation_result['status'],
            execution_time_sec=simulation_result['execution_time'],
            student_notes=simulation_result['notes']
        )
        
        # Instancia la clase notificadora con los datos actuales
        notifier = AsyncTeacherNotification(
            request.user,
            configuration_obj.configuration_name,
            simulation_result['status'],
            simulation_result['execution_time'],
            simulation_result,
            active_group_id
        )

        
        threading.Thread(target=notifier.send).start() # Lanza el método 'send' de la clase en un hilo de segundo plano
        # notifier.send()
        messages.success(request, '¡Simulación calculada! Tu docente ha sido notificado con los documentos adjuntos.') # Muestra el mensaje de éxito web
        
        # Inicializa el diccionario de contexto que transportará los datos desde Python hacia la plantilla HTML
        context = {
            'history': history_record,
            'configuration': configuration_obj,
            'plot_html': simulation_result['plot_html'],
            'graphs_2d': simulation_result.get('graphs_2d'),
            'title': 'Simulation results'
        }

        return render(request, 'simulator/simulation_crud/simulation_result.html', context) # Combina la petición original, la ruta de la plantilla HTML y el contexto para devolver una respuesta

# FN.4: Historial de Simulaciones y Depuración Automática (Leer)
# Esta clase muestra la bitácora privada con todos los experimentos iterados por el usuario activo.
class SimulationHistoryListView(LoginRequiredMixin, ListView):
    model = Simulation_history
    template_name = 'simulator/simulation_crud/simulation_history_list.html'
    context_object_name = 'history_records'
    
    # Permite ver los registros que según el usuario que está haciendo la petición
    def get_queryset(self):
        group_id = self.request.session.get('ultimo_grupo_id')
        
        # Filtra por autor
        queryset = Simulation_history.objects.filter(configuration__author=self.request.user)
        
        # Filtra por el grupo entrando y la configuración
        if group_id:
            queryset = queryset.filter(configuration__academic_group_id=group_id)
            
        # Filtro dinámico por estado de ejecución (estable / divergente)
        status = self.request.GET.get('estado')
        if status in ['estable', 'divergente']:
            queryset = queryset.filter(stability_status=status) 
            
        # Ordenamiento dinámico por fecha
        order = self.request.GET.get('orden', 'desc') # Por defecto descendente (más recientes)
        if order == 'asc':
            queryset = queryset.order_by('calculated_at') # Más antiguos primero
        else:
            queryset = queryset.order_by('-calculated_at') # Más recientes primero
        
        return queryset
    
    # Sirve para pasar variables adicionales a las plantillas
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Mi historial de simulaciones'
        group_id = self.request.session.get('ultimo_grupo_id')
        
        # Busca el grupo del estudiante para el botón de regreso
        if group_id:
            context['my_group'] = Academic_group.objects.filter(pk=group_id).first()
        
        context['current_status'] = self.request.GET.get('estado', '')
        context['current_order'] = self.request.GET.get('orden', 'desc')
        
        return context


# FN4. Busca el historial, pide al "motor" que vuelva a dibujar la gráfica, y manda a la pantalla de resultados sin alterar la BD
class SimulationHistoryDetailView(LoginRequiredMixin, View):
    
    # Esta funcion hace la simulacion y muestra si hubo un error o no.
    def get(self, request, pk):
        history_record = get_object_or_404(Simulation_history, pk=pk, configuration__author=request.user)
        engine = SimulationEngine(history_record.configuration)# Instancia el motor con la receta histórica        
        simulation_result = engine.execute_simulation()# Usa el método principal
        plot_html = simulation_result.get('plot_html')# Extrae el gráfico de forma segura
        
        # Si por alguna razón matemática la regeneración falla, mostra el error
        if simulation_result.get('status') == 'divergente':
             history_record.student_notes = f"Error al regenerar: {simulation_result.get('notes')}"
        
        # Prepara el contexto para enviarlo a la plantilla HTML que mostrará el resultado de la simulación
        context = {
            'history': history_record,
            'configuration': history_record.configuration,
            'plot_html': plot_html,
            'graphs_2d': simulation_result.get('graphs_2d'), # NUEVO: Inyecta las gráficas bidimensionales (FN.8) también en la vista del historial
            'title': 'Render Histórico 3D y 2D'
        }
        
        return render(request, 'simulator/simulation_crud/simulation_result.html', context)

# Esta clase (vista) es para descargar la configuracion de los parametros en excel y en pdf, jpg y png la grafica 3d de la NPe + Graficas 2D
class SimulationDownloadView(LoginRequiredMixin, View):
    
    # Funcion que prepara los datos de la simulacion para la exportacion.
    def get(self, request, pk, file_type):
        history_record = get_object_or_404(Simulation_history, pk=pk, configuration__author=request.user) # Recupera la configuración del historial
        engine = SimulationEngine(history_record.configuration) # Instanciamos el motor y recalculamos los datos numéricos al vuelo
        simulation_result = engine.execute_simulation()
        
        # Si la matemática falló, no hay nada que descargar
        if simulation_result.get('status') == 'divergente':
            messages.error(request, "No se pueden exportar archivos de una simulación inestable/divergente.")
            return redirect('simulation_history')
        
        if file_type == 'xlsx': # Descarga de EXCEL (.xlsx)
            df_data = simulation_result['dataframe']
            df_params = simulation_result['dataframe_params']
            df_evolution = simulation_result['dataframe_evolution']
            buffer = io.BytesIO() # io sirve para gestionar operaciones de entrada y salida, permitiendo leer y escribir flujos de datos (streams) ya sea en archivos del disco
            
            # ExcelWriter para guardar dos pestañas en el mismo archivo
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer: # with gestion el flujo de escritura de un archivo de Excel
                df_params.to_excel(writer, sheet_name='Configuración', index=False) # El nombre, el tipo morfológico y los parámetros físicos de arranque (Radio, Densidad, Temperatura y Velocidad).
                df_evolution.to_excel(writer, sheet_name='Evolución 2D', index=False) # Muestra cómo cambiaron las propiedades físicas del gas paso a paso (en saltos de 100 años) desde el inicio hasta el final de la simulación, tiempo (Años), Radio de expansión (pc), Temperatura (K), Densidad Max (%), Velocidad del viento (km/s) y Pérdida masa (M☉/yr).
                df_data.to_excel(writer, sheet_name='Datos crudos 3D', index=False) # Cada fila representa un punto en el espacio y cuánta materia estelar hay ahí.
            
            buffer.seek(0) # Regresa el cursor al inicio
            response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="datos_simulacion_{pk}.xlsx"'
            
            return response
            
        elif file_type in ['png', 'jpg', 'pdf']: # Descarga de imágenes y PDF (Stitching 3D + 2D)
            # Extrae el objeto crudo de Plotly y lo convierte a imagen
            img_3d = Matplotlib3DRenderer.render(
                simulation_result['dataframe'],
                history_record.configuration.configuration_name
            )
            
            # Obtiene las gráficas 2D Logarítmicas de Matplotlib
            graphs_log = simulation_result['graphs_2d']['log']
            images_2d = []
            
            # Extrae el código base64 del HTML generado usando Expresiones Regulares
            for key in ['temp', 'density', 'velocity', 'radius', 'mass']:
                html_tag = graphs_log[key]
                # Busca el texto que está entre 'base64,' y la comilla de cierre '"'
                b64_str = re.search(r'base64,(.*?)"', html_tag).group(1)
                img_bytes = base64.b64decode(b64_str)
                img_2d = Image.open(io.BytesIO(img_bytes))
                images_2d.append(img_2d)
                
            # Calcula el tamaño del Lienzo Final (Costura de imágenes)
            # Altura = (Alto del 3D) + (Suma de los altos de todas las gráficas 2D)
            total_height = img_3d.height + sum(img.height for img in images_2d)
            max_width = 800 # Ancho estandarizado para coincidir con la imagen 3D
            
            # Crea un lienzo nuevo con color oscuro (RGB: 17, 17, 17 es #111111) para mantener el tema de la plataforma
            canvas = Image.new('RGB', (max_width, total_height), (17, 17, 17))
            
            # Pega las imágenes como si fuera un rompecabezas vertical
            canvas.paste(img_3d, (0, 0)) # El modelo 3D va en la parte superior
            y_offset = img_3d.height
            
            for img in images_2d:
                canvas.paste(img, (0, y_offset)) # Pega la siguiente gráfica justo debajo de la anterior
                y_offset += img.height
                
            # Guarda el lienzo gigante en el formato solicitado
            buffer = io.BytesIO()
            
            # Plotly reconoce 'jpeg', pero Pillow usa 'JPEG'. Mapea el formato correctamente.
            # Pillow soporta guardar este lienzo de imágenes directamente como PDF de forma nativa.
            export_format = 'JPEG' if file_type == 'jpg' else file_type.upper()
            canvas.save(buffer, format=export_format)
            buffer.seek(0)
            
            # Respuesta HTTP con el tipo de contenido adecuado
            content_types = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'pdf': 'application/pdf'
            }
            
            response = HttpResponse(buffer, content_type=content_types[file_type])
            response['Content-Disposition'] = f'attachment; filename="reporte_visual_{pk}.{file_type}"'
            
            return response

# Sirve para actualizar/modificar la simulacion FN4
class SimulationHistoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Simulation_history
    fields = ['student_notes']
    template_name = 'simulator/simulation_crud/history_form.html'
    success_url = reverse_lazy('simulation_history')
    
    # Restringe la consulta para que el usuario solo pueda editar sus propias simulaciones
    def get_queryset(self):
        group_id = self.request.session.get('ultimo_grupo_id')
        queryset = Simulation_history.objects.filter(configuration__author=self.request.user) # Filtra por usuario
        
        # Protege la bitácora, filtra por grupo
        if group_id:
            queryset = queryset.filter(configuration__academic_group_id=group_id)
            
        return queryset
    
    # Calcula el número secuencial dinámico para ocultar el ID real
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sequence = Simulation_history.objects.filter(
            configuration__author=self.request.user,
            calculated_at__gte=self.object.calculated_at
        ).count()
        
        context['sequence_id'] = sequence
        
        return context
    
    # Funcion para mostrar mensjes en el formulario
    def form_valid(self, form):
        messages.success(self.request, 'Notas actualizadas correctamente.')
        return super().form_valid(form)

# FN4: Esta clase sirve para borrar del historial una simulacion
class SimulationHistoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Simulation_history
    template_name = 'simulator/simulation_crud/history_confirm_delete.html'
    success_url = reverse_lazy('simulation_history')
    
    # Este metodo restringe la consulta para que el usuario solo pueda borrar sus propios experimentos
    def get_queryset(self):
        group_id = self.request.session.get('ultimo_grupo_id')
        queryset = Simulation_history.objects.filter(configuration__author=self.request.user) # Filtra por usuario
        
        # Protege la bitácora, filtra por grupo
        if group_id:
            queryset = queryset.filter(configuration__academic_group_id=group_id)
            
        return queryset
    
    # Calcula el número secuencial dinámico para ocultar el ID real
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sequence = Simulation_history.objects.filter(
            configuration__author=self.request.user,
            calculated_at__gte=self.object.calculated_at
        ).count()
            
        context['sequence_id'] = sequence
            
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Simulación eliminada de la bitácora.')
        return super().form_valid(form)

# Esta clase es el dashboard principal del usuario, lo que ve una vez inicia sesion.
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'simulator/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Identificacion de los roles booleanos para el HTML
        context['is_admin'] = user.is_superuser or user.groups.filter(name='Administrador').exists()
        context['is_teacher'] = user.groups.filter(name='Docente/Divulgador').exists()
        
        # Si no es admin ni docente, se asume que es estudiante
        context['is_student'] = not (context['is_admin'] or context['is_teacher'])
        context['title'] = 'Panel de control | ISW-Lab'
        
        return context

# Define la clase encargada de gestionar, construir y enviar notificaciones por correo con reportes adjuntos
class AsyncTeacherNotification:
    def __init__(self, student_user, config_name, status, execution_time, simulation_result, id_group=None):
        self.student_user = student_user
        self.config_name = config_name
        self.status = status
        self.execution_time = execution_time
        self.simulation_result = simulation_result
        self.id_group = id_group

    # Método privado para generar un libro de Excel en memoria y adjuntarlo al objeto de correo
    def _attach_excel(self, email):
        # Crea un buffer en memoria RAM (flujo de bytes) para evitar guardar archivos en el disco duro
        buffer_excel = io.BytesIO()
        
        # Abre un escritor de Excel de Pandas usando 'openpyxl' como motor apuntando al buffer en memoria
        
        with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
            self.simulation_result['dataframe_params'].to_excel(writer, sheet_name='Configuración', index=False) # Exporta el DataFrame de parámetros iniciales a una hoja llamada 'Configuración' sin índices numéricos
            self.simulation_result['dataframe_evolution'].to_excel(writer, sheet_name='Evolución 2D', index=False) # Exporta el DataFrame de evolución temporal a una hoja llamada 'Evolución 2D' sin índices
            self.simulation_result['dataframe'].to_excel(writer, sheet_name='Datos crudos 3D', index=False) # Exporta el DataFrame con los datos espaciales completos a una hoja llamada 'Datos crudos 3D' sin índices

        # Adjunta los bytes del Excel generado al correo especificando nombre de archivo y tipo MIME oficial
        email.attach(f'Datos_{self.config_name}.xlsx', buffer_excel.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    # Método privado para unir la gráfica 3D y las 2D en un solo archivo PDF y adjuntarlo al correo
    def _attach_pdf(self, email):
        # Exporta la figura 3D de Plotly a PNG en bytes y la abre como imagen de Pillow (PIL)
        img_3d = Matplotlib3DRenderer.render(
            self.simulation_result['dataframe'],
            self.config_name
        )
        images_2d = [Image.open(io.BytesIO(base64.b64decode(re.search(r'base64,(.*?)"', self.simulation_result['graphs_2d']['log'][k],).group(1)))) for k in ['temp', 'density', 'velocity', 'radius', 'mass']]

        # Calcula la altura total del documento sumando la altura de la imagen 3D más todas las imágenes 2D
        total_height = img_3d.height + sum(img.height for img in images_2d)
        canvas = Image.new('RGB', (800, total_height), (17, 17, 17)) # Crea un lienzo en blanco de 800 px de ancho por la altura total con fondo oscuro  (17, 17, 17)
        canvas.paste(img_3d, (0, 0)) # Pega la gráfica 3D en la esquina superior izquierda
        y_offset = img_3d.height # Inicializa el desplazamiento vertical justo debajo de la imagen 3D
        
        # Recorre cada una de las 5 gráficas 2D para apilarlas verticalmente
        for img in images_2d:
            canvas.paste(img, (0, y_offset)) # Pega la gráfica 2D actual en la posición X=0 y Y=y_offset    
            y_offset += img.height # Incrementa el desplazamiento vertical sumando la altura de la gráfica recién pegada
        
        buffer_pdf = io.BytesIO() # Crea un nuevo buffer temporal en memoria RAM para almacenar el documento PDF
        canvas.save(buffer_pdf, format='PDF') # Guarda el lienzo compuesto dentro del buffer codificado en formato PDF
        
        # Adjunta los bytes del PDF resultante al objeto de correo con su nombre y tipo MIME
        email.attach(f'Reporte_{self.config_name}.pdf', buffer_pdf.getvalue(), 'application/pdf')
    
    # Método principal que orquesta la búsqueda de docentes, armado del correo, adjuntos y envío SMTP
    def send(self):
        # Consulta los correos únicos de los docentes vinculados al grupo académico del estudiante
        teacher_emails = Academic_group.objects.filter(students=self.student_user).values_list('teacher__email', flat=True).distinct()
        
        if self.id_group:
            teacher_emails = Academic_group.objects.filter(
                pk = self.id_group,
                students = self.student_user
            ).values_list('teacher__email', flat=True).distinct() # values_list devuelve el QuerySet, flat=True para un solo campo y SELECT DISTINCT
        else:
            teacher_emails = Academic_group.objects.filter(
                students = self.student_user
            ).values_list('teacher__email', flat=True).distinct()
                
        # Verifica si la lista de correos de docentes está vacía
        if not teacher_emails:
            return # Detiene la ejecución del método silenciosamente si el estudiante no tiene docentes asignados
        
        # Construye el diccionario de contexto con los datos dinámicos para las plantillas de correo
        context = {
            'student_name': self.student_user.get_full_name() or self.student_user.username,
            'simulation_name': self.config_name,
            'status': self.status,
            'time': self.execution_time,
        }
        
        subject = f'ISW-Lab: Resultados de simulación - {self.student_user.username}' # Define el asunto del correo electrónico incluyendo el usuario del estudiante
        message_text = render_to_string( 'simulator/teacher_notification/teacher_notification.txt', context) # Renderiza la plantilla de texto plano inyectando las variables del contexto
        message_html = render_to_string('simulator/teacher_notification/teacher_notification_email.html', context) # Renderiza la plantilla HTML inyectando las variables del contexto
        sender = getattr(settings, 'DEFAULT_FROM_EMAIL', 'brio231179@upemor.edu.mx')
        email = EmailMultiAlternatives(subject, message_text, sender, list(teacher_emails)) # Crea la instancia base del correo electrónico de Django con texto plano y destinatarios
        email.attach_alternative(message_html, 'text/html') # Añade la versión HTML como alternativa enriquecida para clientes de correo modernos
        
        
        # Comprueba si la simulación fue numéricamente estable antes de generar los reportes pesados
        if self.status != 'divergente':
            self._attach_excel(email)
            self._attach_pdf(email)
        
        try:
            # Envía el correo; fail_silently=False permite lanzar una excepción si el servidor SMTP falla
            email.send(fail_silently=False)
        except Exception as e:
            print(f'Error al enviar correo: {str(e)}')

# Esta vista es para rendedizar las graficas 3D.
class Matplotlib3DRenderer:
    @staticmethod # Permite llamarla directo con Matplotlib3DRenderer.render(...) sin necesidad de instanciar la clase cada vez.
    def render(df_3d, title="Simulación 3D"):
        if len(df_3d) > 2500:
            df_3d = df_3d.sample(n=2500, random_state=42)
        
        fig_mpl = plt.figure(figsize=(8, 6), dpi=100, facecolor='#111111')
        ax = fig_mpl.add_subplot(111, projection='3d', facecolor='#111111')

        sc = ax.scatter(
            df_3d['Eje X (pc)'],
            df_3d['Eje Y (pc)'],
            df_3d['Eje Z (pc)'],
            c=df_3d['Densidad (%)'],
            cmap='plasma',
            vmin=5,
            vmax=100,
            s=20,
            alpha=0.75,
            edgecolors='none'
        )

        cbar = fig_mpl.colorbar(sc, ax=ax, shrink=0.65, pad=0.1)
        cbar.set_label('Densidad (%)', color='white', fontsize=10)
        cbar.ax.yaxis.set_tick_params(color='white', labelcolor='white')

        ax.set_xlabel('X (pc)', color='white')
        ax.set_ylabel('Y (pc)', color='white')
        ax.set_zlabel('Z (pc)', color='white')
        ax.tick_params(colors='white', labelsize=8)
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.set_title(f'Simulation: {title}', color='white', fontsize=12)

        buf = io.BytesIO()
        fig_mpl.savefig(buf, format='png', facecolor='#111111')
        plt.close(fig_mpl)  # Libera la RAM de inmediato
        buf.seek(0)
        return Image.open(buf).convert('RGB')