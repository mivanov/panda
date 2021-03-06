#!/usr/bin/env python

from django.contrib.auth.models import Group
from django.conf import settings
from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django.utils import simplejson as json
from tastypie.bundle import Bundle

from panda.api.users import UserValidation
from panda.models import User
from panda.tests import utils

class TestUserValidation(TestCase):
    def setUp(self):
        self.validator = UserValidation()

    def test_required_fields(self):
        bundle = Bundle(data={})

        errors = self.validator.is_valid(bundle)

        self.assertIn("email", errors)

    def test_invalid_emails(self):
        for email in ['nobody.com', 'nobody@', 'nobody@nobody', 'nobody@.com', '']:
            bundle = Bundle(data={ 'email': email })
        
            errors = self.validator.is_valid(bundle)

            self.assertIn("email", errors)

    def test_valid_emails(self):
        for email in ['nobody@nobody.com', 'nobody.nobody@somewhere.com', 'no_body@no-body.re']:
            bundle = Bundle(data={ 'email': email })
        
            errors = self.validator.is_valid(bundle)

            self.assertNotIn("email", errors)

class TestAPIUser(TransactionTestCase):
    fixtures = ['init_panda.json']

    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True

        self.user = utils.get_panda_user() 
        self.panda_user_group = Group.objects.get(name='panda_user')
        
        self.auth_headers = utils.get_auth_headers()

        self.client = Client()

    def test_get(self):
        response = self.client.get('/api/1.0/user/%i/' % self.user.id, **self.auth_headers) 

        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content)

        self.assertNotIn('username', body)
        self.assertNotIn('password', body)
        self.assertNotIn('is_superuser', body)
        self.assertNotIn('is_staff', body)

    def test_get_unauthorized(self):
        response = self.client.get('/api/1.0/user/%i/' % self.user.id) 

        self.assertEqual(response.status_code, 401)

    def test_list(self):
        response = self.client.get('/api/1.0/user/', data={ 'limit': 5 }, **self.auth_headers)

        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content)

        self.assertEqual(len(body['objects']), 2)
        self.assertEqual(body['meta']['total_count'], 2)
        self.assertEqual(body['meta']['limit'], 5)
        self.assertEqual(body['meta']['offset'], 0)
        self.assertEqual(body['meta']['next'], None)
        self.assertEqual(body['meta']['previous'], None)

    def test_create_as_admin(self):
        new_user = {
            'email': 'tester@tester.com',
            'password': 'test',
            'first_name': 'Testy',
            'last_name': 'McTester'
        }

        response = self.client.post('/api/1.0/user/', content_type='application/json', data=json.dumps(new_user), **utils.get_auth_headers('panda@pandaproject.net'))

        self.assertEqual(response.status_code, 201)
        
        body = json.loads(response.content)

        self.assertEqual(body['email'], 'tester@tester.com')
        self.assertEqual(body['first_name'], 'Testy')
        self.assertEqual(body['last_name'], 'McTester')
        
        new_user = User.objects.get(username='tester@tester.com')

        self.assertEqual(new_user.username, 'tester@tester.com')
        self.assertEqual(new_user.email, 'tester@tester.com')
        self.assertEqual(new_user.first_name, 'Testy')
        self.assertEqual(new_user.last_name, 'McTester')
        self.assertEqual(new_user.password[:5], 'sha1$')
        self.assertNotEqual(new_user.api_key, None)

        self.assertEqual(list(new_user.groups.all()), [self.panda_user_group])

    def test_create_as_user(self):
        new_user = {
            'email': 'tester@tester.com',
            'password': 'test',
            'first_name': 'Testy',
            'last_name': 'McTester'
        }

        response = self.client.post('/api/1.0/user/', content_type='application/json', data=json.dumps(new_user), **self.auth_headers)

        self.assertEqual(response.status_code, 401)

