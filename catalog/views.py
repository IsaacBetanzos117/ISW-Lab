from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect
from .models import Scientific_reference
from .forms import ScientificReferenceForm

# Función auxiliar de validación de seguridad (RBAC), verifica si el usuario autenticado pertenece al grupo de Docente/Divulgador o Administrador.
# Sirve como primer filtro para bloquear el acceso de los Estudiantes a las vistas de modificación.
def is_teacher_or_admin(user):
    return user.groups.filter(name__in=['Docente/Divulgador', 'Administrador']).exists()

# FN5: Esta clase renderiza el formulario para registrar una nueva ficha bibliográfica en la base de datos restringida exclusivamente para usuarios con rol de Docente/Divulgador o Administrador.
class ReferenceCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Scientific_reference
    form_class = ScientificReferenceForm
    template_name = 'reference_crud/reference_form.html'
    success_url = reverse_lazy('reference_list')

    # Método del UserPassesTestMixin que actúa como la primera capa de seguridad, si retorna False (ej. es un Estudiante), Django bloquea el acceso con un error 403.
    def test_func(self):
        return is_teacher_or_admin(self.request.user)

    # Este metodo intercepta la carga inicial de la página (GET) para protegerla de caídas del servidor al intentar renderizar el formulario.
    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, f"Error al cargar el formulario: {str(e)}")
            return redirect('reference_list')

    # Este metodo inyecta títulos al HTML
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action_title'] = 'Crear Nueva Referencia'
        context['button_text'] = 'Guardar Ficha'
        return context

    # Método que se ejecuta cuando el usuario presiona el botón de guardar, asigna automáticamente al usuario actual como el 'autor' de la ficha antes de guardarla 
    # y maneja cualquier error de base de datos durante el proceso.
    def form_valid(self, form):
        try:
            form.instance.author = self.request.user
            messages.success(self.request, "Referencia creada exitosamente.")
            
            return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f"Error al guardar en la base de datos: {str(e)}")
            
            return self.form_invalid(form)

# FN5: Renderiza la vista principal donde se muestran todas las fichas bibliográficas registradas en el sistema.
# Es de solo lectura, por lo que es accesible tanto para Estudiantes como para Docente/Divulgador.
class ReferenceListView(LoginRequiredMixin, ListView):
    model = Scientific_reference
    template_name = 'reference_crud/reference_list.html'
    context_object_name = 'references'

    # Este método consulta la BD para obtener los registros, los ordena de manera descendente e incluye un bloque try/except para evitar que la página colapse si hay un fallo en la BD.
    def get_queryset(self):
        try:
            return Scientific_reference.objects.all().order_by('-created_at')
        except Exception as e:
            messages.error(self.request, f"Error al cargar el catálogo: {str(e)}")
            return Scientific_reference.objects.none()

    # Este método que inyecta variables adicionales al diccionario que viaja hacia la plantilla HTML, wnvía la variable 'is_teacher_or_admin' para que el frontend sepa si debe mostrar u ocultar los botones de acción dependiendo del rol del usuario.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_teacher_or_admin'] = is_teacher_or_admin(self.request.user)
        return context

# FN5: Esta clase renderiza una vista enfocada en mostrar toda la información detallada de una sola nebulosa, al igual que la lista, es de solo lectura y accesible para todos los usuarios autenticados.
class ReferenceDetailView(LoginRequiredMixin, DetailView):
    model = Scientific_reference
    template_name = 'reference_crud/reference_detail.html'
    context_object_name = 'reference'

    # Este método intercepta la petición HTTP de la página, sirve como escudo: si el usuario ingresa un ID en la URL de una ficha que no existe (404) o si ocurre un error, lo captura y lo redirige de vuelta al catálogo con un mensaje limpio.
    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Http404:
            messages.error(request, "La referencia científica que buscas no existe o fue eliminada.")
            return redirect('reference_list')
        except Exception as e:
            messages.error(request, f"Error al cargar la referencia: {str(e)}")
            return redirect('reference_list')

    # Este método es para enviar variables extra al HTML.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_teacher_or_admin'] = is_teacher_or_admin(self.request.user)
        return context

# FN5: Esta clase renderiza el formulario pre-poblado con los datos de una ficha existente para ser modificada, 
# Restringida a Docentes/Divulgadores y Administradores, e incluye validación de propiedad (solo el autor puede editar).
class ReferenceUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Scientific_reference
    form_class = ScientificReferenceForm
    template_name = 'reference_crud/reference_form.html'
    success_url = reverse_lazy('reference_list')

    # Este metodo es la primera capa de seguridad: Verifica que el usuario no sea un Estudiante.
    def test_func(self):
        return is_teacher_or_admin(self.request.user)

    # Este metodo es la segunda capa de seguridad: Recupera el objeto a editar y verifica quién es el autor.
    # Si un docente intenta editar la ficha de otro, levanta una excepción de Permiso Denegado, los Administradores tienen un pase libre para editar cualquier registro.
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.author != self.request.user and not self.request.user.groups.filter(name='Administrador').exists():
            raise PermissionDenied("No tienes permiso para editar una referencia que no creaste.")
        return obj

    # ESte metodo es el escudo frontal para la carga de la página. Captura el 404 (si la ficha ya no existe) 
    # o el error de Permiso Denegado (si no es el autor) y redirige al usuario de forma amigable.
    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except (Http404, PermissionDenied) as e:
            messages.error(request, str(e))
            return redirect('reference_list')
        except Exception as e:
            messages.error(request, f"Error inesperado: {str(e)}")
            return redirect('reference_list')

    # Esta funcion cambia los textos de la plantilla para que se adapten al contexto de "Edición".
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action_title'] = 'Editar Referencia'
        context['button_text'] = 'Actualizar Ficha'
        return context

    # Esta funcion valida y guarda los cambios hechos en el formulario, capturando errores de base de datos.
    def form_valid(self, form):
        try:
            messages.success(self.request, "Referencia actualizada correctamente.")
            return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f"Error al actualizar: {str(e)}")
            return self.form_invalid(form)

# FN5: Esta clase muestra una pantalla de confirmación para borrar un registro permanentemente, aplica las mismas restricciones de roles y propiedad que la vista de actualización.
class ReferenceDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Scientific_reference
    template_name = 'reference_crud/reference_delete.html'
    success_url = reverse_lazy('reference_list')

    # Esta funcion es la primera capa de seguridad: Bloquea a Estudiantes.
    def test_func(self):
        return is_teacher_or_admin(self.request.user)

    # Esta funcion es la segunda capa de seguridad: Evita que un docente elimine el trabajo de otro.
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.author != self.request.user and not self.request.user.groups.filter(name='Administrador').exists():
            raise PermissionDenied("No tienes permiso para eliminar una referencia que no creaste.")
        return obj

    # Esta funcion captura intentos de eliminar registros inexistentes o protegidos, redirigiendo al catálogo.
    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except (Http404, PermissionDenied) as e:
            messages.error(request, str(e))
            return redirect('reference_list')
        except Exception as e:
            messages.error(request, f"Error inesperado: {str(e)}")
            return redirect('reference_list')

    # Esta funcion ejecuta el borrado real en la base de datos tras la confirmación del usuario.
    def form_valid(self, form):
        try:
            messages.success(self.request, "Referencia eliminada de forma permanente.")
            return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f"Error crítico al eliminar: {str(e)}")
            return redirect('reference_list')