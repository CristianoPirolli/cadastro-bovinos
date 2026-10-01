from datetime import date

from django import forms
from django.contrib.auth.forms import SetPasswordForm, UserCreationForm
from .models import Animal, Vaccine, Weighing


class AnimalForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = ['sex', 'age', 'ear_tag_number', 'mother_ear_tag_number', 'birth_date']
        widgets = {
            'sex': forms.Select(attrs={'class': 'form-select'}),
            'age': forms.HiddenInput(),
            'ear_tag_number': forms.TextInput(attrs={'class': 'form-control'}),
            'mother_ear_tag_number': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
        labels = {
            'sex': 'Sexo',
            'ear_tag_number': 'Nº do brinco',
            'mother_ear_tag_number': 'Nº do brinco da mãe',
            'birth_date': 'Data de nascimento',
        }


    def clean_ear_tag_number(self):
        tag = self.cleaned_data['ear_tag_number'].strip()
        duplicates = Animal.objects.filter(ear_tag_number__iexact=tag).exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError('Já existe um animal com este número de brinco.')
        return tag

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date and birth_date > date.today():
            raise forms.ValidationError('A data de nascimento não pode ser futura.')
        return birth_date


class WeighingForm(forms.ModelForm):
    weight = forms.CharField(
        label='Peso (kg)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'decimal'}),
    )

    class Meta:
        model = Weighing
        fields = ['weigh_date', 'weight']
        widgets = {
            'weigh_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
        labels = {
            'weigh_date': 'Data de pesagem',
            'weight': 'Peso (kg)',
        }

    def __init__(self, *args, animal=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.animal = animal or getattr(self.instance, 'animal', None)

    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight is None:
            return weight
        try:
            weight = float(str(weight).replace(',', '.'))
        except (TypeError, ValueError):
            raise forms.ValidationError('Informe um número válido para o peso')
        if weight <= 0:
            raise forms.ValidationError('O peso deve ser maior que zero.')
        return weight

    def clean_weigh_date(self):
        weigh_date = self.cleaned_data.get('weigh_date')
        birth = getattr(self.animal, 'birth_date', None)
        if weigh_date and birth and weigh_date < birth:
            raise forms.ValidationError('A pesagem não pode ser anterior ao nascimento.')
        return weigh_date


VACCINE_CHOICES = [
    ('Aftosa', 'Aftosa'),
    ('Brucelose', 'Brucelose'),
    ('Raiva', 'Raiva'),
    ('Carbúnculo', 'Carbúnculo'),
    ('Clostridiose', 'Clostridiose'),
    ('Leptospirose', 'Leptospirose'),
    ('IBR/IPV', 'IBR/IPV'),
    ('BVD', 'BVD'),
    ('Botulismo', 'Botulismo'),
]


class VaccineForm(forms.ModelForm):
    name = forms.ChoiceField(
        choices=VACCINE_CHOICES,
        label='Nome da vacina',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Vaccine
        fields = ['name', 'application_date', 'applied', 'second_dose', 'second_dose_date', 'second_dose_applied']
        widgets = {
            'application_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'applied': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'second_dose': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'second_dose_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'second_dose_applied': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'application_date': 'Data da 1ª dose (aplicada ou programada)',
            'applied': '1ª dose já aplicada?',
            'second_dose': 'Programar segunda dose?',
            'second_dose_date': 'Data da segunda dose',
            'second_dose_applied': '2ª dose já aplicada?',
        }

    def clean(self):
        cleaned_data = super().clean()
        second_dose = cleaned_data.get('second_dose')
        second_dose_date = cleaned_data.get('second_dose_date')
        application_date = cleaned_data.get('application_date')
        if second_dose and not second_dose_date:
            self.add_error('second_dose_date', 'Informe a data da segunda dose')
        if second_dose and second_dose_date and application_date and second_dose_date < application_date:
            self.add_error('second_dose_date', 'A segunda dose não pode ser antes da primeira.')
        if not second_dose:
            cleaned_data['second_dose_date'] = None
            cleaned_data['second_dose_applied'] = False
        if not cleaned_data.get('applied'):
            cleaned_data['second_dose_applied'] = False
        return cleaned_data


class VaccineBatchForm(forms.Form):
    """Programa a mesma vacina para vários animais de uma vez."""
    animals = forms.ModelMultipleChoiceField(
        queryset=Animal.objects.order_by('ear_tag_number'),
        label='Animais',
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        error_messages={'required': 'Selecione ao menos um animal.'},
    )
    name = forms.ChoiceField(
        choices=VACCINE_CHOICES, label='Nome da vacina',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    application_date = forms.DateField(
        label='Data da 1ª dose',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    applied = forms.BooleanField(
        required=False, initial=True, label='1ª dose já aplicada? (desmarque para apenas programar)',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    second_dose_date = forms.DateField(
        required=False, label='Data da segunda dose (opcional)',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        first = cleaned_data.get('application_date')
        second = cleaned_data.get('second_dose_date')
        if first and second and second < first:
            self.add_error('second_dose_date', 'A segunda dose não pode ser antes da primeira.')
        return cleaned_data

    def save(self):
        data = self.cleaned_data
        vaccines = [
            Vaccine(
                animal=animal, name=data['name'], application_date=data['application_date'],
                applied=data['applied'], second_dose=bool(data['second_dose_date']),
                second_dose_date=data['second_dose_date'],
            )
            for animal in data['animals']
        ]
        return Vaccine.objects.bulk_create(vaccines)


def _bootstrapify(form):
    for field in form.fields.values():
        field.widget.attrs.setdefault('class', 'form-control')


class UserCreateForm(UserCreationForm):
    is_superuser = forms.BooleanField(
        required=False, label='Administrador (pode gerenciar usuários)',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta(UserCreationForm.Meta):
        fields = ('username',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'is_superuser':
                field.widget.attrs.setdefault('class', 'form-control')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_superuser = user.is_staff = self.cleaned_data['is_superuser']
        if commit:
            user.save()
        return user


class UserPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _bootstrapify(self)
