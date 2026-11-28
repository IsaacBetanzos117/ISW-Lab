from django.contrib import messages
from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, Http404
from weasyprint import HTML
from grupos.models import Academic_group
from reportes.forms import ReportFilterForm
from .services import DashboardChartService, ExcelExportService, PDFExportService
from django.template.loader import render_to_string

# Create your views here.

# Esta vista maneja la visualización del panel de reportes gerenciales. Solo los usuarios con los grupos "Administrador" o "Docente/Divulgador" 
# pueden acceder a esta vista. Se utiliza un formulario para filtrar los reportes por fecha de inicio, fecha de fin y grupo académico.
class ManagementReportsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'reports/management_reports.html'
    
    # Este método verifica si el usuario pertenece a los grupos permitidos para acceder al panel de reportes.
    def test_func(self):
        user_groups = self.request.user.groups.values_list('name', flat=True) # Obtiene los nombres de los grupos a los que pertenece el usuario
        return 'Administrador' in user_groups or 'Docente/Divulgador' in user_groups
        
    # Método para manejar el rechazo de permisos limpiamente sin error 404
    def handle_no_permission(self):
        messages.warning(self.request, "Acceso denegado: No tienes permisos para ver los reportes gerenciales.")
        return redirect('dashboard')
    
    # Este método prepara el contexto que se enviará a la plantilla, incluyendo el formulario de filtrado y los datos seleccionados por el usuario.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) # Obtiene el contexto base de la vista
        form = ReportFilterForm(self.request.GET or None) # Instancia el formulario con los datos de la URL
        start_date = None
        end_date = None
        selected_group = None
        
        # Si el formulario es válido, extrae los datos limpios
        if form.is_valid():
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            group_id = form.cleaned_data.get('group_id')
                    
            # Si se ha proporcionado un ID de grupo, se obtiene el grupo académico correspondiente; de lo contrario, se mantiene como None.
            if group_id:
                selected_group = get_object_or_404(Academic_group, pk=group_id)
                        
        chart_service = DashboardChartService(
            start_date=start_date, 
            end_date=end_date, 
            selected_group=selected_group
        )
            
        # Extrae todas las gráficas y las inyecta al contexto de Django
        context.update(chart_service.generate_all_charts())
        
        # Enviamos el formulario y las variables a la plantilla
        context['form'] = form
        context['start_date'] = start_date
        context['end_date'] = end_date
        context['selected_group'] = selected_group
            
        return context


# Esta vista maneja la exportación de reportes gerenciales en formato Excel. Solo los usuarios con los grupos "Administrador" o "Docente/Divulgador" pueden acceder a esta funcionalidad.
class ExportReportsExcelView(LoginRequiredMixin, UserPassesTestMixin, View):
    
    # Este método verifica si el usuario pertenece a los grupos permitidos para exportar reportes en Excel.
    def test_func(self):
        user_groups = self.request.user.groups.values_list('name', flat=True) # Obtiene los nombres de los grupos a los que pertenece el usuario
        return 'Administrador' in user_groups or 'Docente/Divulgador' in user_groups

    def handle_no_permission(self):
        messages.warning(self.request, "Acceso denegado: No tienes permisos para exportar en Excel.")
        return redirect('dashboard')
    
    # Este método maneja la solicitud GET para exportar los reportes en formato Excel. Valida los parámetros de filtrado y genera el archivo correspondiente.
    def get(self, request, *args, **kwargs):
        try:
            form = ReportFilterForm(request.GET)
            
            if not form.is_valid():
                messages.warning(request, "Parámetros de filtrado inválidos.")
                return redirect('management_reports')

            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            group_id = form.cleaned_data.get('group_id')
            selected_group = get_object_or_404(Academic_group, pk=group_id) if group_id else None
            
            # Instancia del servicio de exportación a Excel con los parámetros filtrados
            excel_service = ExcelExportService(
                start_date=start_date,
                end_date=end_date,
                selected_group=selected_group
            )
            excel_file = excel_service.generate_excel() # Generacion del archivo en memoria
            
            # Construye la respuesta HTTP para forzar la descarga
            response = HttpResponse(excel_file, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="Reporte_Gerencial_ISW_Lab.xlsx"'
            
            return response
        except Http404: # Si ocurre un error de tipo Http404, se vuelve a lanzar para que sea manejado por Django
            raise
        except Exception as e: # Si ocurre cualquier otro tipo de excepción, interceptamos y redirigimos con un mensaje
            messages.error(request, f"Ocurrió un error crítico al intentar generar el archivo Excel: {str(e)}")
            return redirect('management_reports')


# Esta vista maneja la exportación de reportes gerenciales en formato PDF. Solo los usuarios con los grupos "Administrador" o "Docente/Divulgador" pueden acceder a esta funcionalidad.
class ExportReportsPDFView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        user_groups = self.request.user.groups.values_list('name', flat=True)
        return 'Administrador' in user_groups or 'Docente/Divulgador' in user_groups

    def handle_no_permission(self):
        messages.warning(self.request, "Acceso denegado: No tienes permisos para exportar en PDF.")
        return redirect('dashboard')

    def get(self, request, *args, **kwargs):
        try:
            form = ReportFilterForm(request.GET)
            
            if not form.is_valid():
                messages.error(request,"Parámetros de filtrado inválidos.")
                return redirect('management_reports')
                
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            group_id = form.cleaned_data.get('group_id')
            selected_group = get_object_or_404(Academic_group, pk=group_id) if group_id else None
            
            # Instancia del servicio y generacion del contexto con las imágenes
            pdf_service = PDFExportService(start_date=start_date, end_date=end_date, selected_group=selected_group)
            context = pdf_service.get_charts_base64()
            
            # Datos descriptivos al contexto
            context['start_date'] = start_date
            context['end_date'] = end_date
            context['selected_group'] = selected_group
            html_string = render_to_string('reports/pdf_report.html', context) # Renderiza la plantilla HTML como una cadena de texto (string)
            pdf_file = HTML(string=html_string).write_pdf() # WeasyPrint para convertir ese HTML a PDF
            response = HttpResponse(pdf_file, content_type='application/pdf') # Retorna la respuesta forzando la descarga del PDF
            response['Content-Disposition'] = 'attachment; filename="Reporte_Gerencial_ISW_Lab.pdf"'
            
            return response
        except Http404:
            raise
        except Exception as e:
            messages.error(request,f"Ocurrió un error crítico al intentar generar el archivo PDF: {str(e)}")
            return redirect('management_reports')