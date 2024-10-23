from django.db import models

# Create your models here.
class TablaFestivos(models.Model):
    dia_festivo = models.DateField(null=True,db_index=True)

    def __str__(self):
        return f'{self.dia_festivo}'
    