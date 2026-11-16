from django.urls import path
from .views import ReferenceCreateView, ReferenceDeleteView, ReferenceDetailView, ReferenceListView, ReferenceUpdateView

urlpatterns = [
    path('', ReferenceListView.as_view(), name='reference_list'),
    path('<int:pk>/', ReferenceDetailView.as_view(), name='reference_detail'),
    path('nueva/', ReferenceCreateView.as_view(), name='reference_create'),
    path('<int:pk>/editar/', ReferenceUpdateView.as_view(), name='reference_update'),
    path('<int:pk>/eliminar/', ReferenceDeleteView.as_view(), name='reference_delete'),
]