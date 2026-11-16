import numpy as np
import plotly.graph_objects as go
import time
import pandas as pd
from django.conf import settings
import matplotlib
matplotlib.use('Agg') # Evita que Matplotlib intente abrir ventanas gráficas en el sistema operativo
import matplotlib.pyplot as plt
import io
import base64

# Esta clase encapsula la lógica de simulación y renderizado, separando la matemática de la interfaz web
# siguiendo el principio de Responsabilidad Única para facilitar el mantenimiento (EV.1).
class SimulationEngine:
    # Constantes físicas universales utilizadas en los cálculos astrofísicos
    G_CONSTANT = 6.67430e-11     # Constante gravitacional (m^3 kg^-1 s^-2)
    SOLAR_MASS = 1.989e30        # Masa solar en kilogramos (kg)
    PARSEC = 3.086e16            # Un Parsec convertido a metros (m)
    BOLTZMANN = 1.380649e-23     # Constante de Boltzmann (J/K)
    SPEED_OF_LIGHT = 299792458.0 # Velocidad de la luz (m/s)
    
    def __init__(self, configuration_instance):
        # Recibe la instancia de la base de datos (Simulation_configuration)
        self.config = configuration_instance

    # Método principal: Controla el tiempo de ejecución y orquesta los submétodos de física y gráficos
    def execute_simulation(self):
        start_time = time.time()
        
        try:
            physics_data = self.calculate_physics() # Calcula toda la física y recupera las matrices/DataFrames
            plot_3d = self.generate_3d_plot(physics_data) # Genera las representaciones visuales a partir de los datos crudos
            graphs_2d = self.generate_2d_plots(physics_data)
            execution_time = round(time.time() - start_time, 2) # Mide el tiempo total real que tardó el servidor en procesar la petición
            
            # Retorna el diccionario estructurado a la vista para ser inyectado en el HTML o descargado
            return {
                'status': 'estable',
                'execution_time': execution_time,
                'plot_html': plot_3d,
                'graphs_2d': graphs_2d, 
                'dataframe': physics_data['df_export'],               # Datos 3D crudos
                'dataframe_params': physics_data['df_params'],        # Parámetros iniciales
                'dataframe_evolution': physics_data['df_evolution'],  # Evolución cronológica
                'notes': 'Simulación ejecutada correctamente.',
                'fig': physics_data['fig']                            # Exportado crudo de Plotly para PDFs/Imágenes
            }
            
        except Exception as error:
            # Si el cálculo matemático falla (ej. por singularidades), atrapa el error y evita que el servidor caiga
            execution_time = round(time.time() - start_time, 2)
            return {
                'status': 'divergente',
                'execution_time': execution_time,
                'plot_html': None, 
                'graphs_2d': None,
                'notes': f'Error numérico: {str(error)}',
            }

    # Lógica matemática estricta (Cálculo matricial y termodinámico)
    def calculate_physics(self):
        # Extracción de los valores almacenados en la tabla simulation_configuration
        radius_pc = self.config.nebula_radius
        base_density = self.config.particle_density
        morph_type = str(self.config.morphological_type).lower()
        gas_temp = float(self.config.gas_temperature)
        exp_velocity = float(self.config.expansion_velocity)
        mass_loss = float(getattr(self.config, 'mass_loss_rate', 1e-5))
        
        # DETECTA DIVERGENCIA Y SINGULARIDADES
        # NumPy no detiene el programa ante cálculos infinitos. Si la masa es colosal o el radio tiende a cero,
        # se fuerza la excepción antes de saturar la memoria RAM.
        if radius_pc <= 0.0001 or base_density >= 1000000: # Un radio casi nulo (< 0.0001$ pc) o una densidad masiva generan divisiones entre cero o un desbordamiento por la función exponencial (np.exp)
            raise ValueError("Colapso matemático: Relación densidad-radio inestable. Ejecución detenida preventivamente.")
        
        # Convierte el radio de Parsecs a Metros internamente para los cálculos físicos.
        # El 1.5 crea el "límite" o caja espacial donde ocurrirá la simulación.
        limit_m = (radius_pc * self.PARSEC) * 1.5
        grid_points = 30 # Define la resolución volumétrica tridimensional, cuadrícula de 30*30*30 genera 27,000 cálculos matriciales por iteración, suficiente para verse bien en 3D, pero lo bastante bajo para que NumPy lo resuelva en milisegundos sin colapsar la RAM del servidor.
        spatial_step = (limit_m - (-limit_m)) / (grid_points - 1) # Delta X en metros (Paso espacial para diferencias finitas)
        
        # Crea un array con números equidistantes para cada eje 3D (X, Y, Z) (matrices multidimensionales)
        x_axis = np.linspace(-limit_m, limit_m, grid_points)
        y_axis = np.linspace(-limit_m, limit_m, grid_points)
        z_axis = np.linspace(-limit_m, limit_m, grid_points)
        
        # meshgrid entrelaza los 3 ejes para crear una cuadrícula tridimensional
        X_grid, Y_grid, Z_grid = np.meshgrid(x_axis, y_axis, z_axis)

        # ESTADO INICIAL (t=0)
        # Calcula la distancia de cada punto al centro usando el Teorema de Pitágoras en 3D
        R_distance = np.sqrt(X_grid**2 + Y_grid**2 + Z_grid**2)
        core_radius = limit_m * 0.25
        
        # Genera una distribución Gaussiana inicial para la densidad de la nube
        density_matrix = base_density * np.exp(-(R_distance**2) / (core_radius**2))
        
        # Evolución cinemática por diferencias finitas
        time_steps = 25 # Límite de iteraciones en el tiempo, 25 pasos para que el usuario no espere más de 1 segundo en la web
        dt = 3.154e7 * 100 # Delta t: Saltos de 100 años convertidos a segundos
        
        # Garantiza la estabilidad matemática y asegura una expansión visible sin provocar Underflow, Condición de Courant-Friedrichs-Lewy (CFL).
        # la constante de difusión debe ser <= 1/6 (aprox 0.166). Usar 0.15 garantiza que los vectores no diverjan hacia el infinito, manteniendo el fluido estable.
        kinematic_diffusion = (spatial_step**2) * 0.15 / dt
        
        # VECTORES DE SEGUIMIENTO TEMPORAL 2D
        time_history = []         # Tiempo transcurrido en años
        temp_history = []         # Temperatura térmica en Kelvin
        density_history = []      # Nivel de compresión de partículas
        velocity_history = []     # Aceleración/Desaceleración cinemática
        radius_history = []       # Tamaño de la frontera nebular
        mass_loss_history = []    # Expulsión de masa estelar
        
        # Simula el paso del tiempo iteración por iteración, iterar 25 veces en saltos de 100 años simula un lapso de 2,500 años.
        for step in range(time_steps):
            # Matriz temporal para guardar el cálculo del Laplaciano (cambio espacial en las 3 dimensiones)
            laplacian = np.zeros_like(density_matrix) 
            
            # Operaciones vectorizadas de diferencias finitas centrales.
            # NumPy evalúa posiciones vecinas y las divide entre el paso espacial al cuadrado (Delta X^2).
            laplacian[1:-1, :, :] += (density_matrix[2:, :, :] - 2 * density_matrix[1:-1, :, :] + density_matrix[:-2, :, :]) / (spatial_step**2)
            laplacian[:, 1:-1, :] += (density_matrix[:, 2:, :] - 2 * density_matrix[:, 1:-1, :] + density_matrix[:, :-2, :]) / (spatial_step**2)
            laplacian[:, :, 1:-1] += (density_matrix[:, :, 2:] - 2 * density_matrix[:, :, 1:-1] + density_matrix[:, :, :-2]) / (spatial_step**2)
            
            # Actualiza la densidad sumándole la expansión calculada en este salto de tiempo
            density_matrix += dt * kinematic_diffusion * laplacian
            
            # CAPTURA DE DATOS PARA GRÁFICAS 2D
            current_time = step * 100
            time_history.append(current_time)
            current_max_density = np.max(density_matrix)
            density_history.append(current_max_density)
            
            # El radio actual es el borde donde la densidad sigue siendo mayor al 5% del núcleo activo
            active_region = R_distance[density_matrix > (current_max_density * 0.05)] # El gas no tiene un borde sólido; se difumina en el vacío. Físicamente, estableci la "frontera" de la nebulosa donde la densidad cae por debajo del 5% del núcleo activo
            current_radius_pc = np.max(active_region) / self.PARSEC if len(active_region) > 0 else radius_pc
            radius_history.append(current_radius_pc)
            
            # Enfriamiento por expansión adiabática: al expandirse, el gas pierde temperatura cuadráticamente
            expansion_factor = (radius_pc / max(current_radius_pc, 1e-10))**2 # Epsilon: 1e-10
            temp_history.append(gas_temp * expansion_factor)
            
            # Aceleración de vientos estelares (simulando choque de ondas rápidas contra lentas)
            wind_shock = np.exp(-step/5.0) * (exp_velocity * 0.5)
            velocity_history.append(exp_velocity + wind_shock)
            
            # Pulsos térmicos de pérdida de masa (Modulado con onda Seno para simular anillos concéntricos)
            thermal_pulse = np.abs(np.sin(step * 0.8)) * 0.6
            mass_loss_history.append(mass_loss * (1 + thermal_pulse))
        
        # MODELADO MORFOLÓGICO (Perturbaciones angulares)
        # Convierte las coordenadas cartesianas (X, Y, Z) a Esféricas (Ángulos Theta y Phi)
        R_safe = np.where(R_distance == 0, 1e-10, R_distance)
        theta = np.arccos(Z_grid / R_safe)
        phi = np.arctan2(Y_grid, X_grid)
        
        # NUEVO: Interacción con el Medio Interestelar (ISM)
        # El medio interestelar no es un vacío perfecto; ejerce una resistencia cinemática (fricción).
        # Simulamos una mayor densidad de polvo en el plano galáctico (eje ecuatorial) que frena el gas.
        ism_drag = 1.0 - (0.05 * np.abs(np.sin(phi))) 
        density_matrix *= ism_drag
        
        # Deformación de la matriz base usando armónicos esféricos
        if 'elíptica' in morph_type or 'eliptica' in morph_type:
            # Ensancha el ecuador y achata los polos mediante la función Seno
            density_matrix *= 0.5 + 0.5 * (np.sin(theta) ** 2)
        elif 'bipolar' in morph_type:
            # El Coseno al cuadrado estira el gas hacia los polos del eje Z (dos lóbulos)
            density_matrix *= (0.2 + np.abs(np.cos(theta)) ** 2)
        elif 'multipolar' in morph_type:
            # Interferencia de Seno y Coseno que crea patrones en "estrella"
            density_matrix *= (0.2 + np.abs(np.sin(2 * theta) * np.cos(2 * phi)))
        elif 'proto' in morph_type:
            # Concentra la materia en un disco ecuatorial denso simulando una "dona"
            density_matrix *= (0.1 + np.sin(theta) ** 4)
        
        # Normaliza la matriz final a una escala relativa de 0 a 100 para garantizar
        # que Plotly siempre tenga un rango de colores sano
        max_dens = np.max(density_matrix)
        if max_dens > 0:
            density_matrix = (density_matrix / max_dens) * 100 
            
        # Filtro de optimización: Limpia el "vacío espacial" (densidades menores al 5%)
        density_matrix[density_matrix < 5] = 0
        valid_indices = density_matrix.flatten() > 5
        
        # PREPARACIÓN DE DATAFRAMES PARA EXPORTACIÓN A EXCEL
        # Dataframe 1: Representación de la cuadrícula tridimensional filtrada
        df_export = pd.DataFrame({
            'Eje X (pc)': (X_grid / self.PARSEC).flatten()[valid_indices],
            'Eje Y (pc)': (Y_grid / self.PARSEC).flatten()[valid_indices],
            'Eje Z (pc)': (Z_grid / self.PARSEC).flatten()[valid_indices],
            'Densidad (%)': density_matrix.flatten()[valid_indices]
        })
        
        # Dataframe 2: Ficha técnica de la receta simulada
        df_params = pd.DataFrame({
            'Parámetro': ['Nombre', 'Morfología', 'Radio (pc)', 'Densidad base', 'Temperatura (K)', 'Velocidad (km/s)'],
            'Valor': [self.config.configuration_name, self.config.morphological_type, radius_pc, base_density, gas_temp, exp_velocity]
        })

        # Dataframe 3: Evolución de las gráficas cronológicas
        df_evolution = pd.DataFrame({
            'Tiempo (Años)': time_history,
            'Radio Expansión (pc)': radius_history,
            'Temperatura (K)': temp_history,
            'Densidad Max (%)': density_history,
            'Velocidad Viento (km/s)': velocity_history,
            'Pérdida Masa (M☉/yr)': mass_loss_history
        })

        return {
            'X_grid': X_grid, 'Y_grid': Y_grid, 'Z_grid': Z_grid, 'density_matrix': density_matrix,
            'time_history': time_history, 'temp_history': temp_history, 'density_history': density_history,
            'velocity_history': velocity_history, 'radius_history': radius_history, 'mass_loss_history': mass_loss_history,
            'df_export': df_export, 'df_params': df_params, 'df_evolution': df_evolution
        }

    # Renderizado 3D interactivo con Plotly
    def generate_3d_plot(self, data):
        # Construye el objeto volumétrico devolviendo las medidas a Parsecs para su lectura en UI
        fig = go.Figure(data=go.Volume(
            x=(data['X_grid'] / self.PARSEC).flatten(), 
            y=(data['Y_grid'] / self.PARSEC).flatten(), 
            z=(data['Z_grid'] / self.PARSEC).flatten(),
            value=data['density_matrix'].flatten(),
            isomin=5, isomax=100, 
            opacity=0.3,          # Transparencia para simular el gas ionizado
            surface_count=15,     # Cantidad de capas isométricas
            colorscale='Plasma',   # Paleta de colores astronómica
            # Título explícito en la barra de colores.
            colorbar=dict(
                title=dict(
                    text='Densidad (%)',
                    side='right',
                    font=dict(color='white', size=14)
                ),
                tickfont=dict(color='white')
            )
        ))
        
        fig.update_layout(
            title=f"Simulation: {self.config.configuration_name}",
            scene=dict(xaxis_title='X (pc)', yaxis_title='Y (pc)', zaxis_title='Z (pc)'),
            template="plotly_dark", 
            margin=dict(l=0, r=0, b=0, t=40)
        )
        
        data['fig'] = fig # Guarda la figura nativa para exportarla a PNG/PDF/JPG posteriormente
        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    # Esta funcion renderiza gráficas estáticas 2D con Matplotlib
    def generate_2d_plots(self, data):
        # Función auxiliar para estandarizar la creación de gráficas y evitar redundancia.
        # El parámetro 'is_log' (booleano) es para alternar dinámicamente entre escala lineal y logarítmica.
        def plot_base64(x_data, y_data, title, x_label, y_label, line_color, is_log=False):
            fig_2d, ax = plt.subplots(figsize=(8, 4))
            
            # Armonización de colores oscuros para combinar con la paleta de la interfaz web
            fig_2d.patch.set_facecolor('#111111')
            ax.set_facecolor('#111111')
            
            # Trazado de la línea principal con marcadores para delimitar los saltos temporales (100 años)
            ax.plot(x_data, y_data, color=line_color, marker='o', markersize=4, linewidth=2)
            
            # --- LÓGICA DE ESCALA LOGARÍTMICA ---
            # Si is_log es Verdadero, transforma matemáticamente el eje Y a una escala exponencial.
            # Esto es vital en astrofísica para observar variables que decaen drásticamente en el vacío.
            if is_log:
                ax.set_yscale('log')
                title += " (Escala Logarítmica)"
            
            # Configuración estética de etiquetas, títulos, fuentes y cuadrícula (grid)
            ax.set_title(title, color='white', pad=15)
            ax.set_xlabel(x_label, color='white')
            ax.set_ylabel(y_label, color=line_color)
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', labelcolor=line_color)
            ax.tick_params(axis='x', colors='white', which='both') # which='both' fuerza a que tanto los números principales como la notación científica logarítmica tomen el color brillante
            ax.tick_params(axis='y', colors=line_color, labelcolor=line_color, which='both')
            ax.yaxis.get_offset_text().set_color(line_color) # Fuerza el color del texto de la base logarítmica (ej. el "10" en 10^1)
            ax.grid(color='#333333', linestyle='-', linewidth=0.5)
            fig_2d.tight_layout()
            
            # Serialización en memoria RAM y codificación a formato Base64 para inyección HTML segura
            buf = io.BytesIO()
            plt.savefig(buf, format='png', facecolor=fig_2d.get_facecolor(), edgecolor='none')
            buf.seek(0)
            encoded = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig_2d) # Cierre explícito de la figura para liberar la memoria del servidor de Django
            
            return f'<img src="data:image/png;base64,{encoded}" alt="{title}" class="img-fluid rounded shadow w-100">'

        # Retorna un diccionario multidimensional separando las gráficas por tipo de escala (Lineal vs Log).
        # Esto permite enviar todas las versiones pre-generadas desde el backend hacia el frontend en una sola petición.
        return {
            'linear': {
                'temp': plot_base64(data['time_history'], data['temp_history'], 'T vs t: Decaimiento Térmico', 'Tiempo (Años)', 'Temperatura (K)', '#ff5555'),
                'density': plot_base64(data['time_history'], data['density_history'], 'ρ vs t: Dispersión de Partículas', 'Tiempo (Años)', 'Densidad (%)', '#a020f0'),
                'velocity': plot_base64(data['time_history'], data['velocity_history'], 'v vs t: Cinemática Estelar', 'Tiempo (Años)', 'Velocidad (km/s)', '#ffff00'),
                'radius': plot_base64(data['time_history'], data['radius_history'], 'R vs t: Expansión Espacial', 'Tiempo (Años)', 'Radio (pc)', '#00ffcc'),
                'mass': plot_base64(data['time_history'], data['mass_loss_history'], 'Ṁ vs t: Pulsos de Masa', 'Tiempo (Años)', 'Pérdida de Masa (M☉/yr)', '#ffaa00')
            },
            'log': {
                'temp': plot_base64(data['time_history'], data['temp_history'], 'T vs t: Decaimiento Térmico', 'Tiempo (Años)', 'Temperatura (K)', '#ff5555', True),
                'density': plot_base64(data['time_history'], data['density_history'], 'ρ vs t: Dispersión de Partículas', 'Tiempo (Años)', 'Densidad (%)', '#a020f0', True),
                'velocity': plot_base64(data['time_history'], data['velocity_history'], 'v vs t: Cinemática Estelar', 'Tiempo (Años)', 'Velocidad (km/s)', '#ffff00', True),
                'radius': plot_base64(data['time_history'], data['radius_history'], 'R vs t: Expansión Espacial', 'Tiempo (Años)', 'Radio (pc)', '#00ffcc', True),
                'mass': plot_base64(data['time_history'], data['mass_loss_history'], 'Ṁ vs t: Pulsos de Masa', 'Tiempo (Años)', 'Pérdida de Masa (M☉/yr)', '#ffaa00', True)
            }
        }