from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Animal, Vaccine, Weighing


class BaseTest(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user('u', password='senha-forte-123')
        self.client.login(username='u', password='senha-forte-123')
        self.animal = Animal.objects.create(
            sex='M', ear_tag_number='A1', mother_ear_tag_number='M1',
            birth_date=date.today() - timedelta(days=400),
        )


class AuthTests(TestCase):
    def test_anonymous_redirected_to_login(self):
        for url in ['/', '/animal/add/', '/animal/1/']:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302)
            self.assertIn('/login/', r['Location'])

    def test_login_page_public(self):
        self.assertEqual(self.client.get('/login/').status_code, 200)


class ListTests(BaseTest):
    def test_search_and_filter(self):
        Animal.objects.create(sex='F', ear_tag_number='B2', mother_ear_tag_number='M9')
        r = self.client.get('/', {'q': 'B2'})
        self.assertEqual([a.ear_tag_number for a in r.context['page']], ['B2'])
        r = self.client.get('/', {'sex': 'M'})
        self.assertEqual([a.ear_tag_number for a in r.context['page']], ['A1'])
        self.assertEqual(r.context['total'], 2)


class FormTests(BaseTest):
    def test_duplicate_ear_tag_rejected(self):
        r = self.client.post('/animal/add/', {'sex': 'F', 'ear_tag_number': 'a1', 'mother_ear_tag_number': 'x'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Animal.objects.count(), 1)

    def test_weighing_before_birth_rejected(self):
        r = self.client.post(
            f'/animal/{self.animal.pk}/weighing/add/',
            {'weigh_date': (self.animal.birth_date - timedelta(days=1)).isoformat(), 'weight': '100'},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Weighing.objects.count(), 0)

    def test_weight_accepts_comma(self):
        self.client.post(
            f'/animal/{self.animal.pk}/weighing/add/',
            {'weigh_date': date.today().isoformat(), 'weight': '250,5'},
        )
        self.assertEqual(Weighing.objects.get().weight, 250.5)


class StatsTests(BaseTest):
    def test_gmd(self):
        d = date.today()
        Weighing.objects.create(animal=self.animal, weigh_date=d - timedelta(days=100), weight=200)
        Weighing.objects.create(animal=self.animal, weigh_date=d, weight=300)
        self.assertEqual(self.animal.weight_stats()['gmd'], 1.0)
        self.assertEqual(self.client.get(f'/animal/{self.animal.pk}/').status_code, 200)

    def test_no_weighings(self):
        self.assertIsNone(self.animal.weight_stats())


class UserManagementTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser('master', password='senha-forte-123')
        self.user = User.objects.create_user('comum', password='senha-forte-123')

    def test_non_superuser_forbidden(self):
        self.client.login(username='comum', password='senha-forte-123')
        for url in ['/usuarios/', '/usuarios/novo/', f'/usuarios/{self.admin.pk}/senha/', f'/usuarios/{self.admin.pk}/excluir/']:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(f'/usuarios/{self.admin.pk}/excluir/').status_code, 403)

    def test_create_user(self):
        self.client.login(username='master', password='senha-forte-123')
        r = self.client.post('/usuarios/novo/', {'username': 'novo', 'password1': 'outra-senha-987', 'password2': 'outra-senha-987'})
        self.assertRedirects(r, '/usuarios/')
        novo = get_user_model().objects.get(username='novo')
        self.assertFalse(novo.is_superuser)

    def test_change_password(self):
        self.client.login(username='master', password='senha-forte-123')
        r = self.client.post(f'/usuarios/{self.user.pk}/senha/', {'new_password1': 'nova-senha-456', 'new_password2': 'nova-senha-456'})
        self.assertRedirects(r, '/usuarios/')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('nova-senha-456'))

    def test_change_own_password_keeps_session(self):
        self.client.login(username='master', password='senha-forte-123')
        self.client.post(f'/usuarios/{self.admin.pk}/senha/', {'new_password1': 'nova-senha-456', 'new_password2': 'nova-senha-456'})
        self.assertEqual(self.client.get('/usuarios/').status_code, 200)

    def test_delete_user(self):
        self.client.login(username='master', password='senha-forte-123')
        self.client.post(f'/usuarios/{self.user.pk}/excluir/')
        self.assertFalse(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_cannot_delete_self(self):
        self.client.login(username='master', password='senha-forte-123')
        self.client.post(f'/usuarios/{self.admin.pk}/excluir/')
        self.assertTrue(get_user_model().objects.filter(pk=self.admin.pk).exists())


class VaccineScheduleTests(BaseTest):
    def make(self, **kw):
        defaults = dict(animal=self.animal, name='Aftosa', application_date=date.today(), applied=True)
        defaults.update(kw)
        return Vaccine.objects.create(**defaults)

    def test_dose_status(self):
        today = date.today()
        v = self.make(
            application_date=today - timedelta(days=10), applied=True,
            second_dose=True, second_dose_date=today - timedelta(days=1), second_dose_applied=False,
        )
        self.assertEqual([e['status'] for e in v.dose_events()], ['done', 'overdue'])
        v2 = self.make(application_date=today + timedelta(days=5), applied=False)
        self.assertEqual([e['status'] for e in v2.dose_events()], ['scheduled'])

    def test_calendar_page_and_navigation(self):
        self.make(application_date=date(2030, 3, 10), applied=False)
        r = self.client.get('/vacinas/calendario/', {'year': 2030, 'month': 3})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Março de 2030')
        self.assertContains(r, 'Aftosa')
        self.assertEqual(self.client.get('/vacinas/calendario/', {'year': 'x', 'month': '99'}).status_code, 200)

    def test_mark_done(self):
        v = self.make(application_date=date.today() + timedelta(days=3), applied=False)
        url = f'/animal/{self.animal.pk}/vaccine/{v.pk}/dose/1/aplicada/'
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        v.refresh_from_db()
        self.assertTrue(v.applied)
        self.assertEqual(self.client.post(f'/animal/{self.animal.pk}/vaccine/{v.pk}/dose/2/aplicada/').status_code, 404)

    def test_mark_done_rejects_external_redirect(self):
        v = self.make(applied=False)
        r = self.client.post(f'/animal/{self.animal.pk}/vaccine/{v.pk}/dose/1/aplicada/', {'next': 'https://evil.example'})
        self.assertEqual(r['Location'], '/vacinas/calendario/')

    def test_batch_schedule(self):
        other = Animal.objects.create(sex='F', ear_tag_number='B2', mother_ear_tag_number='M2')
        r = self.client.post('/vacinas/lote/', {
            'animals': [self.animal.pk, other.pk], 'name': 'Raiva',
            'application_date': (date.today() + timedelta(days=7)).isoformat(),
            'second_dose_date': (date.today() + timedelta(days=37)).isoformat(),
        })
        self.assertRedirects(r, '/vacinas/calendario/')
        self.assertEqual(Vaccine.objects.filter(name='Raiva', applied=False, second_dose=True).count(), 2)

    def test_batch_requires_animals(self):
        r = self.client.post('/vacinas/lote/', {'name': 'Raiva', 'application_date': date.today().isoformat()})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Vaccine.objects.count(), 0)

    def test_second_dose_before_first_rejected(self):
        today = date.today()
        r = self.client.post(f'/animal/{self.animal.pk}/vaccine/add/', {
            'name': 'Raiva', 'application_date': today.isoformat(), 'applied': 'on',
            'second_dose': 'on', 'second_dose_date': (today - timedelta(days=1)).isoformat(),
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Vaccine.objects.count(), 0)

    def test_detail_shows_apply_button(self):
        self.make(application_date=date.today() + timedelta(days=3), applied=False)
        self.assertContains(self.client.get(f'/animal/{self.animal.pk}/'), 'Aplicar 1ª')
