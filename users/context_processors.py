# Este archivo sirve para enviar los avisos de la caché a base.html, Django exige que cada context processor registrado
# en settings.py sea una función que reciba request y devuelva un diccionario directamente

from django.core.cache import cache

# Esta funcion es para 
def admin_notifications(request):
    if request.user.is_authenticated and (request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()):
        # Cada vez que el Administrador abre o recarga cualquier página, revisa el buzón con cache.get('admin_notifications', [])
        notifs = cache.get('admin_notifications', [])
        
        return {
            'admin_notifications': notifs[:5],
            'unread_notifications_count': len(notifs),
        }
    return {}