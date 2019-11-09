# from loginout import loginout
import unittest

class TestLoginout(unittest.TestCase):

    def setUp(self):
        self.app = loginout.app.test_client()

    def test_redirect_before_login(self):
        response = self.app.get('/')
        assert response.status_code == 302
        assert 'login' == response.headers.get('Location')[-5:]
        response = self.app.get('/', follow_redirects=True)
        assert response.status_code == 200

    def test_login_logout(self):
        response = self.app.post('/login', data={'username':'sampleuser'})
        assert response.status_code == 302
        assert '/' == response.headers.get('Location')[-1:]
        response = self.app.get('/')
        assert response.status_code == 200
        response = self.app.get('/logout')
        assert response.status_code == 302
        assert 'login' == response.headers.get('Location')[-5:]
        response = self.app.get('/')
        assert response.status_code == 302
        assert 'login' == response.headers.get('Location')[-5:]

if __name__ == "__main__":
    unittest.main()