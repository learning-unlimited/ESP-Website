from django.db import models
from django.test import TestCase

import unittest

from esp.cache import registry, queued
from esp.cache.function import cache_function
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
    num_comments.depend_on_row('cache.Comment', lambda comment: {'self': comment.article})

    @cache_function
    def num_comments_with_dummy(self, dummy):
        return self.comments.count()
    num_comments_with_dummy.depend_on_row('cache.Comment', lambda comment: {'self': comment.article})

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
    full_name.depend_on_row('cache.Reporter', lambda reporter: {'self': reporter})

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
    def articles_with_hashtag(self, hashtag='#hashtag'):
        return list(self.articles.filter(hashtags__label=hashtag).values_list('headline', flat=True))
    articles_with_hashtag.depend_on_model(HashTag)
    articles_with_hashtag.depend_on_row(Article, lambda article: {'self': article.reporter})
    articles_with_hashtag.depend_on_m2m(Article, 'hashtags', lambda article, hashtag: {'self': article.reporter, 'hashtag': hashtag.label})

    @cache_function
    def articles_with_headline(self, headline):
        return list(self.articles.filter(headline=headline).values_list('content', flat=True))
    articles_with_headline.depend_on_row(Article, lambda article: {'self': article.reporter, 'headline': article.headline})

    @cache_function
    def articles_with_headline_and_dummy(self, dummy, headline):
        return list(self.articles.filter(headline=headline).values_list('content', flat=True))
    articles_with_headline_and_dummy.depend_on_row(Article, lambda article: {'self': article.reporter, 'headline': article.headline})

    def __unicode__(self):
        return self.full_name()

# unhack the cache loader
registry._finalize_caches()
registry._lock_caches()


