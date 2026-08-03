from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import CustomUser, FavoriteAd, ProfileMedia, SiteConfiguration
from apps.ads.models import Ad, AdImage, ServiceTag
from apps.payments.models import Transaction


class PlatformFlowTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.professional = CustomUser.objects.create_user(
            username='professional_test',
            password='test-password',
            type=CustomUser.Types.PROFESSIONAL,
        )
        cls.professional.profile.zone = 'EIVISSA'
        cls.professional.profile.save(update_fields=['zone'])

        cls.other_professional = CustomUser.objects.create_user(
            username='other_professional',
            password='test-password',
            type=CustomUser.Types.PROFESSIONAL,
        )
        cls.other_professional.profile.zone = 'SANT_ANTONI'
        cls.other_professional.profile.save(update_fields=['zone'])

        cls.client_user = CustomUser.objects.create_user(
            username='client_test',
            password='test-password',
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
