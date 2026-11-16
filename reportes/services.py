import pandas as pd
import plotly.express as px
from simulador.models import Simulation_history, Simulation_configuration
import io # Sirve para crear un flujo de bytes en memoria, lo cual es útil para generar archivos Excel o PDF sin necesidad de guardarlos en el disco.
import base64 # Sirve para codificar imágenes en base64 (transformar datos binarios en texto plano), lo cual es útil para incrustar gráficos en archivos PDF.
from catalog.models import Scientific_reference
from datetime import timedelta # Importado a nivel global para ser usado por todos los servicios

# Esta clase se encarga de generar los gráficos del panel de reportes gerenciales.
class DashboardChartService:
    def __init__(self, start_date=None, end_date=None, selected_group=None, morphological_type=None):
        self.start_date = start_date
        self.end_date = end_date
        self.selected_group = selected_group
        self.morphological_type = morphological_type # Guardar el filtro
        self.history_qs = Simulation_history.objects.all()
        self.config_qs = Simulation_configuration.objects.all()
        self._apply_filters()
    
    # Método privado que aplica los filtros de fecha y grupo a los QuerySets.
    def _apply_filters(self):
        # 1. Filtros seguros para la fecha de inicio
        if self.start_date:
            # Usamos __gte directo sobre el datetime, sin invocar conversiones de BD
            self.history_qs = self.history_qs.filter(calculated_at__gte=self.start_date)
            self.config_qs = self.config_qs.filter(saved_date__gte=self.start_date)
            
        # 2. Filtros seguros para la fecha de fin
        if self.end_date:
            # Sumamos exactamente 1 día y usamos "menor que" (<) para abarcar hasta las 23:59:59
            end_date_safe = self.end_date + timedelta(days=1)
            self.history_qs = self.history_qs.filter(calculated_at__lt=end_date_safe)
            self.config_qs = self.config_qs.filter(saved_date__lt=end_date_safe)

        # 3. Filtro por grupo académico
        if self.selected_group:
            self.history_qs = self.history_qs.filter(configuration__author__groups=self.selected_group)
            self.config_qs = self.config_qs.filter(author__groups=self.selected_group)
    
    # Este método genera un gráfico de línea que muestra la actividad de simulaciones a lo largo del tiempo, basado en el historial filtrado.
    def get_activity_chart(self):
        if not self.history_qs.exists():
            return None
        
        df_activity = pd.DataFrame(list(self.history_qs.values('calculated_at')))
        # Convertir a datetime y forzar al primer día del mes para agrupar
        df_activity['mes'] = pd.to_datetime(df_activity['calculated_at']).dt.to_period('M').dt.to_timestamp()
        df_grouped = df_activity.groupby('mes').size().reset_index(name='conteo')
        
        # Generar gráfica de BARRAS por MES
        fig = px.bar(df_grouped, x='mes', y='conteo',
                      title="Volumen de cálculos ejecutados en el tiempo (Por mes)",
                      labels={'mes': 'Mes de ejecución', 'conteo': 'Simulaciones calculadas'})
        
        # Formatear el eje X para que muestre el mes (ej. "Oct 2026")
        fig.update_layout(xaxis=dict(tickformat="%b %Y", dtick="M1"))
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # Este método genera un gráfico de pastel que muestra la distribución morfológica de las configuraciones de simulación, basado en el QuerySet filtrado.
    def get_morphology_chart(self):
        if not self.history_qs.exists(): # Si no hay registros en el QuerySet filtrado, devuelve None para indicar que no se puede generar el gráfico.
            return None
        
        df_morph = pd.DataFrame(list(self.history_qs.values('configuration__morphological_type'))) # Se crea un DataFrame a partir del QuerySet de historial de simulaciones, extrayendo solo el tipo morfológico de la configuración ligada a cada registro del historial.
        
        # Si el DataFrame está vacío, devuelve None para indicar que no se puede generar el gráfico.
        if df_morph.empty:
            return None
            
        df_morph_grouped = df_morph.groupby('configuration__morphological_type').size().reset_index(name='Total') # Se agrupa por tipo morfológico y se cuenta el número de registros por tipo, creando un DataFrame con dos columnas: 'configuration__morphological_type' y 'Total'.
        df_morph_grouped.rename(columns={'configuration__morphological_type': 'Morfología'}, inplace=True) # Se renombra la columna 'configuration__morphological_type' a 'Morfología' para el gráfico y en el Excel.
        
        # Se genera un gráfico de pastel utilizando Plotly Express, mostrando la distribución morfológica simulada.
        fig = px.pie(df_morph_grouped, names='Morfología', values='Total', 
                     title="Distribución morfológica simulada")
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    
    # Este método genera un gráfico de barras que muestra el volumen de experimentos guardados por usuario, basado en el QuerySet filtrado.
    def get_volume_chart(self):
        if not self.history_qs.exists():
            return None
        
        df_vol = pd.DataFrame(list(self.history_qs.values('configuration__author__username')))
        df_vol_grouped = df_vol.groupby('configuration__author__username').size().reset_index(name='total').sort_values(by='total', ascending=True).tail(10) # ascending=True para que el mayor quede arriba
        
        # Cambiar a gráfica de barras HORIZONTALES (orientation='h') e intercambiar X e Y
        fig = px.bar(df_vol_grouped, x='total', y='configuration__author__username', orientation='h',
                     title="Top 10 usuarios activos (Por cálculos)",
                     labels={'configuration__author__username': 'Usuario', 'total': 'Cálculos ejecutados'})
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    
    # Este método genera un gráfico de barras que muestra el crecimiento del catálogo de referencias científicas por día, basado en el QuerySet filtrado.
    def get_catalog_chart(self):
        qs = Scientific_reference.objects.all()
        
        # Filtros de catálogo homologados
        if self.start_date:
            qs = qs.filter(created_at__gte=self.start_date)
        if self.end_date:
            end_date_safe = self.end_date + timedelta(days=1)
            qs = qs.filter(created_at__lt=end_date_safe)
            
        if not qs.exists():
            return None
            
        df_cat = pd.DataFrame(list(qs.values('created_at')))
        df_cat['fecha'] = pd.to_datetime(df_cat['created_at']).dt.date
        df_grouped = df_cat.groupby('fecha').size().reset_index(name='nuevas')
        
        # Generar gráfica de barras por día
        fig = px.bar(df_grouped, x='fecha', y='nuevas', 
                      title="Volumen de documentación (Nebulosas ingresadas)",
                      labels={'fecha': 'Fecha de registro', 'nuevas': 'Nebulosas añadidas'})
                      
        # CORRECCIÓN DE LA PROPIEDAD DEL LAYOUT
        fig.update_layout(yaxis=dict(tickformat="d"))
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    
    # Este método público genera todos los gráficos y los devuelve en un diccionario.
    def generate_all_charts(self):
        return {
            'chart_activity': self.get_activity_chart(),
            'chart_morphology': self.get_morphology_chart(),
            'chart_volume': self.get_volume_chart(),
            'chart_catalog': self.get_catalog_chart()
        }

