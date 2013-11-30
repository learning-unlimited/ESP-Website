from django.db import models
from django.test import TestCase

from esp.cache import registry
from esp.cache.argcache import cache_function
from esp.cache.key_set import wildcard

# hack the cache loader so we can define more caches
registry._caches_locked = False

# some test functions and models

counter = [0]
@cache_function
def get_calls(x):
    counter[0] += 1
    return counter[0]

class HashTag(models.Model):
    label = models.CharField(max_length=40, unique=True)

    def __unicode__(self):
        return self.label

class Article(models.Model):
    headline = models.CharField(max_length=200)
    content = models.TextField()
    reporter = models.ForeignKey('Reporter', related_name='articles')
    hashtags = models.ManyToManyField('HashTag', related_name='articles')

    @cache_function
    def num_comments(self):
        return self.comments.count()
    num_comments.depend_on_row(lambda: Comment, lambda comment: {'self': comment.article})

    def __unicode__(self):
        return self.headline

class Comment(models.Model):
    article = models.ForeignKey('Article', related_name='comments')

class Reporter(models.Model):
    first_name = models.CharField(max_length=70)
    last_name = models.CharField(max_length=70)

    @cache_function
    def full_name(self):
        return self.first_name + ' ' + self.last_name
    full_name.depend_on_row(lambda: Reporter, lambda reporter: {'self': reporter})

    @cache_function
    def top_article(self):
        articles = self.articles.all()
        if articles:
            return max(articles, key=Article.num_comments)
        else:
            return None
    top_article.depend_on_row(Article, lambda article: {'self': article.reporter})
    top_article.depend_on_cache(Article.num_comments, lambda self=wildcard: {'self': self.reporter})

    @cache_function
    def articles_with_hashtag(self, hashtag):
        return list(self.articles.filter(hashtags__label=hashtag).values_list('headline', flat=True))
    articles_with_hashtag.depend_on_model(HashTag)
    articles_with_hashtag.depend_on_row(Article, lambda article: {'self': article.reporter})
    articles_with_hashtag.depend_on_m2m(Article, 'hashtags', lambda article, hashtag: {'self': article.reporter, 'hashtag': hashtag.label})

    def __unicode__(self):
        return self.full_name()

# unhack the cache loader
registry._finalize_caches()
registry._lock_caches()


