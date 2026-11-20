from django.urls import path
from .views import DatabaseMaintenanceView, DatabaseBackupDownloadView, DatabaseRestoreView

urlpatterns = [
    path('', DatabaseMaintenanceView.as_view(), name='db_maintenance'),
    path('descargar/', DatabaseBackupDownloadView.as_view(), name='db_backup_download'),
    path('restaurar/', DatabaseRestoreView.as_view(), name='db_restore'),
]