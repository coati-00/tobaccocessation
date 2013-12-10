from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory
from django.test.client import Client
from pagetree.models import Hierarchy, Section
from tobaccocessation.activity_treatment_choice.views import loadstate, \
    savestate
from tobaccocessation.main.models import UserProfile


class TestViews(TestCase):
    def setUp(self):
        self.c = Client()
        self.factory = RequestFactory()
        self.user = User.objects.create_user('test_student',
                                             'test@ccnmtl.com',
                                             'testpassword')
        self.user.save()

        self.hierarchy = Hierarchy(name="main", base_url="/")
        self.hierarchy.save()

        root = Section.add_root(label="Root", slug="",
                                hierarchy=self.hierarchy)

        root.append_child("Section 1", "section-1")
        root.append_child("Section 2", "section-2")

        self.section1 = Section.objects.get(slug="section-1")
        self.section2 = Section.objects.get(slug="section-2")

    def tearDown(self):
        self.user.delete()

    def test_index(self):
        # it should redirect us somewhere.
        response = self.c.get("/")
        self.assertEquals(response.status_code, 302)
        # for now, we don't care where. really, we
        # are just making sure it's not a 500 error
        # at this point

    def test_smoke(self):
        # run the smoketests. we don't care if they pass
        # or fail, we just want to make sure that the
        # smoketests themselves don't have an error
        response = self.c.get("/smoketest/")
        self.assertEquals(response.status_code, 200)

    def test_treatment_choice_load_state(self):
        request = self.factory.get('/activity/treatment/load/')
        request.user = self.user
        response = loadstate(request)
        self.assertEqual(response.status_code, 200)

    def test_treatment_choice_save_state(self):
        request = self.factory.post('/activity/treatment/save/',
                                    {'json': 'need json'})
        request.user = self.user
        response = savestate(request)
        self.assertEqual(response.status_code, 200)

    '''Test Views in Main'''
    def test_index2(self):
        self.c = Client()
        self.c.login(username='test_student', password='testpassword')
        self.response = self.c.get('/')
        self.assertEqual(self.response.status_code, 302)

#    def test_flash_creation(self):
#        self.flash_create = self.c.post(
        #self.flash_create = self.c.post('/', {
        #'file_url': 'medication name', 'image_url': Falsewidth'height})
    #     self.request =
    #     self.block_create = self.block.create(self.request)
    #     self.assertIsNotNone(self.block_create)

    def test_accessible(self):
        pass
        #'''Need better test...'''
        #self.user = User.objects.get(username='test_student')
        #self.accessible = accessible(self.section1, self.user)
        #self.assertIsNotNull(self.accessible)

    def test_is_accessible(self):
        pass

    def test_clear_state(self):
        pass

    def test_consent_no_profile(self):
        self.c = Client()
        self.c.login(username='test_student', password='testpassword')
        self.response = self.c.get('/', follow=True)
        self.assertEqual(self.response.status_code, 200)
        self.assertEquals(self.response.redirect_chain[0][1], 302)
        self.assertEquals(self.response.templates[0].name,
                          "main/create_profile.html")

    def test_consent_incomplete_profile(self):
        # User has a profile, but does not have "consent" or other
        # special fields filled out. Redirect to create profile
        UserProfile.objects.get_or_create(user=self.user)[0]

        self.c = Client()
        self.c.login(username='test_student', password='testpassword')
        self.response = self.c.get('/', follow=True)
        self.assertEqual(self.response.status_code, 200)
        self.assertEquals(self.response.templates[0].name,
                          "main/create_profile.html")
        self.assertEquals(self.response.redirect_chain[0][1], 302)

    def test_consent_complete_profile(self):
        # User has a complete profile
        profile = UserProfile.objects.get_or_create(user=self.user)[0]
        profile.gender = 'F'
        profile.is_faculty = 'ST'
        profile.specialty = 'S10'
        profile.year_of_graduation = 2014
        profile.consent = True
        profile.save()

        self.c = Client()
        self.c.login(username='test_student', password='testpassword')
        self.response = self.c.get('/', follow=True)
        self.assertEqual(self.response.status_code, 200)
        self.assertEquals(self.response.templates[0].name,
                          "main/index.html")
        self.assertEquals(len(self.response.redirect_chain), 0)
