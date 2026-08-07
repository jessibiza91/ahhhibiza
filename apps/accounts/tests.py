import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.accounts.models import CustomUser, ProfileMedia
from apps.accounts.utils import safe_file_size


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