class CacheTests(TestCase):
    def setUp(self):
        # create initial objects
        reporter1 = Reporter.objects.create(pk=1, first_name='John', last_name='Doe')
        reporter2 = Reporter.objects.create(pk=2, first_name='Jane', last_name='Roe')
        reporter3 = Reporter.objects.create(pk=3, first_name='Jim', last_name='Poe')
        article1 = Article.objects.create(pk=1, headline='Breaking News', content='Lorem ipsum dolor sit amet', reporter=reporter1)
        article2 = Article.objects.create(pk=2, headline='Article II', content='The executive Power shall be vested in a President', reporter=reporter1)
        article3 = Article.objects.create(pk=3, headline='Article II', content='He shall hold his Office during the Term', reporter=reporter3)
        comment1 = Comment.objects.create(pk=1, article=article1)
        comment2 = Comment.objects.create(pk=2, article=article1)
        hashtag1 = HashTag.objects.create(pk=1, label='#hashtag')
        hashtag2 = HashTag.objects.create(pk=2, label='#news')
        article1.hashtags.add(hashtag2)
        article2.hashtags.add(hashtag1)

    def test_caches_loaded(self):
        """
        Rudimentary test that the loading mechanism works as expected.
        """
        # pending lookups should be empty once everything is loaded
        self.assertEqual(queued.pending_lookups, {})

        # we should test that signals are connected properly, but this
        # is hard to do directly. hope that if there is a problem with
        # that part, it ought to trip the other tests anyway.

    def test_cached(self):
        """
        Basic functionality: cached functions are called only on a
        cache miss, and retrieve the expected result on a cache hit.
        """
        # check that we make the expected number of function calls,
        # and get the expected results for arguments of various types
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

        # check that we get the same result from calling a cached method twice
        # (presumably from the cache the second time)
        reporter = Reporter.objects.get(pk=1)
        name1 = reporter.full_name()
        name2 = reporter.full_name()
        self.assertEqual(name1, name2)

        # use assertNumQueries to check that we aren't making DB queries
        # cache hits should not make queries
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
        """
        None values can be stored in the cache.
        """
        reporter = Reporter.objects.get(pk=2)
        top_article = reporter.top_article()
        self.assertIsNone(top_article)
        with self.assertNumQueries(0):
            top_article_again = reporter.top_article()
        self.assertIsNone(top_article_again)

    def test_kwargs(self):
        """
        Cached functions handle keyword arguments, *args, and **kwargs
        as expected.
        """
        reporter = Reporter.objects.get(pk=1)
        # with positional arg
        with_hashtag1 = reporter.articles_with_hashtag('#hashtag')
        with self.assertNumQueries(0):
            # with keyword arg
            with_hashtag1_again = reporter.articles_with_hashtag(hashtag='#hashtag')
        self.assertEqual(with_hashtag1, with_hashtag1_again)

        # with keyword arg
        with_hashtag2 = reporter.articles_with_hashtag(hashtag='#news')
        with self.assertNumQueries(0):
            # with *args and **kwargs
            args = ['#news']
            kwargs = {'hashtag': '#news'}
            with_hashtag2_args = reporter.articles_with_hashtag(*args)
            with_hashtag2_kwargs = reporter.articles_with_hashtag(**kwargs)
        self.assertEqual(with_hashtag2, with_hashtag2_args)
        self.assertEqual(with_hashtag2, with_hashtag2_kwargs)

    def test_optional_args(self):
        """
        Cached functions handle optional arguments as expected.
        """
        reporter = Reporter.objects.get(pk=1)
        # with positional arg
        with_hashtag1 = reporter.articles_with_hashtag('#hashtag')
        with self.assertNumQueries(0):
            # omitting optional arg (defaulting to '#hashtag')
            with_hashtag1_again = reporter.articles_with_hashtag()
        self.assertEqual(with_hashtag1, with_hashtag1_again)

    def test_depend_on_row(self):
        """
        depend_on_row triggers cache invalidation when models are updated.
        """
        # call the function, update the model, call the function again
        # should result in a cache miss
        article = Article.objects.get(pk=1)
        cnt1 = article.num_comments()
        article.comments.create(pk=3)
        with self.assertNumQueries(1):
            cnt2 = article.num_comments()
        self.assertEqual(cnt2, cnt1 + 1)

        # unrelated DB updates should not affect the cache
        article2 = Article.objects.get(pk=2)
        article2.comments.create(pk=4)
        with self.assertNumQueries(0):
            cnt3 = article.num_comments()
        self.assertEqual(cnt3, cnt2)

    @unittest.skip("Known issue, see Github #866")
    def test_depend_on_row_with_dummy(self):
        """
        depend_on_row still works correctly when there are other arguments to the function.
        """
        # call the function, update the model, call the function again
        # should result in a cache miss
        article = Article.objects.get(pk=1)
        cnt1 = article.num_comments()
        article.comments.create(pk=3)
        with self.assertNumQueries(1):
            cnt2 = article.num_comments_with_dummy(None)
        self.assertEqual(cnt2, cnt1 + 1)

        # unrelated DB updates should not affect the cache
        article2 = Article.objects.get(pk=2)
        article2.comments.create(pk=4)
        with self.assertNumQueries(0):
            cnt3 = article.num_comments_with_dummy(None)
        self.assertEqual(cnt3, cnt2)

    def test_depend_on_row_multiple_arguments(self):
        '''Tests that depend_on_row works properly with multiple arguments (in this case, where all are used).'''
        reporter1 = Reporter.objects.get(pk=1)
        reporter3 = Reporter.objects.get(pk=3)
        # The first time around, each one should hit the cache.
        with self.assertNumQueries(1):
            arts1a = reporter1.articles_with_headline('Breaking News')
        with self.assertNumQueries(1):
            arts2a = reporter1.articles_with_headline('Article II')
        with self.assertNumQueries(1):
            arts3a = reporter3.articles_with_headline('Article II')
        
        # There were no updates, so we shouldn't hit the cache.
        with self.assertNumQueries(0):
            arts1b = reporter1.articles_with_headline('Breaking News')
            self.assertEqual(arts1a,arts1b)
        with self.assertNumQueries(0):
            arts2b = reporter1.articles_with_headline('Article II')
            self.assertEqual(arts2a,arts2b)
        with self.assertNumQueries(0):
            arts3b = reporter3.articles_with_headline('Article II')
            self.assertEqual(arts3a,arts3b)

        article1 = Article.objects.get(pk=1)
        article1.content = 'The news is broken.'
        article1.save()

        # The first query should be affected by the update, but the latter two shouldn't.
        with self.assertNumQueries(1):
            arts1c = reporter1.articles_with_headline('Breaking News')
            self.assertNotEqual(arts1b,arts1c)
        with self.assertNumQueries(0):
            arts2c = reporter1.articles_with_headline('Article II')
            self.assertEqual(arts2b,arts2c)
        with self.assertNumQueries(0):
            arts3c = reporter3.articles_with_headline('Article II')
            self.assertEqual(arts3b,arts3c)

        article2 = Article.objects.get(pk=2)
        article2.content = 'The executive Power shall be vested in a Prime Minister'
        article2.save()

        # Now only the second should be affected.
        with self.assertNumQueries(0):
            arts1d = reporter1.articles_with_headline('Breaking News')
            self.assertEqual(arts1c,arts1d)
        with self.assertNumQueries(1):
            arts2d = reporter1.articles_with_headline('Article II')
            self.assertNotEqual(arts2c,arts2d)
        with self.assertNumQueries(0):
            arts3d = reporter3.articles_with_headline('Article II')
            self.assertEqual(arts3c,arts3d)

        article3 = Article.objects.get(pk=3)
        article3.content = 'He shall hold his Office forever'
        article3.save()

        # Now only the third should be affected.
        with self.assertNumQueries(0):
            arts1e = reporter1.articles_with_headline('Breaking News')
            self.assertEqual(arts1d,arts1e)
        with self.assertNumQueries(0):
            arts2e = reporter1.articles_with_headline('Article II')
            self.assertEqual(arts2d,arts2e)
        with self.assertNumQueries(1):
            arts3e = reporter3.articles_with_headline('Article II')
            self.assertNotEqual(arts3d,arts3e)

    @unittest.skip("Known issue, see Github #866")
    def test_depend_on_row_multiple_arguments_with_dummy(self):
        '''Tests for a bug when more than one but less than all of the arguments to the function are used in a depend_on_row.'''
        reporter1 = Reporter.objects.get(pk=1)
        reporter3 = Reporter.objects.get(pk=3)
        # The first time around, each one should hit the cache.
        with self.assertNumQueries(1):
            arts1a = reporter1.articles_with_headline_and_dummy(None, 'Breaking News')
        with self.assertNumQueries(1):
            arts2a = reporter1.articles_with_headline_and_dummy(None, 'Article II')
        with self.assertNumQueries(1):
            arts3a = reporter3.articles_with_headline_and_dummy(None, 'Article II')
        
        # There were no updates, so we shouldn't hit the cache.
        with self.assertNumQueries(0):
            arts1b = reporter1.articles_with_headline_and_dummy(None, 'Breaking News')
            self.assertEqual(arts1a,arts1b)
        with self.assertNumQueries(0):
            arts2b = reporter1.articles_with_headline_and_dummy(None, 'Article II')
            self.assertEqual(arts2a,arts2b)
        with self.assertNumQueries(0):
            arts3b = reporter3.articles_with_headline_and_dummy(None, 'Article II')
            self.assertEqual(arts3a,arts3b)

        article1 = Article.objects.get(pk=1)
        article1.content = 'The news is broken.'
        article1.save()

        # The first query should be affected by the update, but the latter two shouldn't.
        with self.assertNumQueries(1):
            arts1c = reporter1.articles_with_headline_and_dummy(None, 'Breaking News')
            self.assertNotEqual(arts1b,arts1c)
        with self.assertNumQueries(0):
            arts2c = reporter1.articles_with_headline_and_dummy(None, 'Article II')
            self.assertEqual(arts2b,arts2c)
        with self.assertNumQueries(0):
            arts3c = reporter3.articles_with_headline_and_dummy(None, 'Article II')
            self.assertEqual(arts3b,arts3c)

        article2 = Article.objects.get(pk=2)
        article2.content = 'The executive Power shall be vested in a Prime Minister'
        article2.save()

        # Now only the second should be affected.
        with self.assertNumQueries(0):
            arts1d = reporter1.articles_with_headline_and_dummy(None, 'Breaking News')
            self.assertEqual(arts1c,arts1d)
        with self.assertNumQueries(1):
            arts2d = reporter1.articles_with_headline_and_dummy(None, 'Article II')
            self.assertNotEqual(arts2c,arts2d)
        with self.assertNumQueries(0):
            arts3d = reporter3.articles_with_headline_and_dummy(None, 'Article II')
            self.assertEqual(arts3c,arts3d)

        article3 = Article.objects.get(pk=3)
        article3.content = 'He shall hold his Office forever'
        article3.save()

        # Now only the third should be affected.
        with self.assertNumQueries(0):
            arts1e = reporter1.articles_with_headline_and_dummy(None, 'Breaking News')
            self.assertEqual(arts1d,arts1e)
        with self.assertNumQueries(0):
            arts2e = reporter1.articles_with_headline_and_dummy(None, 'Article II')
            self.assertEqual(arts2d,arts2e)
        with self.assertNumQueries(1):
            arts3e = reporter3.articles_with_headline_and_dummy(None, 'Article II')
            self.assertNotEqual(arts3d,arts3e)

    def test_depend_on_cache(self):
        """
        depend_on_cache triggers cache invalidation when dependent caches
        are invalidated.
        """
        # Reporter.top_article depends on Article.num_comments
        # so invalidating num_comments should invalidate top_article too
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

        # top_article should be a cache miss here
        with self.assertNumQueries(1):
            new_top_article = reporter.top_article()
        self.assertEqual(next_article, new_top_article)

    def test_depend_on_m2m(self):
        """
        depend_on_m2m triggers cache invalidation when new many-to-many
        relations are updated.
        """
        reporter = Reporter.objects.get(pk=1)
        article1 = Article.objects.get(pk=1)
        article2 = Article.objects.get(pk=2)
        hashtag1 = HashTag.objects.get(pk=1)
        hashtag2 = HashTag.objects.get(pk=2)

        # adding a hashtag to an article should invalidate articles_with_hashtag
        with_hashtag1 = reporter.articles_with_hashtag(hashtag1.label)
        article1.hashtags.add(hashtag1)
        with self.assertNumQueries(1):
            with_hashtag1_new = reporter.articles_with_hashtag(hashtag1.label)
        self.assertEqual(set(with_hashtag1_new), set(with_hashtag1 + [article1.headline]))
        self.assertEqual(len(with_hashtag1_new), len(with_hashtag1) + 1)

        # ...and with the second hashtag
        with_hashtag2 = reporter.articles_with_hashtag(hashtag2.label)
        hashtag2.articles.add(article2)
        with self.assertNumQueries(1):
            with_hashtag2_new = reporter.articles_with_hashtag(hashtag2.label)
        self.assertEqual(set(with_hashtag2_new), set(with_hashtag2 + [article2.headline]))
        self.assertEqual(len(with_hashtag2_new), len(with_hashtag2) + 1)

        # but the second hashtag shouldn't affect the first one's cache
        with self.assertNumQueries(0):
            with_hashtag1_again = reporter.articles_with_hashtag(hashtag1.label)
        self.assertEqual(with_hashtag1_again, with_hashtag1_new)

        # removing a hashtag should also invalidate
        article2.hashtags.remove(hashtag2)
        with self.assertNumQueries(1):
            with_hashtag2_removed = reporter.articles_with_hashtag(hashtag2.label)
        self.assertEqual(set(with_hashtag2_removed), set(with_hashtag2))
        self.assertEqual(len(with_hashtag2_removed), len(with_hashtag2))

        with self.assertNumQueries(0):
            with_hashtag1_again = reporter.articles_with_hashtag(hashtag1.label)
        self.assertEqual(with_hashtag1_again, with_hashtag1_new)

        # as should clearing
        hashtag1.articles.clear()
        with self.assertNumQueries(1):
            with_hashtag1_removed = reporter.articles_with_hashtag(hashtag1.label)
        self.assertEqual(set(with_hashtag1_removed), set())

        with self.assertNumQueries(0):
            with_hashtag2_again = reporter.articles_with_hashtag(hashtag2.label)
        self.assertEqual(with_hashtag2_again, with_hashtag2_removed)

    def test_depend_on_model(self):
        """
        depend_on_model triggers cache invalidation when any instance
        of the model is updated.
        """
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