class CacheTests(TestCase):
    def setUp(self):
        reporter1 = Reporter.objects.create(pk=1, first_name='John', last_name='Doe')
        reporter2 = Reporter.objects.create(pk=2, first_name='Jane', last_name='Roe')
        article1 = Article.objects.create(pk=1, headline='Breaking News', content='Lorem ipsum dolor sit amet', reporter=reporter1)
        article2 = Article.objects.create(pk=2, headline='Article II', content='The executive Power shall be vested in a President', reporter=reporter1)
        comment1 = Comment.objects.create(pk=1, article=article1)
        comment2 = Comment.objects.create(pk=2, article=article1)
        hashtag1 = HashTag.objects.create(pk=1, label='#hashtag')
        hashtag2 = HashTag.objects.create(pk=2, label='#news')
        article1.hashtags.add(hashtag2)
        article2.hashtags.add(hashtag1)

    def test_cached(self):
        self.assertEqual(get_calls(1), 1)
        self.assertEqual(get_calls(()), 2)
        self.assertEqual(get_calls('a'), 3)
        self.assertEqual(get_calls(None), 4)
        self.assertEqual(get_calls(False), 5)
        self.assertEqual(get_calls(frozenset([2.0, 3.0])), 6)
        self.assertEqual(get_calls(frozenset([2.0, 3.0])), 6)
        self.assertEqual(get_calls(None), 4)
        self.assertEqual(get_calls(False), 5)
        self.assertEqual(get_calls(1), 1)
        self.assertEqual(get_calls(()), 2)
        self.assertEqual(get_calls('a'), 3)
        self.assertEqual(get_calls('b'), 7)

        reporter = Reporter.objects.get(pk=1)
        name1 = reporter.full_name()
        name2 = reporter.full_name()
        self.assertEqual(name1, name2)

        article = Article.objects.get(pk=1)
        cnt1 = article.num_comments()
        with self.assertNumQueries(0):
            cnt2 = article.num_comments()
        self.assertEqual(cnt1, cnt2)

        article_ = Article.objects.get(pk=1)
        with self.assertNumQueries(0):
            cnt3 = article_.num_comments()
        self.assertEqual(cnt1, cnt3)

        top_article = reporter.top_article()
        self.assertEqual(top_article, max(reporter.articles.all(), key=Article.num_comments))
        with self.assertNumQueries(0):
            top_article_again = reporter.top_article()
        self.assertEqual(top_article, top_article_again)

        with_hashtag = reporter.articles_with_hashtag('#hashtag')
        with self.assertNumQueries(0):
            with_hashtag_again = reporter.articles_with_hashtag('#hashtag')
        self.assertEqual(with_hashtag, with_hashtag_again)

    def test_cache_none(self):
        reporter = Reporter.objects.get(pk=2)
        top_article = reporter.top_article()
        self.assertIsNone(top_article)
        with self.assertNumQueries(0):
            top_article_again = reporter.top_article()
        self.assertIsNone(top_article_again)

    def test_kwargs(self):
        reporter = Reporter.objects.get(pk=1)
        with_hashtag1 = reporter.articles_with_hashtag('#hashtag')
        with self.assertNumQueries(0):
            with_hashtag1_again = reporter.articles_with_hashtag(hashtag='#hashtag')
        self.assertEqual(with_hashtag1, with_hashtag1_again)

        with_hashtag2 = reporter.articles_with_hashtag(hashtag='#news')
        with self.assertNumQueries(0):
            args = ['#news']
            kwargs = {'hashtag': '#news'}
            with_hashtag2_args = reporter.articles_with_hashtag(*args)
            with_hashtag2_kwargs = reporter.articles_with_hashtag(**kwargs)
        self.assertEqual(with_hashtag2, with_hashtag2_args)
        self.assertEqual(with_hashtag2, with_hashtag2_kwargs)

    def test_depend_on_row(self):
        article = Article.objects.get(pk=1)
        cnt1 = article.num_comments()
        article.comments.create(pk=3)
        with self.assertNumQueries(1):
            cnt2 = article.num_comments()
        self.assertEqual(cnt2, cnt1 + 1)

        article2 = Article.objects.get(pk=2)
        article2.comments.create(pk=4)
        with self.assertNumQueries(0):
            cnt3 = article.num_comments()
        self.assertEqual(cnt3, cnt2)

    def test_depend_on_cache(self):
        reporter = Reporter.objects.get(pk=1)
        top_article = reporter.top_article()
        next_article = reporter.articles.exclude(pk=top_article.pk)[0]

        d = top_article.num_comments() - next_article.num_comments()
        for i in range(4, 5 + d):
            next_article.comments.create(pk=i)

        with self.assertNumQueries(0):
            top_article_comments = top_article.num_comments()
        with self.assertNumQueries(1):
            next_article_comments = next_article.num_comments()
        self.assertEqual(next_article_comments, top_article_comments + 1)

        with self.assertNumQueries(1):
            new_top_article = reporter.top_article()
        self.assertEqual(next_article, new_top_article)

    def test_depend_on_m2m(self):
        reporter = Reporter.objects.get(pk=1)
        article1 = Article.objects.get(pk=1)
        article2 = Article.objects.get(pk=2)
        hashtag1 = HashTag.objects.get(pk=1)
        hashtag2 = HashTag.objects.get(pk=2)

        with_hashtag1 = reporter.articles_with_hashtag(hashtag1.label)
        article1.hashtags.add(hashtag1)
        with self.assertNumQueries(1):
            with_hashtag1_new = reporter.articles_with_hashtag(hashtag1.label)
        self.assertEqual(set(with_hashtag1_new), set(with_hashtag1 + [article1.headline]))
        self.assertEqual(len(with_hashtag1_new), len(with_hashtag1) + 1)

        with_hashtag2 = reporter.articles_with_hashtag(hashtag2.label)
        hashtag2.articles.add(article2)
        with self.assertNumQueries(1):
            with_hashtag2_new = reporter.articles_with_hashtag(hashtag2.label)
        self.assertEqual(set(with_hashtag2_new), set(with_hashtag2 + [article2.headline]))
        self.assertEqual(len(with_hashtag2_new), len(with_hashtag2) + 1)

        with self.assertNumQueries(0):
            with_hashtag1_again = reporter.articles_with_hashtag(hashtag1.label)
        self.assertEqual(with_hashtag1_again, with_hashtag1_new)

    def test_depend_on_model(self):
        reporter = Reporter.objects.get(pk=1)
        hashtag1 = HashTag.objects.get(pk=1)
        with_hashtag1 = reporter.articles_with_hashtag(hashtag1.label)
        old_label = hashtag1.label

        hashtag1.label = '#updated'
        hashtag1.save()
        with self.assertNumQueries(1):
            with_hashtag1_old = reporter.articles_with_hashtag(old_label)
        self.assertEqual(with_hashtag1_old, [])
        with self.assertNumQueries(1):
            with_hashtag1_new = reporter.articles_with_hashtag(hashtag1.label)
        self.assertEqual(set(with_hashtag1_new), set(with_hashtag1))
        self.assertEqual(len(with_hashtag1_new), len(with_hashtag1))
