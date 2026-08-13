import io
import tempfile
from datetime import date
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.accounts.models import CustomUser, FavoriteAd, ProfileMedia, SiteConfiguration
from apps.ads.forms import AdForm, ControlAdForm
from apps.ads.models import Ad, AdImage, PromotionProduct, ServiceTag
from apps.ads.services import charge_daily_tangas
from apps.payments.models import Transaction


class PlatformFlowTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.professional = CustomUser.objects.create_user(
            username='professional_test',
            password='test-password',
            email='professional@example.com',
            type=CustomUser.Types.PROFESSIONAL,
        )
        cls.professional.profile.zone = 'EIVISSA'
        cls.professional.profile.save(update_fields=['zone'])

        cls.other_professional = CustomUser.objects.create_user(
            username='other_professional',
            password='test-password',
            email='other_professional@example.com',
            type=CustomUser.Types.PROFESSIONAL,
        )
        cls.other_professional.profile.zone = 'SANT_ANTONI'
        cls.other_professional.profile.save(update_fields=['zone'])

        cls.client_user = CustomUser.objects.create_user(
            username='client_test',
            password='test-password',
            email='client@example.com',
            type=CustomUser.Types.CLIENT,
        )
        cls.superadmin = CustomUser.objects.create_superuser(
            username='superadmin_test',
            password='test-password',
            email='admin@example.com',
        )

        cls.massages = ServiceTag.objects.create(name='Masajes de prueba')
        cls.travel = ServiceTag.objects.create(name='Viajes de prueba')

        cls.featured_ad = Ad.objects.create(
            owner=cls.professional,
            title='Profesional relax',
            public_description='Masaje relajante en el centro.',
            hot_description='Contenido privado de prueba.',
        )
        cls.featured_ad.services.add(cls.massages)

        cls.other_ad = Ad.objects.create(
            owner=cls.other_professional,
            title='Acompanante viajera',
            public_description='Disponible para eventos.',
            hot_description='Otra zona privada.',
        )
        cls.other_ad.services.add(cls.travel)

    def test_home_renders_filter_controls(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Todas las categorias')
        self.assertContains(response, 'Toda Ibiza')
        self.assertQuerySetEqual(
            response.context['services'],
            [self.other_ad, self.featured_ad],
        )

    def test_home_filters_by_public_text(self):
        response = self.client.get(reverse('home'), {'q': 'relajante'})

        self.assertEqual(list(response.context['services']), [self.featured_ad])

    def test_home_combines_text_and_zone_filters(self):
        response = self.client.get(reverse('home'), {
            'q': 'relax',
            'zone': 'EIVISSA',
        })

        self.assertEqual(list(response.context['services']), [self.featured_ad])

    def test_home_ignores_invalid_filter_values(self):
        response = self.client.get(reverse('home'), {
            'service': self.massages.id,
            'zone': 'NOT_A_ZONE',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_zone'], '')
        self.assertQuerySetEqual(
            response.context['services'],
            [self.other_ad, self.featured_ad],
        )

    def test_hot_content_is_locked_for_visitors_and_open_for_clients(self):
        visitor_response = self.client.get(
            reverse('ad_detail', args=[self.featured_ad.id])
        )
        self.assertFalse(visitor_response.context['can_view_private'])

        self.client.force_login(self.client_user)
        client_response = self.client.get(
            reverse('ad_detail', args=[self.featured_ad.id])
        )
        self.assertTrue(client_response.context['can_view_private'])

    def test_client_can_toggle_favorite_only_by_post(self):
        self.client.force_login(self.client_user)
        url = reverse('toggle_favorite_ad', args=[self.featured_ad.id])

        self.assertEqual(self.client.get(url).status_code, 405)

        self.client.post(url)
        self.assertTrue(FavoriteAd.objects.filter(
            user=self.client_user,
            ad=self.featured_ad,
        ).exists())

        self.client.post(url)
        self.assertFalse(FavoriteAd.objects.filter(
            user=self.client_user,
            ad=self.featured_ad,
        ).exists())

    def test_only_professional_can_open_ad_creation(self):
        self.client.force_login(self.client_user)
        client_response = self.client.get(reverse('ad_create'))
        self.assertRedirects(
            client_response,
            reverse('user_dispatch'),
            fetch_redirect_response=False,
        )

        self.client.force_login(self.professional)
        self.assertEqual(self.client.get(reverse('ad_create')).status_code, 200)

    def test_professional_deletion_requires_post_and_uses_trash(self):
        self.client.force_login(self.professional)
        url = reverse('ad_delete', args=[self.featured_ad.id])

        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)

        self.featured_ad.refresh_from_db()
        self.assertIsNotNone(self.featured_ad.trashed_at)
        self.assertEqual(self.featured_ad.status, Ad.Status.CERRADO)

    def test_non_owner_cannot_edit_or_delete_another_ad(self):
        self.client.force_login(self.other_professional)

        edit_url = reverse('ad_edit', args=[self.featured_ad.id])
        self.assertEqual(self.client.get(edit_url).status_code, 403)

        delete_url = reverse('ad_delete', args=[self.featured_ad.id])
        self.assertEqual(self.client.post(delete_url).status_code, 403)

        self.featured_ad.refresh_from_db()
        self.assertIsNone(self.featured_ad.trashed_at)
        self.assertEqual(self.featured_ad.status, Ad.Status.ACTIVE)

    def test_superadmin_visual_control_is_staff_only(self):
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse('control_panel')).status_code, 302)

        self.client.force_login(self.superadmin)
        self.assertEqual(self.client.get(reverse('control_panel')).status_code, 200)

    def test_superadmin_restores_user_and_keeps_dependent_ads_closed(self):
        self.professional.send_to_trash(
            by_user=self.superadmin,
            note='Seleccion multiple desde panel',
        )
        self.featured_ad.send_to_trash(
            by_user=self.superadmin,
            note='Usuario enviado a papelera',
        )
        self.client.force_login(self.superadmin)

        response = self.client.post(
            reverse('control_trash'),
            {'restore_user': self.professional.id},
        )

        self.assertRedirects(response, reverse('control_trash'))
        self.professional.refresh_from_db()
        self.featured_ad.refresh_from_db()
        self.assertIsNone(self.professional.trashed_at)
        self.assertTrue(self.professional.is_active)
        self.assertIsNone(self.featured_ad.trashed_at)
        self.assertEqual(self.featured_ad.status, Ad.Status.CERRADO)

    def test_ad_cannot_be_restored_while_owner_is_in_trash(self):
        self.professional.send_to_trash(by_user=self.superadmin, note='Moderacion')
        self.featured_ad.send_to_trash(by_user=self.superadmin, note='Moderacion')
        self.client.force_login(self.superadmin)

        self.client.post(
            reverse('control_trash'),
            {'restore_ad': self.featured_ad.id},
        )

        self.featured_ad.refresh_from_db()
        self.assertIsNotNone(self.featured_ad.trashed_at)

    def test_superadmin_restores_selected_profile_media_and_ad_image(self):
        media = ProfileMedia.objects.create(
            profile=self.professional.profile,
            file='user_test/restored.jpg',
        )
        image = AdImage.objects.create(
            ad=self.featured_ad,
            image='ad_images/restored.jpg',
        )
        media.send_to_trash(by_user=self.superadmin, note='Revision')
        image.send_to_trash(by_user=self.superadmin, note='Revision')
        self.client.force_login(self.superadmin)

        self.client.post(reverse('control_trash'), {
            'action': 'restore_selected',
            'profile_media': [media.id],
            'ad_images': [image.id],
        })

        media.refresh_from_db()
        image.refresh_from_db()
        self.assertIsNone(media.trashed_at)
        self.assertIsNone(image.trashed_at)

    def test_trash_screen_exposes_restore_controls(self):
        self.featured_ad.send_to_trash(by_user=self.superadmin, note='Revision')
        self.client.force_login(self.superadmin)

        response = self.client.get(reverse('control_trash'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Restaurar seleccionados')
        self.assertContains(response, 'Restaurar todo')
        self.assertContains(response, 'Restaurar anuncio cerrado')

    def test_superadmin_can_restore_all_valid_dependencies(self):
        image = AdImage.objects.create(
            ad=self.featured_ad,
            image='ad_images/restore_all.jpg',
        )
        self.professional.send_to_trash(by_user=self.superadmin, note='Moderacion')
        self.featured_ad.send_to_trash(
            by_user=self.superadmin,
            note='Usuario enviado a papelera',
        )
        image.send_to_trash(by_user=self.superadmin, note='Moderacion')
        self.client.force_login(self.superadmin)

        self.client.post(reverse('control_trash'), {'action': 'restore_all'})

        self.professional.refresh_from_db()
        self.featured_ad.refresh_from_db()
        image.refresh_from_db()
        self.assertIsNone(self.professional.trashed_at)
        self.assertIsNone(self.featured_ad.trashed_at)
        self.assertIsNone(image.trashed_at)

    def test_superadmin_visual_routes_cover_operational_entities(self):
        self.client.force_login(self.superadmin)
        routes = [
            reverse('control_ads'),
            reverse('control_media'),
            reverse('control_transactions'),
            reverse('control_service_tags'),
            reverse('control_site_settings'),
            reverse('control_user_detail', args=[self.professional.id]),
            reverse('control_ad_detail', args=[self.featured_ad.id]),
        ]

        for route in routes:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 200)

    def test_operational_control_pages_do_not_link_to_django_admin(self):
        self.client.force_login(self.superadmin)
        routes = [
            reverse('control_professionals'),
            reverse('control_clients'),
            reverse('control_ads'),
            reverse('control_media'),
            reverse('control_transactions'),
            reverse('control_user_detail', args=[self.professional.id]),
            reverse('control_ad_detail', args=[self.featured_ad.id]),
        ]

        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertNotContains(response, '/admin/')

    def test_control_panel_uses_visual_ad_and_transaction_destinations(self):
        Transaction.objects.create(
            user=self.professional,
            amount=10,
            description='Recarga de prueba',
        )
        self.client.force_login(self.superadmin)

        response = self.client.get(reverse('control_panel'))

        self.assertContains(
            response,
            reverse('control_ad_detail', args=[self.featured_ad.id]),
        )
        self.assertContains(response, reverse('control_transactions'))
        self.assertNotContains(
            response,
            f'/admin/ads/ad/{self.featured_ad.id}/change/',
        )

    def test_superadmin_can_manage_services_without_django_admin(self):
        self.client.force_login(self.superadmin)
        response = self.client.post(reverse('control_service_tags'), {
            'action': 'save',
            'name': 'Servicio visual nuevo',
        })

        self.assertRedirects(response, reverse('control_service_tags'))
        self.assertTrue(ServiceTag.objects.filter(name='Servicio visual nuevo').exists())

    def test_superadmin_can_update_site_configuration_visually(self):
        self.client.force_login(self.superadmin)
        response = self.client.post(reverse('control_site_settings'), {
            'support_email': 'ayuda@example.com',
            'maintenance_mode': 'on',
        })

        self.assertRedirects(response, reverse('control_site_settings'))
        configuration = SiteConfiguration.objects.get()
        self.assertEqual(configuration.support_email, 'ayuda@example.com')
        self.assertTrue(configuration.maintenance_mode)

    def test_global_media_moderation_returns_to_visual_gallery(self):
        image = AdImage.objects.create(
            ad=self.featured_ad,
            image='ad_images/moderation.jpg',
        )
        self.client.force_login(self.superadmin)

        response = self.client.post(
            reverse('delete_ad_image', args=[image.id]),
            {'from_control': '1'},
        )

        self.assertRedirects(response, reverse('control_media'))
        image.refresh_from_db()
        self.assertIsNotNone(image.trashed_at)

    def test_client_operational_routes_are_visual_and_admin_free(self):
        self.client.force_login(self.client_user)
        routes = [
            reverse('client_dashboard'),
            reverse('profile_edit'),
            reverse('ad_detail', args=[self.featured_ad.id]),
        ]

        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, '/admin/')

    def test_professional_operational_routes_are_visual_and_admin_free(self):
        self.client.force_login(self.professional)
        routes = [
            reverse('professional_dashboard'),
            reverse('professional_wallet'),
            reverse('professional_favorite_clients'),
            reverse('profile_edit'),
            reverse('ad_create'),
            reverse('ad_edit', args=[self.featured_ad.id]),
            reverse('ad_detail', args=[self.featured_ad.id]),
        ]

        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, '/admin/')

    def test_client_and_professional_cannot_cross_management_roles(self):
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse('professional_wallet')).status_code, 302)
        self.assertEqual(self.client.get(reverse('ad_create')).status_code, 302)

        self.client.force_login(self.professional)
        self.assertEqual(self.client.get(reverse('client_dashboard')).status_code, 302)

    def test_favorite_next_url_cannot_redirect_outside_platform(self):
        self.client.force_login(self.client_user)
        response = self.client.post(
            reverse('toggle_favorite_ad', args=[self.featured_ad.id]),
            {'next': 'https://example.com/phishing'},
        )

        self.assertRedirects(
            response,
            reverse('ad_detail', args=[self.featured_ad.id]),
            fetch_redirect_response=False,
        )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='ahhh_ads_media_'))
