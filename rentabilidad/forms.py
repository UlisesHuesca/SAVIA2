from django import forms
from .models import Solicitud_Costos, Costos, Concepto, Ingresos, Solicitud_Ingresos, Depreciaciones
from datetime import datetime, date

class Solicitud_Costo_Form(forms.ModelForm):
    # Sobrescribimos el campo para poder usar input_formats y controlar la limpieza
    fecha = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'month',
                'class': 'form-control',
                'placeholder': 'MM-YYYY',
            },
            format='%Y-%m',   # usado para renderizar el valor inicial
        ),
        input_formats=['%Y-%m'],  # acepta 'YYYY-MM' desde el POST
        required=True,
        help_text='Selecciona mes y año'
    )

    class Meta:
        model = Solicitud_Costos
        fields = ['distrito','contrato','fecha','tipo'] 

    def clean_fecha(self):
        """
        Garantiza que lo que guarde sea un objeto date válido.
        Si el navegador envía 'YYYY-MM' lo convertimos a 'YYYY-MM-01'.
        """
        # Intentamos tomar el valor ya limpiado (puede venir como date)
        val = self.cleaned_data.get('fecha')
        if isinstance(val, date):
            # ya es una date (posible si input_formats la parseó bien)
            return date(val.year, val.month, 1)

        # Si no, tomamos el valor "raw" enviado por el form (ej: '2025-09')
        raw = self.data.get(self.add_prefix('fecha'))
        if not raw:
            raise forms.ValidationError("Debes seleccionar mes y año.")

        try:
            parsed = datetime.strptime(raw, '%Y-%m')
            return date(parsed.year, parsed.month, 1)
        except ValueError:
            raise forms.ValidationError("Formato de fecha inválido. Usa Mes-Año (YYYY-MM).")
        
class Solicitud_Costo_Indirecto_Form(forms.ModelForm):
    # Sobrescribimos el campo para poder usar input_formats y controlar la limpieza
    fecha = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'month',
                'class': 'form-control',
                'placeholder': 'MM-YYYY',
            },
            format='%Y-%m',   # usado para renderizar el valor inicial
        ),
        input_formats=['%Y-%m'],  # acepta 'YYYY-MM' desde el POST
        required=True,
        help_text='Selecciona mes y año'
    )

    class Meta:
        model = Solicitud_Costos
        fields = ['distrito','fecha','tipo'] 

    def clean_fecha(self):
        """
        Garantiza que lo que guarde sea un objeto date válido.
        Si el navegador envía 'YYYY-MM' lo convertimos a 'YYYY-MM-01'.
        """
        # Intentamos tomar el valor ya limpiado (puede venir como date)
        val = self.cleaned_data.get('fecha')
        if isinstance(val, date):
            # ya es una date (posible si input_formats la parseó bien)
            return date(val.year, val.month, 1)

        # Si no, tomamos el valor "raw" enviado por el form (ej: '2025-09')
        raw = self.data.get(self.add_prefix('fecha'))
        if not raw:
            raise forms.ValidationError("Debes seleccionar mes y año.")

        try:
            parsed = datetime.strptime(raw, '%Y-%m')
            return date(parsed.year, parsed.month, 1)
        except ValueError:
            raise forms.ValidationError("Formato de fecha inválido. Usa Mes-Año (YYYY-MM).")


class Solicitud_Costo_Indirecto_Central_Form(forms.ModelForm):
    # Sobrescribimos el campo para poder usar input_formats y controlar la limpieza
    fecha = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'month',
                'class': 'form-control',
                'placeholder': 'MM-YYYY',
            },
            format='%Y-%m',   # usado para renderizar el valor inicial
        ),
        input_formats=['%Y-%m'],  # acepta 'YYYY-MM' desde el POST
        required=True,
        help_text='Selecciona mes y año'
    )

    class Meta:
        model = Solicitud_Costos
        fields = ['fecha'] 

    def clean_fecha(self):
        """
        Garantiza que lo que guarde sea un objeto date válido.
        Si el navegador envía 'YYYY-MM' lo convertimos a 'YYYY-MM-01'.
        """
        # Intentamos tomar el valor ya limpiado (puede venir como date)
        val = self.cleaned_data.get('fecha')
        if isinstance(val, date):
            # ya es una date (posible si input_formats la parseó bien)
            return date(val.year, val.month, 1)

        # Si no, tomamos el valor "raw" enviado por el form (ej: '2025-09')
        raw = self.data.get(self.add_prefix('fecha'))
        if not raw:
            raise forms.ValidationError("Debes seleccionar mes y año.")

        try:
            parsed = datetime.strptime(raw, '%Y-%m')
            return date(parsed.year, parsed.month, 1)
        except ValueError:
            raise forms.ValidationError("Formato de fecha inválido. Usa Mes-Año (YYYY-MM).")

