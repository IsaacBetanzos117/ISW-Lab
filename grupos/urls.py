from django.urls import path
from .views import AcademicGroupDeleteView, AcademicGroupDetailView, AcademicGroupListView, AcademicGroupCreateView, AcademicGroupUpdateView, GroupSimulationListView

urlpatterns = [
    path('', AcademicGroupListView.as_view(), name='group_list'),
    path('crear/', AcademicGroupCreateView.as_view(), name='group_create'),
    path('editar/<int:pk>/', AcademicGroupUpdateView.as_view(), name='group_update'),
    path('eliminar/<int:pk>/', AcademicGroupDeleteView.as_view(), name='group_delete'),
    path('<int:pk>/simulaciones/', GroupSimulationListView.as_view(), name='group_simulations'),
    path('clase/<int:pk>/', AcademicGroupDetailView.as_view(), name='group_detail'),
]