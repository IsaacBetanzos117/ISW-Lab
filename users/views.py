from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.mail import send_mail
from django.urls import reverse_lazy # para evitar errores si la ruta cambia en el futuro
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.models import User
from config import settings
from .forms import UserRegistrationForm, UserUpdateForm
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.template.loader import render_to_string
from django.contrib.auth.models import Group
from django.http import Http404
from django.shortcuts import redirect
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.decorators import login_required

# Create your views here.
# Esta clase o vista se encarga de crear un nuevo usuario, y enviar un correo de bienvenida al mismo.
class UserCreateView(CreateView):
    model = User # SELECT * FROM auth_user
    template_name = 'users/crud/user_form.html'
    form_class = UserRegistrationForm
    # success_url = reverse_lazy('user_list') # Redirige a la sonsulta de usuarios.
    
    # Esta función se ejecuta antes de guardar el formulario, y se encarga de asignar la contraseña al usuario
    def get_context_data(self, **kwargs): # Se encarga de pasar variables a la plantilla, en este caso el título y el texto del botón
        context = super().get_context_data(**kwargs)
        context['title'] = 'Registrar nuevo usuario.'
        context['text_button'] = 'Crear.'
        
        return context
    
    # Esta función se ejecuta después de guardar el formulario, y se encarga de enviar el correo de bienvenida al usuario.
    def form_valid(self, form):
        try:
            response = super().form_valid(form) # Llama al método form_valid de la clase padre (CreateView) para guardar el formulario y obtener la respuesta HTTP.
            new_user = self.object # Obtiene el usuario que se acaba de crear (CreateView lo guarda en self.object)
            studet_group, created = Group.objects.get_or_create(name='Estudiante') # Obtiene el grupo "Estudiante" o lo crea si no existe
            new_user.groups.add(studet_group) # Agrega el usuario al grupo "Estudiante"
            
            if new_user.email:
                subject = '¡Bienvenido al simulador ISW-Lab!'
                message_html = render_to_string('users/welcome/welcome_email.html', {'user': new_user}) # Se pasa la variable 'new_user' al HTML bajo el nombre 'user'
                message_text = render_to_string('users/welcome/welcome.txt', {'user': new_user})
                sender = getattr(settings, 'DEFAULT_FROM_EMAIL', 'brio231179@upemor.edu.mx') # Obtiene el correo del remitente desde la configuración de Django, si no existe, se usa un correo por defecto.
                recipient = [new_user.email] 
                
                # Se manda el correo
                send_mail(
                    subject=subject,
                    message=message_text,
                    from_email=sender,
                    recipient_list=recipient,
                    html_message=message_html,
                    fail_silently=False # Muestra error en consola si algo falla
                )
                pass # Se encarga de enviar el correo de bienvenida al usuario recién creado. Si algo falla, se muestra un error en la consola.
            
            # Guarda la notificación en memoria
            notifs = cache.get('admin_notifications', [])
            notifs.insert(0, {
                'message': f"Nuevo usuario registrado: {new_user.username} ({new_user.email})",
                'created_at': timezone.localtime().strftime("%d %b %Y, %H:%M")
            })
            cache.set('admin_notifications', notifs[:10], timeout=None) # Cuando alguien se registra, mete el aviso en el buzón
            
            messages.success(self.request, f"Usuario {new_user.username} registrado exitosamente.")
            
            return response # Devuelve la respuesta para que la página redirija al success_url
        except Exception as e:
            messages.error(self.request, f"Ocurrió un error al registrar el usuario: {str(e)}")
            
            return self.form_invalid(form)
    
    # Esta función redirige al login o a la consulta de usuarios dependiendo del tipo de usuario.
    def get_success_url(self):
        if self.request.user.is_authenticated and (self.request.user.is_superuser or self.request.user.groups.filter(name='Administrador').exists()):
            return reverse_lazy('user_list')
        return reverse_lazy('login')

# Esta clase o vista se encarga de mostrar la lista de usuarios, y permite filtrar los superusuarios si el usuario que está haciendo la solicitud no es superusuario.
class UserListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = User # SELECT * FROM auth_user
    template_name = 'users/crud/users_list.html'
    context_object_name = 'users' #  se usa en las vistas genéricas basadas en clases de Django para definir el nombre con el que el objeto estará disponible en la plantilla
    
    # Esta función se encarga de verificar si el usuario que está haciendo la solicitud es superusuario o pertenece al grupo "Administrador"
    def test_func(self):
        is_admin = self.request.user.groups.filter(name='Administrador').exists() # Verifica si el usuario que está haciendo la solicitud pertenece al grupo "Administrador"
        
        return self.request.user.is_superuser or is_admin
    
    # Esta función se encarga de obtener la lista de usuarios que se van a mostrar en la plantilla, y filtra los superusuarios si el usuario que está haciendo la solicitud no es superusuario.
    def get_queryset(self):
        queryset = User.objects.prefetch_related('groups').all() # Obtiene todos los usuarios y sus grupos relacionados, para evitar consultas adicionales a la base de datos.
                
        if not self.request.user.is_superuser: # Si el usuario que está haciendo la solicitud no es superusuario, se filtra la lista de usuarios para que solo muestre los usuarios que pertenecen al mismo grupo que el usuario que está haciendo la solicitud.
            queryset = queryset.filter(is_superuser=False) # Excluye a los superusuarios de la lista de usuarios si el usuario que está haciendo la solicitud no es superusuario.
        
        return queryset

