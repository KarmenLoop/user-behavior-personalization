# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Normalize authorized conversations into reviewable evidence, without a model.

Extraction is deliberately conservative and rule-based. It proposes what the
user explicitly said; observed writing style is not a desired response style.
Redaction covers recognizable patterns, not every kind of private information.
"""
import datetime as dt
import re

from host_support import content, identifier, need
from learning import digest, fingerprint, now_utc, timestamp

ROLES = {'user', 'assistant', 'system', 'tool'}
CONVERSATION_FIELDS = {'session_id', 'context', 'messages'}
MESSAGE_FIELDS = {'id', 'role', 'text', 'at'}

# A closed or unterminated PEM block is removed before excerpts are retained.
PEM = re.compile(r'-----BEGIN [A-Z0-9 ]*(?:PRIVATE KEY|CERTIFICATE)[A-Z0-9 ]*-----[\s\S]*?(?:-----END [A-Z0-9 ]+-----|\Z)')
TOKEN = re.compile(r'(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|(?:AKIA|ASIA)[A-Z0-9]{16}|eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})(?![A-Za-z0-9])')
ASSIGNMENT = re.compile(r'''(?ix)(\b(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|passwd|secret|token)\b|密码|密钥|令牌)\s*[:=：]\s*(?:"[^"\n]*"|'[^'\n]*'|[^\s,;，；。]+)''')
BEARER = re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/-]{8,}=*')
EMAIL = re.compile(r'(?<![\w.+-])[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+(?![\w-])')

TEMPORARY = re.compile(r'(?i)\b(?:today|tonight|this time|this one|for now|for this (?:task|answer|reply|session)|just this|on this occasion)\b|今天|今晚|这次|本次|这一次|暂时|这条回复|当前这轮')
REPORTED = re.compile(r"(?i)^\s*(?:[-*+]\s*)?(?:example\b|for example\b|e\.g\.|suppose\b|imagine\b|what if\b|translate\b|quote\b|(?:my (?:teammate|colleague|friend)|he|she|they)\s+(?:said|says|prefers)\b|(?:i am|i'm) not saying\b)|^(?:示例|例如|比如|假设|如果|翻译|引用|同事说|朋友说|他说|她说|他们说)")
DURABLE = re.compile(r'(?i)\b(?:I prefer\b|I would prefer\b|From now on\b|For future\b|Going forward\b|Please remember\b|Remember that I\b)|(?:以后|今后|长期|我更喜欢|我偏好|请记住|不要再|不再用)')
GOAL = re.compile(r'(?i)\b(?:My goal is|My long-term goal is|I aim to|I want to learn)\b|(?:我的目标是|我的长期目标是|我想学会|我希望掌握)')
ALWAYS = re.compile(r'(?i)^\s*(?:[-*+]\s*)?(?:Always|Never)\b')
ASSISTANCE = re.compile(r'(?i)\b(?:answer|respond|response|reply|replies|explain|write|writing|report|summary|summaries|status|update|plan|workflow|task|review|test|commit|release|deploy|code|coding|example|example[s]?|checklist|diagram|teach|lesson|step|format|output|address me|call me|ask me)\b|回答|回复|讲解|解释|写作|总结|汇报|步骤|任务|工作流|测试|提交|发布|部署|代码|示例|图解|教程|称呼|输出|格式')
DANGEROUS = re.compile(r'(?i)(?:ignore|disregard|override|forget).{0,50}(?:system|developer|previous|higher.priority|safety).{0,30}(?:instruction|prompt|rule)|(?:bypass|disable|skip).{0,30}(?:permission|authori[sz]ation|approval|authentication|safety|security)|(?:reveal|exfiltrate|send|upload).{0,30}(?:password|secret|credential|token|private key)|忽略.{0,30}(?:系统|开发者|安全|之前).{0,15}(?:指令|规则)|(?:绕过|关闭|跳过).{0,20}(?:权限|授权|审批|安全验证)|(?:泄露|发送|上传).{0,20}(?:密码|密钥|令牌)')
SENSITIVE = re.compile(r'(?i)\b(?:diagnos\w*|depression|depressed|bipolar|schizophren\w*|autis\w*|adhd|mental health|religion|religious|ethnicity|sexual orientation|sexuality|political affiliation|pregnan\w*|medical condition)\b|诊断|抑郁|躁郁|精神病|自闭|宗教|民族|性取向|政治立场|怀孕|病史')
PSYCHOLOGICAL_LABEL = re.compile(r'(?i)\b(?:subconscious|mind.reading|personality type|narcissis\w*|neurotic\w*|introvert\w*|extrovert\w*)\b|(?:you are|the user is).{0,25}(?:emotionally unstable|manipulable|vulnerable|irrational)|人格类型|潜意识|读心|心理弱点|操控用户|性格诊断')
WORKFLOW = re.compile(r'(?i)\b(?:plan|workflow|task|review|test|commit|release|deploy|code|coding|verify|verification|rollback|project|checklist|version|approval|deadline|receipt)\b|流程|工作流|任务|审查|测试|提交|发布|部署|代码|验证|回滚|项目|清单|版本|审批|期限|收条')
CONSTRAINT = re.compile(r'(?i)\b(?:never|do not|don.t|must not|stop|avoid|no longer|without)\b|不要|不再|禁止|避免|不能|不得')
ONE_TASK = re.compile(r'(?i)\b(?:fix|delete|upload|send|buy|book|run)\s+(?:this|that|the)\s+(?:bug|file|message|command|ticket|build)\b|\bfix\s+bug\s*[#0-9]|(?:修复|删除|发送|上传|运行)(?:这个|这条|这份|那个)(?:错误|文件|消息|命令|问题)')


def redact(text):
    """Return sanitized text and whether any recognizable pattern was removed."""
    value = PEM.sub('[REDACTED_PEM]', text)
    value = TOKEN.sub('[REDACTED_CREDENTIAL]', value)
    value = ASSIGNMENT.sub('[REDACTED_CREDENTIAL]', value)
    value = BEARER.sub('[REDACTED_CREDENTIAL]', value)
    value = EMAIL.sub('[REDACTED_EMAIL]', value)
    return value, value != text


def safe_candidate_text(text):
    """A bounded lexical filter for model proposals, not a safety classifier.

    A true result still requires exact evidence, user review and host policy.
    Novel private data, diagnoses or obfuscated commands can evade word filters.
    """
    if not isinstance(text, str) or not 0 < len(text.strip()) <= 1000:
        return False
    _, redacted = redact(text)
    return not (redacted or '[REDACTED_' in text or DANGEROUS.search(text)
                or SENSITIVE.search(text) or PSYCHOLOGICAL_LABEL.search(text))


def _blank(match):
    return ''.join('\n' if char == '\n' else ' ' for char in match.group())


def extraction_mask(text):
    """Keep offsets stable while hiding code, blockquotes and quoted spans."""
    lines = text.splitlines(keepends=True)
    result = []
    fence = None
    for line in lines:
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = (token[0], len(token))
            elif token[0] == fence[0] and len(token) >= fence[1]:
                fence = None
            result.append(''.join('\n' if c == '\n' else ' ' for c in line))
        elif fence or re.match(r'^\s*>', line):
            result.append(''.join('\n' if c == '\n' else ' ' for c in line))
        else:
            result.append(line)
    masked = ''.join(result)
    for pattern in (r'`+[^`\n]*`+', r'"[^"\n]*"', r'“[^”\n]*”', r'「[^」\n]*」', r'『[^』\n]*』', r"(?<!\w)'[^'\n]+'(?!\w)", r'‘[^’\n]*’'):
        masked = re.sub(pattern, _blank, masked)
    # Incomplete quotes/code are still data, not durable user instructions.
    for pattern in (r'"[^\n]*$', r'“[^\n]*$', r'「[^\n]*$', r'『[^\n]*$', r'`[^\n]*$'):
        masked = re.sub(pattern, _blank, masked, flags=re.MULTILINE)
    return masked


def features(text):
    """Counts of plain authored surface, not quoted/code content or desires.

    Masked spans and redaction placeholders contribute nothing. Whitespace is
    normalized per nonblank line; word_count is a simple Unicode token count.
    """
    text = extraction_mask(text)
    text = re.sub(r'\[REDACTED_[A-Z_]+\]', ' ', text)
    lines = [re.sub(r'[^\S\n]+', ' ', line).strip() for line in text.splitlines()]
    text = '\n'.join(line for line in lines if line)
    cjk = bool(re.search(r'[\u3400-\u9fff]', text))
    latin = bool(re.search(r'[A-Za-z]', text))
    language = 'mixed' if cjk and latin else 'zh' if cjk else 'en' if latin else 'other'
    return {
        'chars': len(text),
        'word_count': len(re.findall(r'\b\w+\b', text)),
        'sentences': len([part for part in re.split(r'[.!?。！？\n]+', text) if part.strip()]),
        'bullet_lines': len(re.findall(r'^\s*(?:[-*+]\s+|\d+[.)、]\s*)\S', text, re.MULTILINE)),
        'question_marks': text.count('?') + text.count('？'),
        'language': language,
    }


def _proposals(excerpt, source_key, scope, truncated=False):
    mask = extraction_mask(excerpt)
    proposals, excluded = [], []
    # Split on unquoted sentence boundaries; keep quotes faithful to the excerpt.
    for match in re.finditer(r'[^\n]+?(?:[.!?](?=\s|$)|[。！？]|\n|$)', mask):
        visible = match.group()
        left = match.start() + len(visible) - len(visible.lstrip())
        right = match.end() - len(visible) + len(visible.rstrip())
        original = excerpt[left:right].strip()
        is_goal = bool(GOAL.search(visible))
        explicit = is_goal or bool(DURABLE.search(visible)) or bool(ALWAYS.search(visible) and ASSISTANCE.search(visible))
        if not explicit:
            continue
        reason = None
        if truncated and match.end() == len(excerpt) and not re.search(r'[.!?。！？]\s*$', original):
            reason = 'truncated_statement'
        elif TEMPORARY.search(visible):
            reason = 'temporary_request'
        elif REPORTED.search(visible) or visible.rstrip().endswith(('?', '？')):
            reason = 'quoted_example_or_question'
        elif ONE_TASK.search(visible):
            reason = 'single_task_command'
        elif '[REDACTED_' in original:
            reason = 'redacted_private_content'
        elif DANGEROUS.search(original):
            reason = 'instruction_override_or_credential_request'
        elif SENSITIVE.search(original) or PSYCHOLOGICAL_LABEL.search(original):
            reason = 'sensitive_attribute_or_diagnosis'
        if reason:
            excluded.append({'source_key': source_key, 'reason': reason})
            continue
        category = 'goal' if is_goal else 'constraint' if CONSTRAINT.search(visible) else 'workflow' if WORKFLOW.search(visible) else 'communication'
        identity = {'scope': scope, 'statement': original, 'source_keys': [source_key]}
        proposals.append({'id': 'proposal-' + fingerprint(identity)[:32], 'statement': original, 'scope': scope, 'category': category, 'source_keys': [source_key], 'evidence': [{'source_key': source_key, 'quote': original}], 'status': 'pending'})
    return proposals, excluded


def normalize_conversation(conversation, now=None):
    """Validate a batch and return sanitized user evidence plus pending proposals.

    Session and message identifiers are host attestations, not proof of identity
    or consent. Callers must enforce ownership, opt-in, source conflict checks,
    retention and forgetting. No model call, file access or background work runs.
    """
    need(isinstance(conversation, dict) and set(conversation) == CONVERSATION_FIELDS, 'INVALID_CONVERSATION', 'Supply exactly session_id, context and messages.')
    session = identifier(conversation['session_id'])
    context = content(conversation['context'], 'context', 200).casefold()
    need(context != '*', 'INVALID_CONTEXT', 'Conversation evidence needs a specific context.')
    raw_messages = conversation['messages']
    need(isinstance(raw_messages, list) and len(raw_messages) <= 100, 'INVALID_CONVERSATION', 'A batch may contain at most 100 messages.')
    now = now_utc() if now is None else now
    need(isinstance(now, dt.datetime) and now.tzinfo is not None and now.utcoffset() is not None, 'INVALID_TIMESTAMP', 'now must be a timezone-qualified datetime.')
    now = now.astimezone(dt.timezone.utc)
    session_key = 'session-' + digest(session)
    result = {'session_key': session_key, 'session_id': session, 'context': context, 'messages': [], 'proposals': [], 'transitions': [], 'excluded': [], 'counts': {'received_messages': len(raw_messages), 'user_messages': 0, 'ignored_messages': 0, 'proposals': 0, 'redacted_messages': 0, 'excluded_candidates': 0}}
    seen, previous_at = set(), None
    previous_user = None
    for ordinal, message in enumerate(raw_messages):
        need(isinstance(message, dict) and set(message) == MESSAGE_FIELDS, 'INVALID_MESSAGE', 'Supply exactly id, role, text and at for each message.')
        identifier(message['id'])
        need(message['id'] not in seen, 'DUPLICATE_MESSAGE', 'Message identifiers must be unique within a conversation batch.')
        seen.add(message['id'])
        need(isinstance(message['role'], str) and message['role'] in ROLES, 'INVALID_ROLE', 'Choose user, assistant, system or tool.')
        need(isinstance(message['text'], str) and len(message['text']) <= 4000, 'INVALID_MESSAGE', 'Message text must be a string of at most 4000 characters.')
        when = timestamp(message['at'])
        need(when <= now + dt.timedelta(minutes=5), 'FUTURE_MESSAGE', 'Message time is more than five minutes in the future.')
        need(previous_at is None or when >= previous_at, 'NONCHRONOLOGICAL_MESSAGES', 'Messages must be ordered by time, including ignored roles.')
        previous_at = when
        if message['role'] != 'user':
            result['counts']['ignored_messages'] += 1
            continue
        source_digest = digest(session + '\0' + message['id'])
        source_id = 'conversation:' + source_digest
        key = 'message-' + source_digest[:32]
        sanitized, changed = redact(message['text'])
        excerpt = sanitized[:600]
        record = {'key': key, 'source_id': source_id, 'source_hash': digest(source_id), 'content_hash': fingerprint(message), 'session_key': session_key, 'context': context, 'ordinal': ordinal, 'at': when.isoformat(), 'excerpt': excerpt, 'features': features(sanitized)}
        result['messages'].append(record)
        result['counts']['user_messages'] += 1
        result['counts']['redacted_messages'] += int(changed)
        proposed, excluded = _proposals(excerpt, key, context, len(sanitized) > 600)
        result['proposals'].extend(proposed)
        result['excluded'].extend(excluded)
        if previous_user and when - previous_user[1] <= dt.timedelta(hours=24):
            result['transitions'].append({'from_key': previous_user[0], 'to_key': key, 'session_key': session_key, 'context': context, 'at': when.isoformat()})
        previous_user = (key, when)
    result['counts']['proposals'] = len(result['proposals'])
    result['counts']['excluded_candidates'] = len(result['excluded'])
    return result
