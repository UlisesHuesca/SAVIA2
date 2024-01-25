from django.shortcuts import redirect

def perfil_seleccionado_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        # Verificar si el usuario ha seleccionado un perfil
        selected_profile_id = request.session.get('selected_profile_id')
        if not selected_profile_id:
            return redirect('select-profile')  # Redirige al usuario a la selección de perfil si no lo ha seleccionado
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
 