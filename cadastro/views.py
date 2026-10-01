import calendar
from datetime import date, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Animal, Vaccine, Weighing
from .forms import AnimalForm, UserCreateForm, UserPasswordForm, VaccineBatchForm, VaccineForm, WeighingForm


def _pending_events():
    """Doses ainda não aplicadas (agendadas ou atrasadas), da mais antiga para a mais nova."""
    events = []
    qs = Vaccine.objects.select_related('animal').filter(
        Q(applied=False) | Q(second_dose=True, second_dose_applied=False)
    )
    for vaccine in qs:
        events.extend(e for e in vaccine.dose_events() if not e['done'])
    return sorted(events, key=lambda e: e['date'])


def animal_list(request):
    all_animals = Animal.objects.all()
    animals = all_animals.order_by('ear_tag_number')
    q = request.GET.get('q', '').strip()
    sex = request.GET.get('sex', '')
    if q:
        animals = animals.filter(
            Q(ear_tag_number__icontains=q) | Q(mother_ear_tag_number__icontains=q)
        )
    if sex in ('M', 'F'):
        animals = animals.filter(sex=sex)
    page = Paginator(animals, 20).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)
    pending = _pending_events()
    scheduled_count = sum(1 for e in pending if e['status'] == 'scheduled')
    overdue_count = sum(1 for e in pending if e['status'] == 'overdue')
    return render(request, 'animal_list.html', {
        'page': page,
        'q': q,
        'sex': sex,
        'querystring': params.urlencode(),
        'total': all_animals.count(),
        'males': all_animals.filter(sex='M').count(),
        'females': all_animals.filter(sex='F').count(),
        'scheduled_count': scheduled_count,
        'overdue_count': overdue_count,
    })


def animal_create(request):
    if request.method == 'POST':
        form = AnimalForm(request.POST)
        if form.is_valid():
            animal = form.save()
            return redirect('animal_detail', pk=animal.pk)
    else:
        form = AnimalForm()
    return render(request, 'animal_form.html', {'form': form, 'is_edit': False})


def animal_detail(request, pk):
    animal = get_object_or_404(Animal, pk=pk)
    vaccines = animal.vaccine_set.all()
    weights = animal.weighings.order_by('-weigh_date')
    return render(
        request,
        'animal_detail.html',
        {'animal': animal, 'vaccines': vaccines, 'weights': weights, 'stats': animal.weight_stats()},
    )


def vaccine_create(request, animal_pk):
    animal = get_object_or_404(Animal, pk=animal_pk)
    if request.method == 'POST':
        form = VaccineForm(request.POST)
        if form.is_valid():
            vaccine = form.save(commit=False)
            vaccine.animal = animal
            vaccine.save()
            return redirect('animal_detail', pk=animal.pk)
    else:
        form = VaccineForm()
    return render(request, 'vaccine_form.html', {'form': form, 'animal': animal, 'is_edit': False})


def vaccine_edit(request, animal_pk, pk):
    vaccine = get_object_or_404(Vaccine, pk=pk, animal_id=animal_pk)
    if request.method == 'POST':
        form = VaccineForm(request.POST, instance=vaccine)
        if form.is_valid():
            form.save()
            return redirect('animal_detail', pk=animal_pk)
    else:
        form = VaccineForm(instance=vaccine)
    return render(request, 'vaccine_form.html', {'form': form, 'animal': vaccine.animal, 'is_edit': True})


def vaccine_delete(request, animal_pk, pk):
    vaccine = get_object_or_404(Vaccine, pk=pk, animal_id=animal_pk)
    if request.method == 'POST':
        vaccine.delete()
        return redirect('animal_detail', pk=animal_pk)
    return render(request, 'vaccine_confirm_delete.html', {'vaccine': vaccine})


def weighing_create(request, animal_pk):
    animal = get_object_or_404(Animal, pk=animal_pk)
    if request.method == 'POST':
        form = WeighingForm(request.POST, animal=animal)
        if form.is_valid():
            weighing = form.save(commit=False)
            weighing.animal = animal
            weighing.save()
            return redirect('animal_detail', pk=animal.pk)
    else:
        form = WeighingForm(animal=animal)
    return render(
        request,
        'weighing_form.html',
        {'form': form, 'animal': animal, 'is_edit': False},
    )


def weighing_edit(request, animal_pk, pk):
    weighing = get_object_or_404(Weighing, pk=pk, animal_id=animal_pk)
    if request.method == 'POST':
        form = WeighingForm(request.POST, instance=weighing)
        if form.is_valid():
            form.save()
            return redirect('animal_detail', pk=animal_pk)
    else:
        form = WeighingForm(instance=weighing)
    return render(
        request,
        'weighing_form.html',
        {'form': form, 'animal': weighing.animal, 'is_edit': True},
    )


