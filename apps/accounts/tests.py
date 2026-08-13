import io
import re
import tempfile

from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.accounts.media_validators import validate_uploaded_file
from apps.accounts.models import CustomUser, ProfileMedia
from apps.accounts.utils import safe_file_size


def _jpeg_bytes():
    buf = io.BytesIO()
    Image.new('RGB', (2, 2), color=(255, 0, 0)).save(buf, format='JPEG')
    return buf.getvalue()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='ahhh_test_media_'))
class SafeFileSizeTestCase(TestCase):
    def test_empty_field_returns_zero(self):
        self.assertEqual(safe_file_size(None), 0)

    def test_missing_file_returns_zero(self):
        user = CustomUser.objects.create_user(
            username='size_test',
            password='test-password',
        )
        media = ProfileMedia.objects.create(
            profile=user.profile,
            file='user_size_test/missing.jpg',
        )
        self.assertEqual(safe_file_size(media.file), 0)

    def test_real_file_returns_its_size(self):
        user = CustomUser.objects.create_user(
            username='size_real',
            password='test-password',
        )
        content = b'fake-image-bytes'
        upload = SimpleUploadedFile('foto.jpg', content)
        media = ProfileMedia.objects.create(profile=user.profile, file=upload)
        self.assertEqual(safe_file_size(media.file), len(content))

    def test_object_without_size_attribute_returns_zero(self):
        class NoSizeField:
            pass

        self.assertEqual(safe_file_size(NoSizeField()), 0)


class MediaValidatorTestCase(TestCase):
    def test_valid_image_is_accepted(self):
        f = SimpleUploadedFile('foto.jpg', _jpeg_bytes(), content_type='image/jpeg')
        self.assertEqual(validate_uploaded_file(f), 'image')

    def test_extension_mismatch_is_rejected(self):
        f = SimpleUploadedFile('foto.png', _jpeg_bytes(), content_type='image/jpeg')
        with self.assertRaises(ValidationError):
            validate_uploaded_file(f)

    def test_text_file_is_rejected(self):
        f = SimpleUploadedFile('fake.jpg', b'not-an-image', content_type='image/jpeg')
        with self.assertRaises(ValidationError):
            validate_uploaded_file(f)

    def test_spoofed_content_type_is_rejected(self):
        f = SimpleUploadedFile('foto.jpg', _jpeg_bytes(), content_type='text/html')
        with self.assertRaises(ValidationError):
            validate_uploaded_file(f)

    def test_valid_mp4_is_detected_as_video(self):
        header = b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom'
        f = SimpleUploadedFile('video.mp4', header + b'\x00' * 64, content_type='video/mp4')
        self.assertEqual(validate_uploaded_file(f), 'video')

    def test_valid_webm_is_detected_as_video(self):
        header = b'\x1a\x45\xdf\xa3' + b'\x00' * 32
        f = SimpleUploadedFile('clip.webm', header, content_type='video/webm')
        self.assertEqual(validate_uploaded_file(f), 'video')

    def test_video_extension_mismatch_is_rejected(self):
        header = b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom'
        f = SimpleUploadedFile('video.jpg', header + b'\x00' * 64, content_type='video/mp4')
        with self.assertRaises(ValidationError):
            validate_uploaded_file(f)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='ahhh_upload_media_'))
class ProfileUploadTestCase(TestCase):
    def setUp(self):
        self.professional = CustomUser.objects.create_user(
            username='uploader_pro',
            password='test-password',
            email='uploader_pro@example.com',
            type=CustomUser.Types.PROFESSIONAL,
        )
        self.client.force_login(self.professional)

    def test_profile_auto_upload_rejects_invalid_files(self):
        fake = SimpleUploadedFile('bad.mp4', b'not-a-video', content_type='video/mp4')
        response = self.client.post(reverse('profile_edit'), {
            'action': 'auto_upload_media',
            'media_files': [fake],
        })
        self.assertRedirects(response, reverse('profile_edit'))
        self.assertFalse(self.professional.profile.media.exists())

    def test_profile_auto_upload_accepts_valid_images(self):
        img = SimpleUploadedFile('foto.jpg', _jpeg_bytes(), content_type='image/jpeg')
        response = self.client.post(reverse('profile_edit'), {
            'action': 'auto_upload_media',
            'media_files': [img],
        })
        self.assertRedirects(response, reverse('profile_edit'))
        media = self.professional.profile.media.get()
        self.assertFalse(media.is_video)
        self.assertEqual(media.file.size, len(_jpeg_bytes()))

    def test_control_user_upload_rejects_invalid_files(self):
        superadmin = CustomUser.objects.create_superuser(
            username='boss',
            password='test-password',
            email='boss@example.com',
        )
        self.client.force_login(superadmin)
        fake = SimpleUploadedFile('bad.jpg', b'xxx', content_type='image/jpeg')
        response = self.client.post(
            reverse('control_user_detail', args=[self.professional.id]),
            {'action': 'upload_profile_media', 'media_files': [fake]},
        )
        self.assertRedirects(
            response,
            reverse('control_user_detail', args=[self.professional.id]),
        )
        self.assertFalse(self.professional.profile.media.exists())


