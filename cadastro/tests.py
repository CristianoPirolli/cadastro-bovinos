from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Animal, Weighing


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
