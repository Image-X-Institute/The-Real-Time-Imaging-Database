import unittest
import unittest.mock as mock
from application import app


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_root_endpoint(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 302)  # Redirect status code

    def test_get_catalog_of_trials(self):
        response = self.app.get('/trials')
        self.assertEqual(response.status_code, 200)

    def test_get_catalog_of_sites(self):
        response = self.app.get('/sites')
        self.assertEqual(response.status_code, 200)

    # def test_add_patient(self):
    #     data = {
    #     }
    #     response = self.app.post('/add-patient', json=data)
    #     self.assertEqual(response.status_code, 201)

    # def test_add_fraction(self):
    #     data = {

    #     }
    #     response = self.app.post('/add-fraction', json=data)
    #     self.assertEqual(response.status_code, 201)

    def test_render_api_docs(self):
        response = self.app.get('/apidoc')
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
