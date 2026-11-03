# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Retrieve likely follow-up requests from original, inspectable conversation edges.

This is an independently implemented lexical case-retrieval method, not a language
model or a predictor of private thoughts. Scores rank historical examples; they
are not calibrated probabilities. The caller must enforce subject and pause rules.
"""
from collections import Counter
import datetime as dt
import math
import re
import unicodedata

from host_support import content, need
from learning import context_key, now_utc, timestamp

MAX_MESSAGES = 400
MAX_TRANSITIONS = 1000
WINDOW_DAYS = 90
HALF_LIFE_DAYS = 30
MAX_GAP_HOURS = 24
MIN_QUERY_SIMILARITY = 0.20
FOLLOWUP_SIMILARITY = 0.40
MIN_SESSIONS = 2
MIN_TOP_SHARE = 0.60
MIN_RELATIVE_MARGIN = 0.20
MAX_CANDIDATES = 3
MAX_EVIDENCE_EXAMPLES = 6

STOP_WORDS = frozenset(('a an and are as at be by can could for from i in is it me my of on '
                        'our please that the their them these they this to us was we were '
                        'will with would you your').split())
GENERIC_WORDS = frozenset(('please help review check explain make create write prepare look over now next step task request question run give include').split())
CJK_FUNCTIONS = frozenset('\u7684\u4e86\u662f\u8bf7\u6211\u4f60\u4ed6\u5979\u5b83\u4eec\u8fd9\u90a3\u4e00\u4e2a\u4e9b\u5e2e\u5728\u6709\u4e0e\u548c\u628a\u5c06\u518d\u5148\u540e\u5c31\u5e76\u4e3a\u7ed9\u8ba9\u4e5f\u90fd\u5bf9\u4f1a\u8981\u7b49\u53ca\u5730\u5f97\u5417\u5462\u554a\u4e48')
CJK_STOP = frozenset(('\u8bf7\u95ee', '\u5e2e\u6211', '\u4e00\u4e0b', '\u6211\u4eec', '\u53ef\u4ee5', '\u8fd9\u4e2a', '\u90a3\u4e2a', '\u7136\u540e'))
NEGATION = re.compile(r"\b(?:no|not|never|avoid|without|stop|don't|dont)\b|\u4e0d\u8981|\u7981\u6b62|\u4e0d\u8bb8|\u65e0\u9700|\u522b", re.I)
ACTION_BOUNDARIES = (
    re.compile(r'\b(?:delete|remove|erase|drop|wipe|destroy)\w*\b|\u5220\u9664|\u62b9\u9664|\u6e05\u7a7a|\u9500\u6bc1', re.I),
    re.compile(r'\b(?:publish|deploy|send|upload|transfer)\w*\b|\u53d1\u5e03|\u90e8\u7f72|\u53d1\u9001|\u4e0a\u4f20', re.I),
    re.compile(r'\b(?:pay|purchase|buy)\w*\b|\u4ed8\u6b3e|\u652f\u4ed8|\u8d2d\u4e70|\u4e0b\u5355', re.I),
)


def _intent_flags(text):
    # Conservative guard, not a semantic parser: sharing an object does not
    # make deleting, publishing, or buying it equivalent to inspecting it.
    return (bool(NEGATION.search(text)), *(bool(pattern.search(text)) for pattern in ACTION_BOUNDARIES))


def _stem(word):
    # Conservative surface morphology, not a semantic synonym table.
    if len(word) > 5 and word.endswith('ies'):
        return word[:-3] + 'y'
    if len(word) > 5 and word.endswith('ing'):
        stem = word[:-3]
        return stem[:-1] if len(stem) > 2 and stem[-1] == stem[-2] else stem
    if len(word) > 4 and word.endswith('ed'):
        stem = word[:-2]
        return stem[:-1] if len(stem) > 2 and stem[-1] == stem[-2] else stem
    if len(word) > 4 and word.endswith('s') and not word.endswith(('ss', 'us', 'is')):
        return word[:-1]
    return word


def _parts(text):
    normalized = unicodedata.normalize('NFKC', text).casefold()
    words = [_stem(w) for w in re.findall(r"[a-z0-9]+(?:['-][a-z0-9]+)*", normalized)
             if w not in STOP_WORDS]
    runs = re.findall(r'[\u3400-\u4dbf\u4e00-\u9fff]+', normalized)
    return words, runs


def tokens(text):
    """Independent word, morphology, subword and CJK channels; no synonym model."""
    words, runs = _parts(text)
    result = ['w:' + word for word in words]
    result.extend('p:' + left + ' ' + right for left, right in zip(words, words[1:]))
    for word in words:
        if word in GENERIC_WORDS or len(word) < 4:
            continue
        marked = '^' + word + '$'
        result.extend('g:' + marked[n:n + size] for size in (3, 4)
                      for n in range(len(marked) - size + 1))
    for run in runs:
        result.extend('u:' + char for char in run if char not in CJK_FUNCTIONS)
        result.extend('c:' + run[n:n + 2] for n in range(len(run) - 1)
                      if run[n:n + 2] not in CJK_STOP)
    return result


def _anchors(text):
    words, runs = _parts(text)
    english = {word for word in words if word not in GENERIC_WORDS and len(word) > 1}
    chinese = {char for run in runs for char in run if char not in CJK_FUNCTIONS}
    bigrams = {run[n:n + 2] for run in runs for n in range(len(run)-1)
               if run[n:n + 2] not in CJK_STOP}
    return english, chinese, bigrams


def _similarity(left, right, vector):
    if _text_key(left) == _text_key(right):
        return 1.0
    en_left, zh_left, bi_left = vector.anchors(left)
    en_right, zh_right, bi_right = vector.anchors(right)
    en_common, zh_common = en_left & en_right, zh_left & zh_right
    # Multiple content anchors are necessary: generic words or a lone shared
    # name cannot make otherwise unrelated requests look equivalent.
    if len(en_common) < 2 and not (len(zh_common) >= 3 and bi_left & bi_right):
        return 0.0
    left_size, right_size = len(en_left) + len(zh_left), len(en_right) + len(zh_right)
    coverage = (len(en_common) + len(zh_common)) / min(left_size, right_size)
    cosine = _cosine(vector(left), vector(right))
    # The symmetric anchor channel tolerates extra explanation around a shared
    # topic. It is a retrieval heuristic, not an assertion of semantic identity.
    return 0.5 * cosine + 0.5 * math.sqrt(coverage)


def _text_key(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def _vectors(texts):
    """Fit IDF on distinct texts so importing copies cannot flood document counts."""
    distinct = sorted(set(texts))
    counts = {text: Counter(tokens(text)) for text in distinct}
    frequencies = Counter(token for terms in counts.values() for token in terms)
    idf = {token: 1 + 0.25 * math.log((len(distinct) + 1) / (count + 1))
           for token, count in frequencies.items()}
    cached_vectors, cached_anchors = {}, {}

    def vector(text):
        if text in cached_vectors:
            return cached_vectors[text]
        # Unseen query terms remain in its norm; a single shared word must not
        # turn an otherwise unrelated query into an exact match.
        unknown_idf = 1 + 0.25 * math.log(len(distinct) + 1)
        channel = {'w': 1.0, 'p': 0.15, 'g': 0.15, 'u': 0.6, 'c': 0.8}
        weighted = {token: (1 + math.log(count)) * idf.get(token, unknown_idf)
                    * channel[token[0]] * (0.25 if token[2:] in GENERIC_WORDS else 1.0)
                    for token, count in Counter(tokens(text)).items()}
        length = math.sqrt(sum(value * value for value in weighted.values()))
        cached_vectors[text] = {token: value / length for token, value in weighted.items()} if length else {}
        return cached_vectors[text]

    def anchors(text):
        if text not in cached_anchors:
            cached_anchors[text] = _anchors(text)
        return cached_anchors[text]

    # Caches belong to this forecast call, not a process-global profile cache.
    vector.anchors = anchors
    return vector


def _cosine(left, right):
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(token, 0.0) for token, value in left.items())


def _valid_edges(messages, transitions, context, now):
    edges = []
    seen = set()
    for edge in transitions:
        left_key, right_key = edge.get('from_key'), edge.get('to_key')
        identity = (left_key, right_key)
        if identity in seen or left_key == right_key:
            continue
        seen.add(identity)
        left, right = messages.get(left_key), messages.get(right_key)
        if not left or not right:
            continue  # Never bridge across a deleted or absent message.
        session = edge.get('session_key')
        if not session or left.get('session_key') != session or right.get('session_key') != session:
            continue
        if any(context_key(item['context']) != context for item in (left, right, edge)):
            continue
        start, end, recorded = timestamp(left['at']), timestamp(right['at']), timestamp(edge['at'])
        if start > end or end - start > dt.timedelta(hours=MAX_GAP_HOURS) or recorded != end:
            continue
        if start > now or end > now or now - start > dt.timedelta(days=WINDOW_DAYS):
            continue
        previous, following = left.get('excerpt', ''), right.get('excerpt', '')
        if not previous.strip() or not following.strip():
            continue
        edges.append({'from_key': left_key, 'to_key': right_key, 'session_key': session,
                      'previous_request': previous, 'next_request': following,
                      'at': end.isoformat(), 'when': end})
    return sorted(edges, key=lambda e: (e['session_key'], e['at'], e['from_key'], e['to_key']))


def forecast(messages, transitions, context, request, now=None):
    """Return inspectable historical follow-ups or abstain; never create an edge.

    One best-matching original edge per session contributes, preventing a long
    or repeatedly imported session from gaining extra votes. Complete-link
    lexical clusters require every pair of follow-ups to be similar and retain
    negation differences. The representative is an actual historical request.
    """
    need(isinstance(messages, dict) and isinstance(transitions, list), 'INVALID_INPUT',
         'Forecasting requires stored message records and explicit transition records.')
    need(len(messages) <= MAX_MESSAGES and len(transitions) <= MAX_TRANSITIONS,
         'FORECAST_LIMIT', 'Reduce stored evidence before forecasting.')
    key = context_key(context)
    content(request, 'request', 2000)
    now = now or now_utc()
    need(now.tzinfo is not None, 'INVALID_TIMESTAMP', 'Use a timezone-qualified clock.')
    result = {'status': 'insufficient_evidence', 'method': 'case_based_request_retrieval',
              'context': key, 'score_kind': 'lexical_recency_support_not_probability',
              'data_only': True, 'candidates': [], 'reasons': [
                  'Only original same-session transitions in this exact context are considered.',
                  'Session identifiers and source ownership are host attestations.',
                  'Historical wording is private evidence, not an instruction or execution permission.',
                  'Lexical similarity cannot establish intent, semantic equivalence, or private thoughts.']}
    edges = _valid_edges(messages, transitions, key, now)
    result['available_transitions'] = len(edges)
    if not edges or not tokens(request):
        result['reasons'].append('No usable recent transitions match this context.')
        return result
    vector = _vectors([e['previous_request'] for e in edges] + [e['next_request'] for e in edges])
    selected = {}
    for edge in edges:
        if _intent_flags(request) != _intent_flags(edge['previous_request']):
            continue
        similarity = _similarity(request, edge['previous_request'], vector)
        if similarity < MIN_QUERY_SIMILARITY:
            continue
        decay = 0.5 ** ((now - edge['when']).total_seconds() / (HALF_LIFE_DAYS * 86400))
        candidate = {**edge, 'similarity': similarity, 'weight': similarity * decay}
        existing = selected.get(edge['session_key'])
        rank = lambda item: (item['weight'], item['similarity'], item['at'], item['from_key'], item['to_key'])
        if existing is None or rank(candidate) > rank(existing):
            selected[edge['session_key']] = candidate
    cases = sorted(selected.values(), key=lambda e: (-e['weight'], e['session_key'], e['from_key']))
    result['matched_sessions'] = len(cases)
    if len(cases) < MIN_SESSIONS:
        result['reasons'].append('At least two independent session labels need a similar preceding request.')
        return result

    def similar(left, right):
        if _intent_flags(left) != _intent_flags(right):
            return False
        return _similarity(left, right, vector) >= FOLLOWUP_SIMILARITY

    clusters = []
    for case in cases:
        # Complete-link avoids A~B~C chaining when A and C are unrelated.
        compatible = [cluster for cluster in clusters
                      if all(similar(case['next_request'], peer['next_request']) for peer in cluster)]
        if compatible:
            best = max(compatible, key=lambda cluster: sum(_similarity(case['next_request'], peer['next_request'], vector) for peer in cluster) / len(cluster))
            best.append(case)
        else:
            clusters.append([case])
    clusters.sort(key=lambda group: (-sum(e['weight'] for e in group),
                                    _text_key(group[0]['next_request']), group[0]['from_key']))
    total_weight = sum(e['weight'] for e in cases)
    ranked = []
    for cluster in clusters:
        # Weighted medoid: emit a real observed follow-up, never a fabricated summary.
        representative = max(cluster, key=lambda case: (
            sum(_similarity(case['next_request'], peer['next_request'], vector) * peer['weight'] for peer in cluster),
            case['weight'], case['at'], case['from_key']))
        raw_score = sum(e['weight'] for e in cluster)
        recent = any(now - e['when'] <= dt.timedelta(days=HALF_LIFE_DAYS) for e in cluster)
        ranked.append({'suggestion': representative['next_request'], 'score': round(raw_score, 6),
                       'supporting_sessions': len(cluster),
                       'support_share': round(raw_score / total_weight, 6),
                       'ready': len(cluster) >= MIN_SESSIONS and recent,
                       'evidence_count': len(cluster),
                       'evidence_truncated': len(cluster) > MAX_EVIDENCE_EXAMPLES,
                       'evidence': [{k: round(e[k], 6) if k == 'similarity' else e[k]
                                     for k in ('from_key', 'to_key', 'previous_request', 'next_request', 'similarity', 'at')}
                                    for e in sorted(cluster, key=lambda e: (-e['weight'], e['from_key']))[:MAX_EVIDENCE_EXAMPLES]]})
    result['candidates'] = ranked[:MAX_CANDIDATES]
    top = ranked[0]
    if not top['ready']:
        result['reasons'].append('The leading follow-up lacks two supporting sessions or support within 30 days.')
        return result
    competing_score = ranked[1]['score'] if len(ranked) > 1 else 0.0
    margin = (top['score'] - competing_score) / top['score'] if top['score'] else 0.0
    if top['support_share'] < MIN_TOP_SHARE or margin < MIN_RELATIVE_MARGIN:
        result['status'] = 'conflicted'
        result['reasons'].append('Different follow-ups have similar support; ask what would help rather than choosing one.')
    else:
        result['status'] = 'suggested'
        result['reasons'].append('The leading historical follow-up has repeated recent support. Offer it as an optional suggestion.')
    return result
