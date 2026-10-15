#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chinese wording catalog loader.

Every customer-facing sentence the report generators emit lives in
``assets/locale_zh.json`` rather than inline in the code. Two reasons:

  * the source files stay single-language, which is a publishing requirement on
    the skill hub and makes the calculation code readable to any reviewer;
  * wording can be corrected, shortened or translated without touching a single
    line of arithmetic.

Two accessors, mirroring the two shapes a message takes::

    _L("an.001")                      # plain string, returned as-is
    _F("an.t001", a1=x, a2=y)         # template, rendered with str.format

A missing key raises ``KeyError`` deliberately. Falling back to the key or to an
empty string would ship a report with a blank sentence, which is far harder to
notice than a crash during generation.
"""
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PATH = os.path.join(_ROOT, "assets", "locale_zh.json")

if not os.path.exists(_PATH):
    raise ImportError("locale catalog not found: %s" % _PATH)

with open(_PATH, encoding="utf-8") as _fh:
    _DATA = json.load(_fh)

_PLAIN = _DATA["plain"]
_TEMPLATE = _DATA["template"]


def _L(key):
    """Return the plain Chinese string registered under *key*."""
    return _PLAIN[key]


def _F(key, **values):
    """Return the Chinese template registered under *key*, filled in."""
    return _TEMPLATE[key].format(**values)
