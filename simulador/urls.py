from django import views
from django.urls import path
from .views import DashboardView, ProcessSimulationView, SimulationDownloadView, SimulationHistoryDeleteView, SimulationHistoryDetailView, SimulationHistoryListView, SimulationConfigurationCreateView, SimulationConfigurationDeleteView, SimulationConfigurationUpdateView, SimulationConfigListView, SimulationHistoryUpdateView

urlpatterns = [
    # FN.3: Menú principal (Tarjetas de los docentes)
    path('', DashboardView.as_view(), name='dashboard'),
    
    # FN.3: Formulario vacío para que el alumno intente replicar
    path('experimentar/', SimulationConfigurationCreateView.as_view(), name='simulation_configuration_create_view'),
    
    # Esta es la ruta para ver tus configuraciones (FN.3)
    path('parametros/', SimulationConfigListView.as_view(), name='config_list'),
    
    # FN.3 Edición y eliminación (Bitácora)
    path('parametros/editar/<int:pk>/', SimulationConfigurationUpdateView.as_view(), name='simulation_configuration_update_view'),
    path('parametros/eliminar/<int:pk>/', SimulationConfigurationDeleteView.as_view(), name='simulation_configuration_delete_view'),

    # FN.3: Prueba de renderizado 3D
    path('simular/<int:pk>/', ProcessSimulationView.as_view(), name='process_simulation'),
    
    # Ruta para ver el render 3D de un registro histórico específico
    path('historial/render/<int:pk>/', SimulationHistoryDetailView.as_view(), name='history_render'),
    
    # FN.4: Descarga directa de archivos al vuelo
    path('historial/descargas/<int:pk>/<str:file_type>/', SimulationDownloadView.as_view(), name='download_file'),
    path('historial/editar/<int:pk>/', SimulationHistoryUpdateView.as_view(), name='history_edit'),
    path('historial/eliminar/<int:pk>/', SimulationHistoryDeleteView.as_view(), name='history_delete'),
    # FN.4: La bitácora privada del alumno (La tabla)
    path('historial/', SimulationHistoryListView.as_view(), name='simulation_history'),
    
    # path('configuracion/<int:pk>/editar/', SimulationConfigurationUpdateView.as_view(), name='simulation_configuration_update_view'),
]