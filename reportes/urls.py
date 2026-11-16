from django.urls import path
from .views import ExportReportsPDFView, ManagementReportsView, ExportReportsExcelView

urlpatterns = [
    path('', ManagementReportsView.as_view(), name='management_reports'),
    path('exportar/excel/', ExportReportsExcelView.as_view(), name='export_reports_excel'),
    path('exportar/pdf/', ExportReportsPDFView.as_view(), name='export_reports_pdf'),
]