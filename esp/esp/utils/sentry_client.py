"""Custom raven client that skips zlib/deflate compression.

Bugsink's ingest endpoint rejects raven's default zlib-wrapped
'Content-Encoding: deflate' payloads with a 400 ("invalid stored block
lengths") -- it appears to expect either raw deflate or (as verified) plain
uncompressed JSON. Sending uncompressed avoids the mismatch entirely.
"""
from __future__ import absolute_import

from raven.contrib.django import DjangoClient
from raven.utils import json


class UncompressedDjangoClient(DjangoClient):
    def get_content_encoding(self):
        return ''

    def encode(self, data):
        return json.dumps(data).encode('utf8')

    def decode(self, data):
        return json.loads(data.decode('utf8'))
