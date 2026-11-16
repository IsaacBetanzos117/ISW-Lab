from django.db.models import Q # La clase Q es para construir consultas complejas con operadores lógicos (AND, OR, NOT) en Django ORM
from django.http import Http404
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import DeleteView, DetailView, ListView, CreateView, UpdateView
from simulador.models import Simulation_history
from .models import Academic_group
from .forms import AcademicGroupForm
from django.shortcuts import get_object_or_404

# TODO: PROVOCAR ERROR 404, cambiar a produccion



# Esta clase se encargada de mostrar la lista de grupos académicos, los docentes ven solo sus grupos; los administradores ven todos.
# Los estudiantes no tienen acceso a esta vista administrativa.
class AcademicGroupListView(LoginRequiredMixin, ListView):
    model = Academic_group
    template_name = 'groups/groups_crud/groups_list.html'
    context_object_name = 'groups'
        
    # Metodo que sobrescribe la consulta a la BD por defecto, si es Administrador, devuelve todos los registros. Si no, filtra por el docente logueado.
    def get_queryset(self):
        try:
            is_admin = self.request.user.groups.filter(name='Administrador').exists()
            is_teacher = self.request.user.groups.filter(name='Docente/Divulgador').exists()
            query = self.request.GET.get('q', '').strip() # Captura lo escrito en el buscador
            
            # Filtro base por rol (Seguridad)
            if is_admin:
                queryset = Academic_group.objects.all()
            elif is_teacher:
                queryset = Academic_group.objects.filter(teacher=self.request.user)
            else: # Si no es admin ni docente, es estudiante.
                queryset = Academic_group.objects.filter(students=self.request.user)
            
            # Filtro de búsqueda dinámica (Nombre del grupo o username del docente)
            if query:
                queryset = queryset.filter(
                    Q(class_name__icontains=query) | Q(teacher__username__icontains=query) # Permite buscar por nombre de grupo o por username del docente, __icontains ignora mayúsculas y minúsculas
                ).distinct() # Elimina registros duplicados en los resultados
            
            return queryset
        except Exception:
            raise Http404("No se pudieron cargar los grupos académicos.")


# Esta clase se encargada de procesar el formulario de creación de un nuevo grupo, con acceso permitido únicamente para Docentes y Administradores.
class AcademicGroupCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Academic_group
    form_class = AcademicGroupForm
    template_name = 'groups/groups_crud/groups_form.html'
    success_url = reverse_lazy('group_list')

    # Método de seguridad que restringe el acceso a la URL de creación.
    def test_func(self):
        try:
            is_teacher = self.request.user.groups.filter(name='Docente/Divulgador').exists()
            is_admin = self.request.user.groups.filter(name='Administrador').exists()
            return is_teacher or is_admin
        except Exception:
            raise Http404("Error al verificar los permisos de creación.")
    
    # Metodo que intercepta el objeto antes de guardarlo en la BD para inyectar automáticamente al usuario logueado en el campo 'teacher'.
    def form_valid(self, form):
        try:
            form.instance.teacher = self.request.user
            messages.success(self.request, "Grupo académico creado exitosamente.")
            return super().form_valid(form)
        except Exception:
            raise Http404("Ocurrió un error al intentar guardar el grupo.")


# Esta clase se encargada de editar un grupo existente (ej. cambiar nombre o agregar alumnos), reutiliza el mismo formulario y plantilla que la vista de creación.
class AcademicGroupUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Academic_group
    form_class = AcademicGroupForm
    template_name = 'groups/groups_crud/groups_form.html'
    success_url = reverse_lazy('group_list')

    # Método de seguridad a nivel de objeto que permite el acceso si el usuario es el dueño del grupo o si tiene el rol de Administrador.
    def test_func(self):
        try:
            grupo = self.get_object()
            is_admin = self.request.user.groups.filter(name='Administrador').exists()
            return self.request.user == grupo.teacher or is_admin
        except Exception:
            # Si el grupo no existe o falla la consulta, muestra la página 404
            raise Http404("El grupo solicitado no existe o no tienes permisos para editarlo.")
    
    # Se ejecuta al enviar el formulario de edición válido para emitir un mensaje de éxito.
    def form_valid(self, form):
        try:
            messages.success(self.request, "Lista de estudiantes y datos del grupo actualizados.")
            return super().form_valid(form)
        except Exception:
            raise Http404("Ocurrió un error al intentar actualizar el grupo.")

# Clase que se encarg de eliminar un grupo existente.
class AcademicGroupDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Academic_group
    template_name = 'groups/groups_crud/groups_confirm_delete.html'
    success_url = reverse_lazy('group_list')
    
    # Método de seguridad a nivel de objeto que permite el acceso si el usuario es el dueño del grupo o si tiene el rol de Administrador.
    def test_func(self):
        try:
            grupo = self.get_object()
            is_admin = self.request.user.groups.filter(name='Administrador').exists()
            return self.request.user == grupo.teacher or is_admin
        except Exception:
            raise Http404("El grupo no existe o no tienes permisos para eliminarlo.")
    
    # Se ejecuta al enviar el formulario de eliminación válido para emitir un mensaje de éxito.
    def form_valid(self, form):
        try:
            messages.success(self.request, "Grupo académico eliminado exitosamente.")
            return super().form_valid(form)
        except Exception:
            raise Http404("Error al intentar eliminar el grupo.")

# Esta clase se encargada de mostrar la lista de simulaciones asociadas a los estudiantes de un grupo académico específico.
class GroupSimulationListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Simulation_history 
    template_name = 'groups/group_simulations.html'
    context_object_name = 'history_records'
    
    # Este método determina si el usuario tiene permiso para ver la lista de simulaciones del grupo académico.
    def test_func(self):
        grupo = get_object_or_404(Academic_group, pk=self.kwargs['pk'])
        is_admin = self.request.user.groups.filter(name='Administrador').exists()
        is_teacher = self.request.user == grupo.teacher
        return is_admin or is_teacher
    
    # Este método sobrescribe la consulta por defecto para filtrar el historial de simulaciones y traer solo las simulaciones de los alumnos del grupo académico específico.
    def get_queryset(self):
        grupo = get_object_or_404(Academic_group, pk=self.kwargs['pk'])
        
        # Filtra el historial para traer solo las simulaciones de los alumnos de esta clase
        return Simulation_history.objects.filter(
            configuration__author__in=grupo.students.all()
        ).order_by('-calculated_at')


# Esta clase se encargada de mostrar los detalles de un grupo académico específico, incluyendo su nombre, docente y lista de estudiantes.
class AcademicGroupDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Academic_group
    template_name = 'groups/groups_crud/groups_detail.html'
    context_object_name = 'group'
    
    # Este método determina si el usuario tiene permiso para ver los detalles del grupo
    def test_func(self):
        try:
            group = self.get_object() # Obtiene el grupo académico actual basado en la URL (pk)
            is_admin = self.request.user.groups.filter(name='Administrador').exists()
            is_teacher = self.request.user == group.teacher # Verifica si el usuario logueado es el docente del grupo
            is_student = self.request.user in group.students.all() # Verifica si el usuario logueado es uno de los estudiantes del grupo
            
            return is_admin or is_teacher or is_student
        except Exception:
            raise Http404("El grupo no existe o no tienes acceso a esta clase.")
    
    # Este método sobrescribe el contexto de la vista para guardar el ID del grupo en la sesión del usuario, lo que permite recordar la última clase visitada.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Guarda el ID exacto de la clase en la sesión del usuario
        self.request.session['ultimo_grupo_id'] = self.object.pk
        return context