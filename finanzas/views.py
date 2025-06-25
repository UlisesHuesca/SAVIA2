from django.shortcuts import render
from user.models import Profile
from .forms import ExhibitForm
from .models import Exhibit

# Create your views here.
def crear_exhibit(request):
    """
    Vista para crear un Exhibit.
    """
    pk_perfil = request.session.get('selected_profile_id')
    colaborador = Profile.objects.all()
    usuario = colaborador.get(id = pk_perfil)

    form = ExhibitForm()

    if request.method == 'POST':
        # Aquí iría la lógica para procesar el formulario y crear el Exhibit
        pass
    

    context = {
        'form': form,
        'usuario':usuario,
        
    }

    # Renderizar el formulario de creación de Exhibit
    return render(request, 'finanzas/crear_exhibit.html', context)