# Esta clase se encarga de exportar los datos estadísticos filtrados a un archivo de Excel (.xlsx) con múltiples hojas.
class ExcelExportService:
    def __init__(self, start_date=None, end_date=None, selected_group=None):
        self.start_date = start_date
        self.end_date = end_date
        self.selected_group = selected_group
        self.history_qs = Simulation_history.objects.all()
        self.config_qs = Simulation_configuration.objects.all()
        self._apply_filters()
    
    # Este método privado aplica los mismos filtros de fecha y grupo que se utilizan en el panel de reportes gerenciales, asegurando que los datos exportados coincidan con los datos visualizados en los gráficos.
    def _apply_filters(self):
        if self.selected_group:
            self.history_qs = self.history_qs.filter(configuration__author__in=self.selected_group.students.all())
            self.config_qs = self.config_qs.filter(author__in=self.selected_group.students.all())
            
        # Filtros homologados sin __date
        if self.start_date:
            self.history_qs = self.history_qs.filter(calculated_at__gte=self.start_date)
            self.config_qs = self.config_qs.filter(saved_date__gte=self.start_date)
            
        if self.end_date:
            end_date_safe = self.end_date + timedelta(days=1)
            self.history_qs = self.history_qs.filter(calculated_at__lt=end_date_safe)
            self.config_qs = self.config_qs.filter(saved_date__lt=end_date_safe)
    
    
    # Este método genera el archivo Excel en memoria y lo devuelve como bytes, listo para ser enviado como respuesta HTTP.
    def generate_excel(self):
        output = io.BytesIO() # Crea un flujo de bytes en memoria para almacenar el archivo Excel generado. Esto permite generar el archivo sin necesidad de guardarlo en el disco
        
        # Uso de openpyxl para escribir el archivo Excel
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            
            # Actividad y uso de simulaciones
            if self.history_qs.exists():
                
                # Se crea un DataFrame a partir del QuerySet de historial de simulaciones
                df_act = pd.DataFrame(list(self.history_qs.values(
                    'calculated_at', 'configuration__morphological_type', 'configuration__author__username'
                )))
                
                # Convierte la columna a datetime y elimina la zona horaria
                df_act['calculated_at'] = pd.to_datetime(df_act['calculated_at']).dt.tz_localize(None)
                
                # Renombra las columnas en el archivo Excel
                df_act.rename(columns={
                    'calculated_at': 'Fecha de simulación', 
                    'configuration__morphological_type': 'Morfología', 
                    'configuration__author__username': 'Usuario'
                }, inplace=True)
                df_act.to_excel(writer, sheet_name='Actividad de simulaciones', index=False) # Escribe el DataFrame en la hoja "Actividad de simulaciones" del archivo Excel
            else:
                pd.DataFrame({'Mensaje': ['Sin cálculos en este periodo']}).to_excel(writer, sheet_name='Actividad de simulaciones', index=False)
            
            # Tendencias morfológicas
            if self.history_qs.exists():
                df_morph = pd.DataFrame(list(self.history_qs.values('configuration__morphological_type'))) # Se crea un DataFrame a partir del QuerySet de historial de simulaciones, extrayendo solo el tipo morfológico de la configuración ligada a cada registro del historial
                df_morph_grouped = df_morph.groupby('configuration__morphological_type').size().reset_index(name='Total') # Se agrupa por tipo morfológico y se cuenta el número de registros por tipo
                df_morph_grouped.rename(columns={'configuration__morphological_type': 'Tipo Morfológico'}, inplace=True) # Se renombra la columna para que tenga un nombre más amigable en el archivo Excel
                df_morph_grouped.to_excel(writer, sheet_name='Tendencias morfologicas', index=False) # Escribe el DataFrame en la hoja "Tendencias morfologicas" del archivo Excel
            else:
                pd.DataFrame({'Mensaje': ['Sin simulaciones registradas']}).to_excel(writer, sheet_name='Tendencias morfologicas', index=False)

            # Usuarios activos
            if self.history_qs.exists():
                df_vol = pd.DataFrame(list(self.history_qs.values('configuration__author__username'))) # Se crea un DataFrame a partir del QuerySet de historial de simulaciones, extrayendo solo el nombre de usuario del autor de la configuración que se simuló
                df_vol_grouped = df_vol.groupby('configuration__author__username').size().reset_index(name='Total').sort_values(by='Total', ascending=False) # Se agrupa por usuario y se cuenta el número de registros por usuario, luego se ordena de mayor a menor
                df_vol_grouped.rename(columns={'configuration__author__username': 'Usuario'}, inplace=True) # Se renombra la columna en el archivo Excel
                df_vol_grouped.to_excel(writer, sheet_name='Usuarios mas activos', index=False) # Escribe el DataFrame en la hoja "Usuarios mas activos" del archivo Excel
            else:
                pd.DataFrame({'Mensaje': ['Sin actividad de usuarios']}).to_excel(writer, sheet_name='Usuarios mas activos', index=False)
            
            # Crecimiento del catálogo de referencias
            qs_cat = Scientific_reference.objects.all()
            
            # Filtros de catálogo homologados
            if self.start_date:
                qs_cat = qs_cat.filter(created_at__gte=self.start_date) # Si se ha proporcionado una fecha de inicio, se filtran las referencias científicas para incluir solo las creadas después de esa fecha.
            if self.end_date:
                end_date_safe = self.end_date + timedelta(days=1)
                qs_cat = qs_cat.filter(created_at__lt=end_date_safe) # Si se ha proporcionado una fecha de finalización, se filtran las referencias científicas para incluir solo las creadas antes o en esa fecha.
            
            if qs_cat.exists():
                df_cat = pd.DataFrame(list(qs_cat.values('nebula_name', 'created_at'))) # Se crea un DataFrame a partir del QuerySet de referencias científicas, extrayendo el nombre de la nebulosa y la fecha de creación
                df_cat['created_at'] = pd.to_datetime(df_cat['created_at']).dt.tz_localize(None) # Convierte la columna a datetime y elimina la zona horaria
                df_cat.rename(columns={'nebula_name': 'Título de referencia', 'created_at': 'Fecha de registro'}, inplace=True) # Se renombra las columnas en el archivo Excel
                df_cat.to_excel(writer, sheet_name='Crecimiento del catalogo', index=False) # Escribe el DataFrame en la hoja "Crecimiento del catalogo" del archivo Excel
            else:
                pd.DataFrame({'Mensaje': ['Sin referencias en este periodo']}).to_excel(writer, sheet_name='Crecimiento del catalogo', index=False) 
        
        return output.getvalue() # Devuelve el contenido del archivo Excel como bytes, listo para ser enviado como respuesta HTTP.


