from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Academic_group(models.Model):
    class_name = models.CharField(max_length=100, verbose_name='Nombre de la clase')
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teaching_groups', verbose_name="Nombre del maestro")
    students = models.ManyToManyField(User, through='Student_group', related_name='enrolled_groups', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.class_name}, {self.teacher.username}"

class Student_group(models.Model):
    group = models.ForeignKey(Academic_group, on_delete=models.CASCADE, verbose_name="Nombre del grupo")
    student = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Nombre del estudiante")
    
    def __str__(self):
        return f"{self.group.class_name}, {self.student.username}"