from django.contrib.auth import get_user_model
from django.urls import reverse
from django_tenants.test.cases import TenantTestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import KnowledgeArticle, KnowledgeArticleRevision, KnowledgeCategory

User = get_user_model()


def response_results(payload):
    return payload.get('results', payload) if isinstance(payload, dict) else payload


class KnowledgeBaseAPITest(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.defaults['HTTP_HOST'] = self.domain.domain
        self.user = User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='testpass123',
        )
        self.staff = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='testpass123',
            is_staff=True,
        )
        self.category = KnowledgeCategory.objects.create(
            name='Risk guidance',
            slug='risk-guidance',
            module_key='risk',
            created_by=self.staff,
        )

    def test_users_can_list_published_tenant_and_global_articles_only(self):
        tenant_article = KnowledgeArticle.objects.create(
            title='Create a risk',
            slug='create-a-risk',
            summary='How to create a risk.',
            body='Open the risk register and record the risk details.',
            category=self.category,
            module_key='risk',
            status='published',
            content_scope='tenant',
            created_by=self.staff,
            updated_by=self.staff,
        )
        global_article = KnowledgeArticle.objects.create(
            title='Risk scoring basics',
            slug='risk-scoring-basics',
            summary='How impact and likelihood work.',
            body='Use the agreed impact and likelihood scale.',
            category=self.category,
            module_key='risk',
            status='published',
            content_scope='global',
            created_by=self.staff,
            updated_by=self.staff,
        )
        KnowledgeArticle.objects.create(
            title='Draft article',
            slug='draft-article',
            summary='Hidden draft.',
            body='Draft content.',
            category=self.category,
            module_key='risk',
            status='draft',
            created_by=self.staff,
            updated_by=self.staff,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('knowledge:knowledge-articles-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {article['title'] for article in response_results(response.data)}
        self.assertEqual(titles, {tenant_article.title, global_article.title})

    def test_non_staff_cannot_read_draft_article_detail(self):
        draft = KnowledgeArticle.objects.create(
            title='Draft article',
            slug='draft-article',
            summary='Hidden draft.',
            body='Draft content.',
            category=self.category,
            module_key='risk',
            status='draft',
            created_by=self.staff,
            updated_by=self.staff,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('knowledge:knowledge-articles-detail', kwargs={'slug': draft.slug}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_can_create_article_and_revision_is_recorded(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            reverse('knowledge:knowledge-articles-list'),
            {
                'title': 'Assess ISO controls',
                'slug': 'assess-iso-controls',
                'summary': 'How to complete an assessment.',
                'body': 'Review the control, answer applicability and upload evidence.',
                'category': self.category.id,
                'module_key': 'frameworks',
                'workflow_key': 'control-assessment',
                'tags': ['ISO 27001', 'evidence'],
                'status': 'published',
                'content_scope': 'tenant',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        article = KnowledgeArticle.objects.get(slug='assess-iso-controls')
        self.assertEqual(article.created_by, self.staff)
        self.assertEqual(article.updated_by, self.staff)
        self.assertIsNotNone(article.published_at)
        self.assertEqual(KnowledgeArticleRevision.objects.filter(article=article).count(), 1)

    def test_non_staff_cannot_create_article(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse('knowledge:knowledge-articles-list'),
            {
                'title': 'Unauthorised article',
                'slug': 'unauthorised-article',
                'body': 'No.',
                'status': 'published',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_contextual_guidance_filters_by_module_and_workflow(self):
        KnowledgeArticle.objects.create(
            title='Risk register overview',
            slug='risk-register-overview',
            summary='Risk module overview.',
            body='Use this page to maintain the risk register.',
            category=self.category,
            module_key='risk',
            workflow_key='',
            status='published',
            created_by=self.staff,
            updated_by=self.staff,
        )
        workflow_article = KnowledgeArticle.objects.create(
            title='Risk treatment workflow',
            slug='risk-treatment-workflow',
            summary='Risk treatment guidance.',
            body='Assign actions and review due dates.',
            category=self.category,
            module_key='risk',
            workflow_key='treatment',
            status='published',
            created_by=self.staff,
            updated_by=self.staff,
        )
        KnowledgeArticle.objects.create(
            title='Policy workflow',
            slug='policy-workflow',
            summary='Policy guidance.',
            body='Publish policies and track acknowledgements.',
            module_key='policies',
            status='published',
            created_by=self.staff,
            updated_by=self.staff,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse('knowledge:knowledge-articles-contextual'),
            {'module_key': 'risk', 'workflow_key': 'treatment'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {article['title'] for article in response.data['results']}
        self.assertEqual(titles, {'Risk register overview', workflow_article.title})

    def test_contextual_guidance_requires_module_key(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('knowledge:knowledge-articles-contextual'))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_can_view_revisions(self):
        article = KnowledgeArticle.objects.create(
            title='Vendor onboarding',
            slug='vendor-onboarding',
            summary='Vendor setup guidance.',
            body='Create the vendor and assign diligence tasks.',
            module_key='vendors',
            status='published',
            created_by=self.staff,
            updated_by=self.staff,
        )
        KnowledgeArticleRevision.objects.create(
            article=article,
            title=article.title,
            summary=article.summary,
            body=article.body,
            status=article.status,
            changed_by=self.staff,
        )

        self.client.force_authenticate(user=self.staff)
        response = self.client.get(reverse('knowledge:knowledge-articles-revisions', kwargs={'slug': article.slug}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