# Esta clase se encarga de exportar los datos estadísticos filtrados a un archivo PDF, incluyendo gráficos generados a partir de los datos.
class PDFExportService:
    def __init__(self, start_date=None, end_date=None, selected_group=None):
        self.start_date = start_date
        self.end_date = end_date
        self.selected_group = selected_group
        
        self.history_qs = Simulation_history.objects.all()
        self.config_qs = Simulation_configuration.objects.all()
        self._apply_filters()
    
    # Este método privado aplica los mismos filtros de fecha y grupo que se utilizan en el panel de reportes gerenciales, asegurando que los datos exportados coincidan con los datos visualizados en los gráficos.
    def _apply_filters(self):
        # Mismos filtros dinámicos que el dashboard y el excel
        if self.selected_group:
            self.history_qs = self.history_qs.filter(configuration__author__in=self.selected_group.students.all())
            self.config_qs = self.config_qs.filter(author__in=self.selected_group.students.all())
            
        # Filtros homologados sin __date
        if self.start_date:
            self.history_qs = self.history_qs.filter(calculated_at__gte=self.start_date)
            self.config_qs = self.config_qs.filter(saved_date__gte=self.start_date)
            
        if self.end_date:
            end_date_safe = self.end_date + timedelta(days=1)
            self.history_qs = self.history_qs.filter(calculated_at__lt=end_date_safe)
            self.config_qs = self.config_qs.filter(saved_date__lt=end_date_safe)
    
    
    # Este método convierte una figura de Plotly a una imagen PNG codificada en base64
    def _fig_to_base64(self, fig):
        img_bytes = fig.to_image(format="png", width=800, height=450)
        return base64.b64encode(img_bytes).decode('utf-8') 
    
    # Este método genera todas las gráficas y las devuelve en un diccionario, incluyendo la gráfica de crecimiento del catálogo.
    def get_charts_base64(self):
        # Inicializa todo en None
        charts = {'chart_activity': None, 'chart_morphology': None, 'chart_volume': None, 'chart_catalog': None, 'catalog_records': None}
        
        # Gráfica de actividad
        if self.history_qs.exists():
            df_act = pd.DataFrame(list(self.history_qs.values('calculated_at'))) # Se crea un DataFrame a partir del QuerySet de historial de simulaciones
            df_act['fecha'] = pd.to_datetime(df_act['calculated_at']).dt.date # Se extrae solo la fecha de la columna 'calculated_at'
            df_grouped = df_act.groupby('fecha').size().reset_index(name='conteo') # Se agrupa por fecha y se cuenta el número de registros por día
            
            # Se genera un gráfico de línea utilizando Plotly Express, mostrando la actividad de simulaciones a lo largo del tiempo.
            fig1 = px.line(df_grouped, x='fecha', y='conteo', 
                           title="Volumen de cálculos ejecutados en el tiempo", 
                           labels={'fecha': 'Fecha de ejecución', 'conteo': 'Simulaciones calculadas'})
            charts['chart_activity'] = self._fig_to_base64(fig1)
            
        # Gráfica de morfología
        if self.history_qs.exists():
            df_morph = pd.DataFrame(list(self.history_qs.values('configuration__morphological_type'))) # Se crea un DataFrame a partir del QuerySet de historial de simulaciones, extrayendo solo el tipo morfológico de la configuración ligada a cada registro del historial
            
            if not df_morph.empty:
                df_morph_grouped = df_morph.groupby('configuration__morphological_type').size().reset_index(name='Total') # Se agrupa por tipo morfológico y se cuenta el número de registros por tipo, creando un DataFrame con dos columnas: 'configuration__morphological_type' y 'Total'
                df_morph_grouped.rename(columns={'configuration__morphological_type': 'Morfología'}, inplace=True) # Se renombra la columna 'configuration__morphological_type' a 'Morfología' para el gráfico y en el Excel
                fig2 = px.pie(df_morph_grouped, names='Morfología', values='Total', title="Distribución morfológica simulada") # Se genera un gráfico de pastel utilizando Plotly Express, mostrando la distribución morfológica simulada
                charts['chart_morphology'] = self._fig_to_base64(fig2) # Se convierte la figura a base64 y se almacena en el diccionario de gráficos
            
        # Gráfica de volumen
        if self.history_qs.exists():
            df_vol = pd.DataFrame(list(self.history_qs.values('configuration__author__username')))# Se crea un DataFrame a partir del QuerySet de historial de simulaciones
            
            # Si el DataFrame no está vacío, se agrupa por usuario y se genera un gráfico de barras
            if not df_vol.empty:
                df_vol_grouped = df_vol.groupby('configuration__author__username').size().reset_index(name='total').sort_values(by='total', ascending=False).head(10) # Se agrupa por usuario y se cuenta el número de registros por usuario, luego se ordena de mayor a menor y se seleccionan los 10 usuarios más activos
                
                # Se genera un gráfico de barras utilizando Plotly Express, mostrando el top 10 de usuarios activos por cálculos ejecutados
                fig3 = px.bar(df_vol_grouped, x='configuration__author__username', y='total', 
                              title="Top 10 usuarios activos (Por cálculos)", 
                              labels={'configuration__author__username': 'Usuario', 'total': 'Cálculos ejecutados'})
                charts['chart_volume'] = self._fig_to_base64(fig3) # Se convierte la figura a base64 y se almacena en el diccionario de gráficos
        
        # Gráfica de catálogo
        qs_cat = Scientific_reference.objects.all()
        
        # Filtros de catálogo homologados
        if self.start_date: 
            qs_cat = qs_cat.filter(created_at__gte=self.start_date) # Si se ha proporcionado una fecha de inicio, se filtran las referencias científicas para incluir solo las creadas después de esa fecha.
        if self.end_date: 
            end_date_safe = self.end_date + timedelta(days=1)
            qs_cat = qs_cat.filter(created_at__lt=end_date_safe) # Si se ha proporcionado una fecha de finalización, se filtran las referencias científicas para incluir solo las creadas antes o en esa fecha.
        
        # Si existen referencias científicas en el QuerySet filtrado, se genera un gráfico de barras que muestra el crecimiento del catálogo por día y se almacena en el diccionario de gráficos. Además, se obtienen las últimas 15 referencias añadidas al catálogo para mostrarlas en la tabla del PDF.
        if qs_cat.exists():
            df_cat = pd.DataFrame(list(qs_cat.values('created_at'))) # Se crea un DataFrame a partir del QuerySet de referencias científicas
            df_cat['fecha'] = pd.to_datetime(df_cat['created_at']).dt.date # Se extrae solo la fecha de la columna 'created_at'
            df_grouped = df_cat.groupby('fecha').size().reset_index(name='nuevas') # Se agrupa por fecha y se cuenta el número de referencias añadidas por día
            
            # Se genera un gráfico de barras utilizando Plotly Express, mostrando el volumen de documentación (nebulosas ingresadas) a lo largo del tiempo.
            fig4 = px.bar(df_grouped, x='fecha', y='nuevas', 
                          title="Volumen de documentación (Nebulosas ingresadas)", 
                          labels={'fecha': 'Fecha de registro', 'nuevas': 'Nebulosas añadidas'})
            
            fig4.update_layout(yaxis=dict(tickformat="d")) # Fuerza números enteros en el eje Y
            charts['chart_catalog'] = self._fig_to_base64(fig4) # Se convierte la figura a base64 y se almacena en el diccionario de gráficos
            charts['catalog_records'] = qs_cat.order_by('-created_at')[:15] # Se obtienen las últimas 15 referencias añadidas al catálogo, ordenadas por fecha de creación descendente, para mostrarlas en la tabla del PDF.
        
        return charts # Devuelve un diccionario con las gráficas codificadas en base64 y las últimas referencias añadidas al catálogo.