class AdMediaUploadTestCase(TestCase):
    def setUp(self):
        self.professional = CustomUser.objects.create_user(
            username='uploader_prof',
            password='test-password',
            email='uploader_prof@example.com',
            type=CustomUser.Types.PROFESSIONAL,
        )
        self.client.force_login(self.professional)

    def _png_bytes(self):
        buf = io.BytesIO()
        Image.new('RGB', (2, 2), color=(0, 0, 255)).save(buf, format='PNG')
        return buf.getvalue()

    def test_ad_create_rejects_non_image_uploads(self):
        fake = SimpleUploadedFile('malware.jpg', b'not-an-image', content_type='image/jpeg')
        response = self.client.post(reverse('ad_create'), {
            'title': 'Anuncio con archivo invalido',
            'public_description': 'Test',
            'status': 'ACTIVE',
            'public_media': [fake],
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Ad.objects.filter(title='Anuncio con archivo invalido').exists())

    def test_ad_create_accepts_valid_images(self):
        img = SimpleUploadedFile('foto.png', self._png_bytes(), content_type='image/png')
        response = self.client.post(reverse('ad_create'), {
            'title': 'Anuncio valido',
            'public_description': 'Test',
            'status': 'ACTIVE',
            'public_media': [img],
        })

        self.assertRedirects(
            response,
            reverse('professional_dashboard'),
            fetch_redirect_response=False,
        )
        ad = Ad.objects.get(title='Anuncio valido')
        self.assertEqual(ad.gallery.count(), 1)


class DailyTangasChargeTestCase(TestCase):
    """Consumo diario de Tangas segun el plan del anuncio."""

    @classmethod
    def setUpTestData(cls):
        cls.professional = CustomUser.objects.create_user(
            username='charger_pro',
            password='test-password',
            email='charger_pro@example.com',
            type=CustomUser.Types.PROFESSIONAL,
        )
        cls.trashed_professional = CustomUser.objects.create_user(
            username='charger_trashed',
            password='test-password',
            email='charger_trashed@example.com',
            type=CustomUser.Types.PROFESSIONAL,
        )
        cls.trashed_professional.trashed_at = timezone.now()
        cls.trashed_professional.save(update_fields=['trashed_at'])

        cls.superadmin = CustomUser.objects.create_superuser(
            username='charger_superadmin',
            password='test-password',
            email='charger_superadmin@example.com',
        )

        cls.basic = PromotionProduct.objects.get(name='Basico')
        cls.featured = PromotionProduct.objects.get(name='Destacado')

    def _ad(self, owner=None, plan=None, status=Ad.Status.ACTIVE):
        ad = Ad.objects.create(
            owner=owner or self.professional,
            title='Anuncio de consumo',
            promotion_product=plan,
            price_tangas=plan.price_tangas if plan else 0,
            status=status,
        )
        return ad

    def _form_data(self, product):
        return {
            'title': 'Anuncio de consumo',
            'public_description': 'Descripcion de prueba.',
            'hot_description': '',
            'services': [],
            'promotion_product': str(product.pk),
            'status': Ad.Status.ACTIVE,
        }

    def _set_balance(self, amount):
        self.professional.tangas_balance = Decimal(str(amount))
        self.professional.save(update_fields=['tangas_balance'])

    def test_charge_deducts_daily_cost(self):
        self._set_balance('25.00')
        ad = self._ad(plan=self.featured)

        result = charge_daily_tangas()

        self.professional.refresh_from_db()
        ad.refresh_from_db()
        self.assertEqual(result['charged'], 1)
        self.assertEqual(self.professional.tangas_balance, Decimal('15.00'))
        self.assertEqual(ad.last_tangas_charged_at, timezone.localdate())
        self.assertEqual(ad.promotion_product, self.featured)

    def test_charge_is_idempotent_same_day(self):
        self._set_balance('25.00')
        self._ad(plan=self.featured)

        charge_daily_tangas()
        self.professional.refresh_from_db()
        result = charge_daily_tangas()
        self.professional.refresh_from_db()

        self.assertEqual(result['charged'], 0)
        self.assertEqual(self.professional.tangas_balance, Decimal('15.00'))

    def test_insufficient_balance_downgrades_to_basic(self):
        self._set_balance('5.00')
        ad = self._ad(plan=self.featured)

        result = charge_daily_tangas()

        ad.refresh_from_db()
        self.professional.refresh_from_db()
        self.assertEqual(result['downgraded'], 1)
        self.assertEqual(ad.promotion_product, self.basic)
        self.assertEqual(ad.price_tangas, 0)
        self.assertEqual(ad.status, Ad.Status.ACTIVE)
        self.assertEqual(ad.last_tangas_charged_at, timezone.localdate())
        self.assertEqual(self.professional.tangas_balance, Decimal('5.00'))

    def test_dry_run_makes_no_changes(self):
        self._set_balance('25.00')
        ad = self._ad(plan=self.featured)

        result = charge_daily_tangas(dry_run=True)

        self.professional.refresh_from_db()
        ad.refresh_from_db()
        self.assertEqual(result['charged'], 1)
        self.assertEqual(self.professional.tangas_balance, Decimal('25.00'))
        self.assertIsNone(ad.last_tangas_charged_at)

    def test_skips_cerrado_trashed_and_free_plan_ads(self):
        self._set_balance('100.00')
        self._ad(plan=self.featured, status=Ad.Status.CERRADO)
        trashed = self._ad(plan=self.featured)
        trashed.send_to_trash()
        self._ad(plan=self.basic)

        result = charge_daily_tangas()

        self.assertEqual(result['charged'], 0)
        self.assertEqual(result['downgraded'], 0)

    def test_skips_owner_trashed_ad(self):
        ad = self._ad(owner=self.trashed_professional, plan=self.featured)

        result = charge_daily_tangas()

        ad.refresh_from_db()
        self.assertEqual(result['charged'], 0)
        self.assertIsNone(ad.last_tangas_charged_at)

    def test_form_rejects_paid_plan_without_balance(self):
        self._set_balance('5.00')

        form = AdForm(self._form_data(self.featured), owner=self.professional)

        self.assertFalse(form.is_valid())
        self.assertIn('promotion_product', form.errors)

    def test_form_charges_first_day_on_save(self):
        self._set_balance('25.00')

        form = AdForm(self._form_data(self.featured), owner=self.professional)
        self.assertTrue(form.is_valid(), form.errors)

        ad = form.save()

        self.professional.refresh_from_db()
        ad.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, Decimal('15.00'))
        self.assertEqual(ad.price_tangas, 10)
        self.assertEqual(ad.promotion_product, self.featured)
        self.assertEqual(ad.last_tangas_charged_at, timezone.localdate())

    def test_form_does_not_charge_when_plan_unchanged(self):
        self._set_balance('25.00')
        ad = self._ad(plan=self.featured)

        form = AdForm(self._form_data(self.featured), instance=ad, owner=self.professional)
        self.assertTrue(form.is_valid(), form.errors)

        form.save()

        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, Decimal('25.00'))

    def test_form_switch_to_basic_does_not_charge(self):
        self._set_balance('25.00')
        ad = self._ad(plan=self.featured)

        form = AdForm(self._form_data(self.basic), instance=ad, owner=self.professional)
        self.assertTrue(form.is_valid(), form.errors)

        form.save()

        ad.refresh_from_db()
        self.professional.refresh_from_db()
        self.assertEqual(ad.promotion_product, self.basic)
        self.assertEqual(ad.price_tangas, 0)
        self.assertEqual(self.professional.tangas_balance, Decimal('25.00'))

    def test_command_charges_and_reports(self):
        self._set_balance('25.00')
        self._ad(plan=self.featured)

        out = io.StringIO()
        call_command('consume_plan_tangas', stdout=out)

        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, Decimal('15.00'))
        self.assertIn('Total: 1 cobrado(s), 0 degradado(s)', out.getvalue())

    def test_command_dry_run_does_not_charge(self):
        self._set_balance('25.00')
        self._ad(plan=self.featured)

        out = io.StringIO()
        call_command('consume_plan_tangas', '--dry-run', stdout=out)

        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, Decimal('25.00'))
        self.assertIn('SIMULACION', out.getvalue())

    def test_command_rejects_invalid_date(self):
        with self.assertRaises(CommandError):
            call_command('consume_plan_tangas', '--date', '2026-13-99')

    def test_command_charge_for_specific_date(self):
        self._set_balance('25.00')
        ad = self._ad(plan=self.featured)
        ad.last_tangas_charged_at = date(2026, 1, 1)
        ad.save(update_fields=['last_tangas_charged_at'])

        call_command('consume_plan_tangas', '--date', '2026-01-02', stdout=io.StringIO())

        ad.refresh_from_db()
        self.professional.refresh_from_db()
        self.assertEqual(ad.last_tangas_charged_at, date(2026, 1, 2))
        self.assertEqual(self.professional.tangas_balance, Decimal('15.00'))

    def test_daily_charge_skips_exempt_ads(self):
        self._set_balance('5.00')
        ad = self._ad(plan=self.featured)
        ad.tangas_charge_exempt = True
        ad.tangas_exempt_reason = 'Cortesia de lanzamiento'
        ad.save()

        result = charge_daily_tangas()

        ad.refresh_from_db()
        self.professional.refresh_from_db()
        self.assertEqual(result['charged'], 0)
        self.assertEqual(result['downgraded'], 0)
        self.assertEqual(self.professional.tangas_balance, Decimal('5.00'))
        self.assertEqual(ad.promotion_product, self.featured)
        self.assertEqual(ad.status, Ad.Status.ACTIVE)
        self.assertIsNone(ad.last_tangas_charged_at)

    def test_form_exempt_ad_paid_plan_without_balance_is_valid_and_does_not_charge(self):
        self._set_balance('0.00')
        ad = self._ad(plan=self.basic)
        ad.tangas_charge_exempt = True
        ad.tangas_exempt_reason = 'Cortesia de lanzamiento'
        ad.save()

        form = AdForm(self._form_data(self.featured), instance=ad, owner=self.professional)
        self.assertTrue(form.is_valid(), form.errors)

        form.save()

        ad.refresh_from_db()
        self.professional.refresh_from_db()
        self.assertEqual(ad.promotion_product, self.featured)
        self.assertEqual(ad.price_tangas, 10)
        self.assertIsNone(ad.last_tangas_charged_at)
        self.assertEqual(self.professional.tangas_balance, Decimal('0.00'))

    def test_professional_form_hides_exemption_fields(self):
        form = AdForm(self._form_data(self.basic), owner=self.professional)

        self.assertNotIn('tangas_charge_exempt', form.fields)
        self.assertNotIn('tangas_exempt_reason', form.fields)

    def test_control_form_exposes_and_persists_exemption(self):
        ad = self._ad(plan=self.featured)
        form = ControlAdForm({
            'title': 'Anuncio de consumo',
            'public_description': 'Descripcion de prueba.',
            'hot_description': '',
            'services': [],
            'promotion_product': str(self.featured.pk),
            'price_tangas': '10',
            'status': Ad.Status.ACTIVE,
            'tangas_charge_exempt': 'on',
            'tangas_exempt_reason': 'Cortesia de Patricia',
        }, instance=ad)

        self.assertIn('tangas_charge_exempt', form.fields)
        self.assertIn('tangas_exempt_reason', form.fields)
        self.assertTrue(form.is_valid(), form.errors)

        form.save()

        ad.refresh_from_db()
        self.assertTrue(ad.tangas_charge_exempt)
        self.assertEqual(ad.tangas_exempt_reason, 'Cortesia de Patricia')

    def test_control_view_persists_exemption(self):
        ad = self._ad(plan=self.featured)
        self.client.force_login(self.superadmin)

        response = self.client.post(
            reverse('control_ad_detail', args=[ad.pk]),
            {
                'title': ad.title,
                'public_description': 'Descripcion de prueba.',
                'hot_description': '',
                'services': [],
                'promotion_product': str(self.featured.pk),
                'price_tangas': '10',
                'status': Ad.Status.ACTIVE,
                'tangas_charge_exempt': 'on',
                'tangas_exempt_reason': 'Motivo de prueba',
            },
        )

        self.assertEqual(response.status_code, 200)
        ad.refresh_from_db()
        self.assertTrue(ad.tangas_charge_exempt)
        self.assertEqual(ad.tangas_exempt_reason, 'Motivo de prueba')

    def test_professional_cannot_access_staff_control_views(self):
        self.client.force_login(self.professional)

        response = self.client.get(reverse('control_ads'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

        ad = self._ad(plan=self.featured)
        detail_response = self.client.get(reverse('control_ad_detail', args=[ad.pk]))
        self.assertEqual(detail_response.status_code, 302)
        self.assertIn('/admin/login/', detail_response.url)