def weighing_delete(request, animal_pk, pk):
    weighing = get_object_or_404(Weighing, pk=pk, animal_id=animal_pk)
    if request.method == 'POST':
        weighing.delete()
        return redirect('animal_detail', pk=animal_pk)
    return render(request, 'weighing_confirm_delete.html', {'weighing': weighing})


def animal_edit(request, pk):
    animal = get_object_or_404(Animal, pk=pk)
    if request.method == 'POST':
        form = AnimalForm(request.POST, instance=animal)
        if form.is_valid():
            form.save()
            return redirect('animal_detail', pk=animal.pk)
    else:
        form = AnimalForm(instance=animal)
    return render(request, 'animal_form.html', {'form': form, 'animal': animal, 'is_edit': True})


def animal_delete(request, pk):
    animal = get_object_or_404(Animal, pk=pk)
    if request.method == 'POST':
        animal.delete()
        return redirect('animal_list')
    return render(request, 'animal_confirm_delete.html', {'animal': animal})


# --- Gerenciamento de usuários (somente superusuário) ---

def superuser_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


@superuser_required
def user_list(request):
    users = get_user_model().objects.order_by('username')
    return render(request, 'user_list.html', {'users': users})


@superuser_required
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f'Usuário "{user.username}" criado.')
        return redirect('user_list')
    return render(request, 'user_form.html', {'form': form, 'title': 'Novo usuário'})


@superuser_required
def user_password(request, pk):
    target = get_object_or_404(get_user_model(), pk=pk)
    form = UserPasswordForm(target, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        if target.pk == request.user.pk:
            update_session_auth_hash(request, target)
        messages.success(request, f'Senha de "{target.username}" alterada.')
        return redirect('user_list')
    return render(request, 'user_form.html', {
        'form': form, 'title': f'Trocar senha de {target.username}',
    })


@superuser_required
def user_delete(request, pk):
    target = get_object_or_404(get_user_model(), pk=pk)
    blocked = None
    if target.pk == request.user.pk:
        blocked = 'Você não pode excluir o próprio usuário.'
    elif target.is_superuser and get_user_model().objects.filter(is_superuser=True).count() <= 1:
        blocked = 'Não é possível excluir o único administrador.'
    if request.method == 'POST':
        if blocked:
            messages.error(request, blocked)
        else:
            target.delete()
            messages.success(request, f'Usuário "{target.username}" excluído.')
        return redirect('user_list')
    return render(request, 'user_confirm_delete.html', {'target': target, 'blocked': blocked})


# --- Vacinas: calendário, lote e baixa de dose ---

MONTHS_PT = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho',
             'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']


def vaccine_calendar(request):
    today = date.today()
    try:
        first = date(int(request.GET.get('year', today.year)), int(request.GET.get('month', today.month)), 1)
    except (TypeError, ValueError, OverflowError):
        first = today.replace(day=1)
    weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(first.year, first.month)
    start, end = weeks[0][0], weeks[-1][-1]

    vaccines = Vaccine.objects.select_related('animal').filter(
        Q(application_date__range=(start, end)) | Q(second_dose_date__range=(start, end))
    )
    by_day = {}
    for vaccine in vaccines:
        for event in vaccine.dose_events():
            if start <= event['date'] <= end:
                by_day.setdefault(event['date'], []).append(event)

    grid = [
        [{'day': d, 'in_month': d.month == first.month, 'is_today': d == today,
          'events': by_day.get(d, [])} for d in week]
        for week in weeks
    ]
    agenda = sorted(
        (e for evs in by_day.values() for e in evs if e['date'].month == first.month),
        key=lambda e: e['date'],
    )
    pending = _pending_events()
    return render(request, 'vaccine_calendar.html', {
        'grid': grid,
        'agenda': agenda,
        'title': f'{MONTHS_PT[first.month - 1]} de {first.year}',
        'prev': (first - timedelta(days=1)).replace(day=1),
        'next': (first + timedelta(days=32)).replace(day=1),
        'overdue': [e for e in pending if e['status'] == 'overdue'],
        'upcoming': [e for e in pending if e['status'] == 'scheduled'][:15],
        'weekdays': ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'],
    })


def vaccine_batch(request):
    form = VaccineBatchForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        created = form.save()
        messages.success(request, f'Vacina cadastrada para {len(created)} animal(is).')
        return redirect('vaccine_calendar')
    return render(request, 'vaccine_batch.html', {'form': form})


@require_POST
def vaccine_mark_done(request, animal_pk, pk, dose):
    vaccine = get_object_or_404(Vaccine, pk=pk, animal_id=animal_pk)
    if dose == 1:
        vaccine.applied = True
    elif dose == 2 and vaccine.second_dose:
        vaccine.second_dose_applied = True
        vaccine.applied = True
    else:
        raise Http404
    vaccine.save()
    messages.success(request, f'{vaccine.name} ({dose}ª dose) marcada como aplicada.')
    nxt = request.POST.get('next', '')
    if not nxt.startswith('/') or nxt.startswith('//'):
        nxt = reverse('vaccine_calendar')
    return redirect(nxt)