@override_settings(AHHH_AUTH_RATE='5/h')
class RateLimitTestCase(TestCase):
    def tearDown(self):
        cache.clear()

    def test_login_is_blocked_after_five_attempts(self):
        url = reverse('login')
        for _ in range(5):
            response = self.client.post(url, {'username': 'x', 'password': 'wrong'})
            self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {'username': 'x', 'password': 'wrong'})
        self.assertEqual(response.status_code, 403)

    def test_registration_is_blocked_after_five_attempts(self):
        url = reverse('client_register')
        for _ in range(5):
            response = self.client.post(url, {})
            self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 403)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordResetTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='reset_user',
            password='old-password-123',
            email='reset_user@example.com',
            type=CustomUser.Types.CLIENT,
        )
        mail.outbox.clear()

    def _token_from_email(self):
        body = mail.outbox[0].body
        match = re.search(r'/reset/([^/]+)/([^/]+)/', body)
        self.assertIsNotNone(match, body)
        return match.group(1), match.group(2)

    def test_reset_page_renders(self):
        response = self.client.get(reverse('password_reset'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recuperar Contraseña')

    def test_reset_sends_email_with_link(self):
        response = self.client.post(reverse('password_reset'), {'email': self.user.email})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        uid, token = self._token_from_email()
        self.assertTrue(uid)
        self.assertTrue(token)

    def test_reset_unknown_email_does_not_reveal_existence(self):
        response = self.client.post(
            reverse('password_reset'),
            {'email': 'noexiste@example.com'},
        )
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_full_flow_changes_password(self):
        self.client.post(reverse('password_reset'), {'email': self.user.email})
        uid, token = self._token_from_email()
        url = reverse('password_reset_confirm', args=[uid, token])

        # Django valida el token y redirige a una URL sin el (set-password)
        # para no filtrarlo en el Referer.
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        form_url = response['Location']

        response = self.client.get(form_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(form_url, {
            'new_password1': 'nueva-pass-456',
            'new_password2': 'nueva-pass-456',
        })
        self.assertRedirects(response, reverse('password_reset_complete'))

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('nueva-pass-456'))
        self.assertFalse(self.user.check_password('old-password-123'))

    def test_confirm_rejects_invalid_token(self):
        response = self.client.get(reverse('password_reset_confirm', args=['invalid', 'invalid']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El enlace de recuperación es inválido')


@override_settings(AHHH_AUTH_RATE='5/h')
class PasswordResetRateLimitTestCase(TestCase):
    def tearDown(self):
        cache.clear()

    def test_password_reset_is_blocked_after_five_attempts(self):
        url = reverse('password_reset')
        for _ in range(5):
            response = self.client.post(url, {'email': 'x@example.com'})
            self.assertEqual(response.status_code, 302)
        response = self.client.post(url, {'email': 'x@example.com'})
        self.assertEqual(response.status_code, 403)


class PasswordChangeTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='change_user',
            password='old-pass-123',
            email='change_user@example.com',
            type=CustomUser.Types.CLIENT,
        )
        self.client.force_login(self.user)

    def test_change_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('password_change'))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('password_change')}",
        )

    def test_change_page_renders(self):
        response = self.client.get(reverse('password_change'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cambiar Contraseña')

    def test_change_with_wrong_current_password_is_invalid(self):
        response = self.client.post(reverse('password_change'), {
            'old_password': 'wrong-pass-999',
            'new_password1': 'nueva-pass-456',
            'new_password2': 'nueva-pass-456',
        })
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('old-pass-123'))

    def test_change_updates_password(self):
        response = self.client.post(reverse('password_change'), {
            'old_password': 'old-pass-123',
            'new_password1': 'nueva-pass-456',
            'new_password2': 'nueva-pass-456',
        })
        self.assertRedirects(response, reverse('password_change_done'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('nueva-pass-456'))
        self.assertFalse(self.user.check_password('old-pass-123'))

    def test_change_done_page_renders(self):
        response = self.client.get(reverse('password_change_done'))
        self.assertEqual(response.status_code, 200)


@override_settings(AHHH_AUTH_RATE='5/h')
class PasswordChangeRateLimitTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='change_ratelimited',
            password='old-pass-123',
            email='change_ratelimited@example.com',
            type=CustomUser.Types.CLIENT,
        )
        self.client.force_login(self.user)

    def tearDown(self):
        cache.clear()

    def test_password_change_is_blocked_after_five_attempts(self):
        url = reverse('password_change')
        data = {
            'old_password': 'wrong-pass-999',
            'new_password1': 'nueva-pass-456',
            'new_password2': 'nueva-pass-456',
        }
        for _ in range(5):
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, 200)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 403)