# Esta clase se encarga de manejar la edición de usuarios, y redirigirlos a la página de lista de usuarios si la edición es exitosa.
class UserUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = User
    template_name = 'users/crud/user_form.html'
    form_class = UserUpdateForm
    success_url = reverse_lazy('user_list')
    
    # Esta función se encarga de asignar la contraseña al usuario
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar.'
        context['text_button'] = 'Guardar cambios'
        
        return context
    
    # Esta función se ejecuta antes de guardar el formulario, y se encarga de asignar la contraseña al usuario
    def test_func(self):
        user_to_edit = self.get_object()
        is_admin = self.request.user.groups.filter(name='Administrador').exists() # Verifica si el usuario que está haciendo la solicitud pertenece al grupo "Administrador"
        is_admin =self.request.user.is_superuser or is_admin
        is_same = self.request.user == user_to_edit # Verifica si el usuario que está haciendo la solicitud es el mismo que el usuario que se va a editar
        
        return is_admin or is_same
    
    # Esta función se encarga de verificar si el usuario que se va a editar existe.
    def get(self, request, *args, **kwargs):
        try:
            # Intentamos cargar la página de edición/eliminación de forma normal
            return super().get(request, *args, **kwargs)
        except Http404:
            # Si el registro no existe, atrapamos el 404 en el aire
            messages.warning(request, "El usuario que intentas consultar no existe o ya fue eliminado.")
            
            return redirect('user_list')

    # Esta función se ejecuta después de guardar el formulario, protege la base de datos de errores
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "El usuario ha sido actualizado correctamente.")
            return response
        except Exception as e:
            messages.error(self.request, f"Error al actualizar los datos: {str(e)}")
            return self.form_invalid(form)

# Esta clase se encarga de manejar la eliminación de usuarios, y redirigirlos a la página de lista de usuarios si la eliminación es exitosa.
class UserDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = User
    template_name ='users/crud/delete_user.html'
    success_url = reverse_lazy('user_list')
    
    # Esta función se encarga de verificar si el usuario que está haciendo la solicitud es superusuario o pertenece al grupo "Administrador"
    def test_func(self):
        new_user = self.request.user # Obtiene el usuario que está haciendo la solicitud
        user_to_delete = self.get_object() # Obtiene el usuario que se va a eliminar
        
        if new_user == user_to_delete:
            return False # Si es el mismo, no se permite eliminarse a sí mismo
            
        is_admin_objective = user_to_delete.groups.filter(name='Administrador').exists()
                
        if is_admin_objective and not new_user.is_superuser: # Si el usuario que se va a eliminar es administrador y el usuario que está haciendo la solicitud no es superusuario, no se permite eliminarlo
            return False
            
        is_admin_current = self.request.user.groups.filter(name='Administrador').exists() # Verifica si el usuario que está haciendo la solicitud pertenece al grupo "Administrador"
            
        return self.request.user.is_superuser or is_admin_current
    
    # Esta función se encarga de verificar si el usuario que se va a eliminar existe.
    def get(self, request, *args, **kwargs):
        try:
            # Intenta cargar la página de eliminación de forma normal
            return super().get(request, *args, **kwargs)
        except Http404:
            # Si el registro no existe, atrapamos el 404 en el aire
            messages.warning(request, "El usuario que intentas eliminar no existe o ya fue borrado.")
            
            return redirect('user_list')

    # Esta función se ejecuta al confirmar la eliminación, protege el borrado en la base de datos
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "El usuario fue eliminado permanentemente.")
            
            return response
        except Exception as e:
            messages.error(self.request, f"No se pudo eliminar al usuario por un error del sistema: {str(e)}")
            
            return redirect('user_list')

# Esta clase se encarga de manejar el inicio de sesión de los usuarios, y redirigirlos a la página de lista de usuarios si el inicio de sesión es exitoso.
class UserLoginView(LoginView):
    template_name = 'users/login.html'
    next_page = reverse_lazy('dashboard')
    redirect_authenticated_user = True
    
    # Esta función se encarga de pasar variables a la plantilla, en este caso el título y el texto del botón
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Iniciar sesion'
        
        return context
    
    # Esta función se encarga de mostrar un mensaje de éxito al usuario.
    def form_valid(self, form):
        nombre_usuario = form.get_user().username
        messages.success(self.request, f'Sesión iniciada correctamente. ¡Bienvenido al simulador, {nombre_usuario}!')
        
        return super().form_valid(form)

# Vista dedicada para el perfil del usuario activo
class UserProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'users/profile/my_profile.html'
    success_url = reverse_lazy('my_profile')
    
    # Esta funcion interactúa directamente con el usuario que ha iniciado sesión
    def get_object(self, queryset=None):
        return self.request.user
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Mi cuenta'
        
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Tus datos personales han sido actualizados.")
            
            return response
        except Exception as e:
            messages.error(self.request, f"Ocurrió un error al guardar: {str(e)}")
            
            return self.form_invalid(form)


# Clase encargada del cache para limpiar las notificaciones.
class MarkNotificationsReadView(LoginRequiredMixin, UserPassesTestMixin, View):
    
    # Metodo que filtra para que solo los Administradores reciban la notificacion.
    def test_func(self):
        is_admin = self.request.user.groups.filter(name='Administrador').exists()
        
        return self.request.user.is_superuser or is_admin
    
    # Metodo que borra el cache y redirige al dashboard.
    def get(self, request, *args, **kwargs):
        # Cuando el Administrador hace clic en "Marcar como leídas", vacía el buzón y recarga la página anterior
        cache.delete('admin_notifications') # Se envia a context_processor.py
        
        return redirect(request.META.get('HTTP_REFERER', 'dashboard'))