class Costo_Form(forms.ModelForm):
    class Meta:
        model = Costos
        fields = ['concepto','monto']

class Solicitud_Ingreso_Form(forms.ModelForm):
    # Sobrescribimos el campo para poder usar input_formats y controlar la limpieza
    fecha = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'month',
                'class': 'form-control',
                'placeholder': 'MM-YYYY',
            },
            format='%Y-%m',   # usado para renderizar el valor inicial
        ),
        input_formats=['%Y-%m'],  # acepta 'YYYY-MM' desde el POST
        required=True,
        help_text='Selecciona mes y año'
    )

    class Meta:
        model = Solicitud_Ingresos
        fields = ['distrito','fecha'] 

    def clean_fecha(self):
        """
        Garantiza que lo que guarde sea un objeto date válido.
        Si el navegador envía 'YYYY-MM' lo convertimos a 'YYYY-MM-01'.
        """
        # Intentamos tomar el valor ya limpiado (puede venir como date)
        val = self.cleaned_data.get('fecha')
        if isinstance(val, date):
            # ya es una date (posible si input_formats la parseó bien)
            return date(val.year, val.month, 1)

        # Si no, tomamos el valor "raw" enviado por el form (ej: '2025-09')
        raw = self.data.get(self.add_prefix('fecha'))
        if not raw:
            raise forms.ValidationError("Debes seleccionar mes y año.")

        try:
            parsed = datetime.strptime(raw, '%Y-%m')
            return date(parsed.year, parsed.month, 1)
        except ValueError:
            raise forms.ValidationError("Formato de fecha inválido. Usa Mes-Año (YYYY-MM).")
        
class Ingreso_Form(forms.ModelForm):
    class Meta:
        model = Ingresos
        fields = ['contrato','concepto','monto', 'tipo_cambio','moneda']

class Depreciacion_Form(forms.ModelForm):
    mes_inicial = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'month',
                'class': 'form-control',
                'placeholder': 'MM-YYYY',
            },
            format='%Y-%m',   # usado para renderizar el valor inicial
        ),
        input_formats=['%Y-%m'],  # acepta 'YYYY-MM' desde el POST
        required=True,
        help_text='Selecciona mes y año'
    )

    class Meta:
        model = Depreciaciones
        fields = ['contrato','distrito','concepto','monto','tipo_unidad','mes_inicial','meses_a_depreciar']

    def clean_mes_inicial(self):
        """
        Garantiza que lo que guarde sea un objeto date válido.
        Si el navegador envía 'YYYY-MM' lo convertimos a 'YYYY-MM-01'.
        """
        # Intentamos tomar el valor ya limpiado (puede venir como date)
        val = self.cleaned_data.get('mes_inicial')
        if isinstance(val, date):
            # ya es una date (posible si input_formats la parseó bien)
            return date(val.year, val.month, 1)

        # Si no, tomamos el valor "raw" enviado por el form (ej: '2025-09')
        raw = self.data.get(self.add_prefix('mes_inicial'))
        if not raw:
            raise forms.ValidationError("Debes seleccionar mes y año.")

        try:
            parsed = datetime.strptime(raw, '%Y-%m')
            return date(parsed.year, parsed.month, 1)
        except ValueError:
            raise forms.ValidationError("Formato de fecha inválido. Usa Mes-Año (YYYY-MM).")
