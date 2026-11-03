# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Discover recurring collaboration feedback from retained, authored excerpts.

This combines bounded request/correction grammar with response targets and
directional vocabulary. It is not unrestricted semantic or personality learning.
It only proposes a habit after independently labeled sessions agree.
Nothing here writes a profile or confirms a preference.
"""
import copy
import re

from conversations import extraction_mask, REPORTED, TEMPORARY, safe_candidate_text
from learning import DIMENSIONS, STATEMENTS, context_key, fingerprint, insights


def pattern(expression):
    return re.compile(expression, re.IGNORECASE)


# Each cue means a response-format request or correction, not an observation
# about how the user writes. Vocabulary is independent of held-out diagnostics.
CUES = {
    ('response_length', 'concise'): pattern(
        r'\b(?:too (?:long|verbose|wordy)|(?:make|keep) (?:it |this |the (?:answer|reply|response) )?(?:shorter|brief|concise)|'
        r'(?:be|answer|respond|write) (?:more )?(?:brief|concise)|(?:cut|skip|drop) (?:the )?(?:fluff|preamble)|'
        r'(?:less|fewer) (?:detail|details|words)|(?:shorten|trim) (?:the )?(?:answer|reply|response))\b|'
        r'太长|太啰嗦|太冗长|简短(?:一点|一些|些|点)|简洁(?:一点|一些|些|点)|精简(?:一下|一些|一点|些|点)|'
        r'少写(?:一点|点)|(?:别|不要)(?:再)?啰嗦|说重点'),
    ('response_length', 'detailed'): pattern(
        r'\b(?:too (?:brief|short|terse)|(?:more|add|include) (?:detail|details|explanation)|'
        r'explain (?:it |this )?(?:in detail|more thoroughly)|expand (?:the |your )?(?:answer|explanation))\b|'
        r'太简略|太简短|太笼统|详细(?:一点|一些|些|点)|展开(?:讲|说)|解释清楚|多(?:讲|说|写)(?:一些|一点|些)?(?:细节|解释)'),
    ('structure', 'conclusion_first'): pattern(
        r'\b(?:(?:start|lead|begin) with (?:the )?(?:answer|conclusion|result|bottom line)|'
        r'(?:answer|conclusion|result|bottom line) first|give me (?:the )?answer before)\b|'
        r'先(?:给|说|讲)(?:我)?(?:结论|答案|结果)|(?:结论|答案|结果)(?:放在|放)?前面|先说重点'),
    ('structure', 'steps'): pattern(
        r'\b(?:step by step|numbered steps|(?:use|show|give me|list) (?:the )?(?:steps|a step-by-step))\b|'
        r'分步骤|一步一步(?:地)?(?:说|讲|解释)|按步骤(?:讲|写|说明)|列出操作顺序'),
    ('structure', 'examples'): pattern(
        r'\b(?:(?:give|show) me (?:a |an |some )?(?:concrete |practical |actual )?examples?|'
        r'(?:use|include|add) (?:a |an |some )?(?:concrete |practical |actual )?examples?)\b|'
        r'举(?:一个|个|些)?(?:具体)?例子|给(?:我)?(?:一个|些)?(?:具体|实际)?(?:例子|示例)|用(?:具体|实际)?例子(?:说明|解释)'),
    ('structure', 'code_first'): pattern(
        r'\b(?:(?:show|give me|put) (?:the )?(?:code|patch|diff) first|'
        r'(?:code|patch|diff) before (?:the )?explanation|start with (?:the )?(?:code|patch|diff))\b|'
        r'先(?:给|看|展示|贴)(?:我)?(?:代码|补丁|改动)|(?:代码|补丁)(?:放在|放)?前面|先代码后解释'),
    ('structure', 'bullets'): pattern(
        r'\b(?:(?:use|prefer|give me|format (?:it |this )?as) (?:a )?(?:bullet points|bullets|bulleted list)|'
        r'(?:put|break) (?:it|this) (?:in|into) bullet points)\b|'
        r'用(?:项目符号|要点列表)|(?:分点|列点)(?:写|说|说明|回答)|列成要点'),
    ('teaching', 'worked_example'): pattern(
        r'\b(?:work through (?:an? )?example|show me (?:a )?worked example|walk me through (?:an? )?example)\b|'
        r'做(?:一个|个)完整例子|带我(?:走|做)一遍|先演示(?:一遍|一个例子)'),
    ('teaching', 'explain_back'): pattern(
        r'\b(?:(?:let me|ask me to) explain (?:it )?back|let me explain (?:it )?in my own words)\b|'
        r'让我用自己的话(?:解释|说)|让我复述'),
    ('teaching', 'practice'): pattern(
        r'\b(?:quiz me|give me (?:a |an |some )?(?:practice questions?|exercises?)|let me try (?:an? )?exercise)\b|'
        r'出(?:几道|一道|点)(?:练习|题)|让我做(?:几道|一道)?练习|让我先练习'),
    ('initiative', 'ask_first'): pattern(
        r'\b(?:ask (?:me )?(?:before|first)|check with me before)\b|先(?:问我|确认)|不要擅自(?:决定|改变方向)'),
    ('initiative', 'suggest_next'): pattern(
        r'\b(?:suggest (?:a |the )?next step|tell me what to do next|offer (?:a |the )?next step)\b|'
        r'建议下一步|告诉我下一步|给出下一步建议'),
    ('workflow_next_step', 'plan'): pattern(
        r'\b(?:plan first|show (?:me )?(?:the |a )?plan before (?:implementing|coding|editing))\b|'
        r'先(?:给|写|列)(?:我)?计划再(?:做|改|实现)|先计划后(?:实施|执行|实现)'),
    ('workflow_next_step', 'test'): pattern(
        r'\b(?:test before (?:the )?review|run (?:the )?tests before (?:the )?review)\b|'
        r'先测试再(?:审查|审阅)|先验证再(?:审查|审阅)'),
    ('language', 'en'): pattern(r'\b(?:(?:reply|answer|respond|write) in English|English replies please)\b|用英文(?:回答|回复|写)|请(?:说|用)英文'),
    ('language', 'zh'): pattern(r'\b(?:(?:reply|answer|respond|write) in (?:Simplified )?Chinese|Chinese replies please)\b|用中文(?:回答|回复|写)|请(?:说|用)中文'),
}

REPORT_CONTEXT = pattern(r'\b(?:colleague|teammate|friend|customer|client|someone|they|he|she)\b.{0,30}\b(?:said|says|wrote|asked|prefers?)\b|(?:同事|朋友|客户|别人|他|她|他们)(?:说|写|要求|希望|喜欢)')
NEGATION = pattern(r"(?:\b(?:don't|do not|never|stop|avoid|not)\s+(?:(?:just|always|only|simply)\s+)?|(?:不要|别|不用|无需)(?:再)?)$")

# These vocabularies describe grammatical roles and feedback targets. They are
# implementation-authored development rules, not a semantic model or a benchmark.
WORD_FORMS = dict(zip(
    'answers responses replies explanations introductions preambles examples illustrations snippets patches changes details words values samples bullets points steps reasons summaries paragraphs exercises tests commands sentences outputs inputs solutions cases stages calculations'.split(),
    'answer response reply explanation introduction preamble example illustration snippet patch change detail word value sample bullet point step reason summary paragraph exercise test command sentence output input solution case stage calculation'.split()))
WORD_FORMS.update({'showing':'show', 'responding':'respond', 'writing':'write', 'answering':'answer',
    'illustrating':'illustrate', 'demonstrating':'demonstrate', 'numbered':'number', 'bulleted':'bullet',
    'condensed':'condense', 'summarized':'summarize', 'ordered':'order', 'actions':'action', 'instructions':'instruction', 'grounded':'ground', 'solving':'solve',
    'solved':'solve', 'working':'work', 'worked':'work', 'skips':'skip', 'leaves':'leave',
    'needs':'need', 'restate':'explain', 'restating':'explain', 'came':'come'})
REPLY_WORDS = {'answer','response','reply','explanation','introduction','preamble','commentary','paragraph','summary','wording','detail','text','reasoning'}
BRIEF_WORDS = {'brief','briefer','brevity','concise','concisely','succinct','succinctly','short','shorter','shorten','terse','terser','compact','tighter','tighten','condense','compress','trim','pare','essentials','summarize'}
VERBOSE_WORDS = {'long','lengthy','verbose','verbosity','wordy','wordiness','rambling','ramble','fluff','padding','preamble','introduction','background','setup','essay'}
DETAIL_WORDS = {'detailed','thorough','thoroughly','comprehensive','depth','expand','elaborate','elaboration','unpack','fully','fuller','rationale'}
CODE_WORDS = {'code','patch','diff','implementation','snippet','change','command','script','sql','query'}
EXAMPLE_WORDS = {'example','illustration','demonstration','sample','scenario','case','dataset','calculation','problem'}
ILLUSTRATE_WORDS = {'illustrate','demonstrate','demystify','concretize','ground'}
ACTION_WORDS = {'give','show','include','add','use','provide','offer','supply','explain','illustrate','demonstrate','ground','make','teach','walk','solve','work'}
DIRECTIVE_VERBS = (r'make|keep|be|answer|respond|reply|write|cut|skip|drop|shorten|trim|pare|compress|condense|'
    r'reduce|tighten|expand|elaborate|include|add|show|give|put|start|lead|begin|open|use|format|'
    r'organize|break|list|spell|walk|work|illustrate|demonstrate|provide|offer|let|ask|check|'
    r'quiz|tell|suggest|plan|run|test|explain|paste|present|take|solve|unpack|boil|dial|have|teach|get|focus|stick|lay')
PRELUDE = r'(?:(?:please|kindly|hey|well|okay|actually|also|instead|so|thanks|first|just)[,:!\s]+)*'
REQUEST = pattern(
    r'^\s*'+PRELUDE+r'(?:(?:can|could|would|will|may)\s+(?:you|we|i|the|your|my|this|it|answers?|replies|responses?)\b|'
    r'i\s+(?:prefer|need|want|would\s+(?:like|prefer|appreciate|find)|could\s+use|wish|find|feel|learn\s+better)\b|'
    r'(?:'+DIRECTIVE_VERBS+r')\b)')
METALANGUAGE = pattern(
    r'^\s*(?:why\b|how\s+(?:do|does|did|can|could|would|should|might)\b|what\s+(?:does|do|if|is|are)\b|'
    r'would\s+it\s+be\b|(?:explain|define|translate|analy[sz]e)\s+(?:what|why|the\s+(?:phrase|sentence|term|request|example))\b)|'
    r'\b(?:(?:tell|explain|describe).{0,25}(?:why|whether|what .{0,15}means)|'
    r'(?:want|need|would like)\s+to\s+(?:know|understand)\b|'
    r'hypothetical|hypothetically|as an example|here(?:\x27s| is| are)\s+(?:an? |some )?(?:example|sample)|'
    r'i\s+(?:told|asked|instructed)\s+(?:him|her|them|my|a|the))\b|'
    r'^(?:为什么|为何|怎么判断|如何判断|举个反例|举一个反例|请?翻译)|'
    r'(?:这里|下面|以下).{0,15}(?:示例|例子)|(?:我|我们)(?:告诉|要求|让)(?:他|她|他们|同事|朋友)|'
    r'(?:想|希望|需要).{0,6}(?:知道|了解|理解).{0,10}(?:为什么|为何|如何|含义)|解释.{0,8}(?:为什么|为何)')
THIRD_PARTY = pattern(r'\b(?:my|our|the|a)\s+(?:colleague|teammate|friend|customer|client|manager|user|interviewee)\b|(?:我的|我们|这个|那位)?(?:同事|朋友|客户|别人|受访者|采访对象)(?:希望|想要|需要|要求|喜欢|认为|说)')
NEGATIVE_SCOPE = pattern(
    r'\b(?:not|never|no\s+(?:need|reason)|without|avoid|stop|cease|refrain|neither|nor|unnecessary|unwanted|'
    r'(?:do|does|did|is|was|are|were|should|would|could|can|have|has)n[\x27’]t|'
    r'don[\x27’]t|doesn[\x27’]t|didn[\x27’]t|isn[\x27’]t|wasn[\x27’]t|aren[\x27’]t|weren[\x27’]t|won[\x27’]t|can[\x27’]t)\b|'
    r'不要|不用|无需|不必|不需要|不希望|不能|不应|不可|勿|没必要|没有必要|并不是|并不想|不想|不是想|不是要|不是让|没让|未要求|没要求|别')
ZH_REPLY = r'(?:回答|回复|答复|解释|讲解|说明|表达|文字|铺垫|前言|结论|答案|复盘)'
ZH_CODE = r'(?:代码|补丁|实现|脚本|可运行.{0,5}片段|能直接运行.{0,5}片段|命令|差异)'
ZH_RESULT = r'(?:结论|答案|最终结果|最终结论)'
# A request to edit a particular artifact is not a request about collaboration.
# Rejecting these targets also prevents literal fallback cues from bypassing it.
ARTIFACT_STYLE = pattern(
    r'\b(?:shorten|trim|compress|condense|rewrite|refactor|simplify|tighten|make).{0,35}\b(?:code|function|file|article|essay|document|movie|walk|hike|database|table)\b|'
    r'\b(?:the|this|that|my|our|your|a)\s+(?:code|function|article|essay|document|movie|walk|hike|database|table)\b.{0,30}\b(?:too|shorter|shorten|compact|trim|brief|long|need)\b|'
    r'(?:代码|函数|文章|文件|文档|电影|数据库|表格).{0,20}(?:太长|冗长|精简|简短|压缩|缩短)|'
    r'(?:精简|压缩|缩短).{0,15}(?:代码|函数|文章|文件|文档|电影|数据库|表格)|'
    r'(?:简洁|简短|精炼).{0,3}(?:代码|函数|文章|文件|文档)')


def _words(text):
    return [WORD_FORMS.get(word, word) for word in re.findall(r'[a-z]+', text.casefold())]


def _eligible_clause(text, words):
    """Authored requests, evaluations and ellipses; never topic mentions alone."""
    vocabulary = set(words)
    if REQUEST.search(text):
        return True
    if re.search(r'\b(?:there is|that\x27s|this is)\b.{0,25}\b(?:too much|more detail|too long|too short)\b',text,re.I):
        return True
    if re.search(r'\bplease\s*$', text, re.I):
        return True
    if re.match(r'^\s*(?:a |the )?(?:short|brief|concise|compact)\s+(?:answer|reply|response)\b',text,re.I):
        return True
    if re.match(r'^\s*(?:too|less|fewer|more|just|a little|a bit|much|way)\b', text, re.I):
        return True
    if vocabulary & BRIEF_WORDS and vocabulary <= BRIEF_WORDS | {'please','a','bit','little','more','much','less','fewer','and'}:
        return True
    # Evaluations have a reply target and an evaluative predicate, rather than
    # only the presence of a format word somewhere in an unrelated sentence.
    evaluative = {'too','overly','excessively','should','ought','need','could','would','reads','like','taking','skip','leave','missing','buries','buried'}
    if vocabulary & (REPLY_WORDS | CODE_WORDS | EXAMPLE_WORDS | {'bullet','sentence','conclusion'}) and vocabulary & evaluative:
        return True
    if re.search(r'\bi\b.{0,15}\b(?:losing|lose|struggle|struggling)\b.{0,25}\b(?:point|answer)\b', text, re.I):
        return True
    if re.search(r'^\s*(?:请|麻烦|能否|能不能|能把|可不可以|可以|我(?:想|要|希望|需要|更想|更喜欢|更习惯)|把|帮我|给我|用|先|出|让|带|拿|配|建议|告诉|少|保留|直接)|'
        r'(?:回答|回复|答复|解释|讲解|说明|表达|文字|铺垫|前言|结论|答案|代码|补丁|复盘).{0,30}(?:太|实在|应该|最好|能不能|请|需要|希望|就|再|先|开头|控制|绕来绕去|更好|不够|费劲|压短|使用|写中文|保持|从.{0,8}开始|放.{0,5}前面)|'
        r'(?:太|过于简略|简短|简洁|精炼|精练|简练|浓缩|压缩|详细|展开|精简|少写|说重点|分步骤|一步一步|按步骤|举)|'
        r'(?:会|比较|更).{0,8}(?:好懂|好读|容易理解)|(?:讲|说)得太|(?:后续|以后|今后).{0,12}请|让我(?:复述|解释)|先征求我|在这里回答|我要的是', text):
        return True
    return False


def _negative_correction(text):
    """Only invert an explicit complaint about excess prose, never a language.

    This handles 'stop rambling' without treating 'do not be concise' as a
    concise request. A rejected language, format, or teaching method abstains.
    """
    if ARTIFACT_STYLE.search(text):
        return set()
    if re.search(r'^\s*(?:please\s+)?(?:stop|avoid|quit|don\x27t|do not)\s+(?:the\s+)?(?:rambling|waffling|padding|(?:write|writing)\s+(?:an?\s+)?essay|(?:give|giving|write|writing)\s+(?:me\s+)?a wall of text)\b', text, re.I):
        return {('response_length','concise')}
    if re.search(r'^\s*(?:请)?(?:别|不要|不用)(?:再)?(?:啰嗦|废话|说这么多|写这么多|写长篇大论)', text):
        return {('response_length','concise')}
    return set()


def _composed_cues(text):
    """Compose intent, target and direction within a bounded authored clause."""
    lower = text.casefold()
    words = _words(lower)
    vocabulary = set(words)
    if not _eligible_clause(lower, words):
        return set()
    cues = set()
    request = bool(REQUEST.search(lower))
    reply = bool(vocabulary & REPLY_WORDS or re.search(ZH_REPLY,text))
    artifact = bool(ARTIFACT_STYLE.search(text))
    brief = bool(vocabulary & BRIEF_WORDS)
    excessive = bool(vocabulary & {'too','overly','excessively','rather','far','reads','like'} and vocabulary & VERBOSE_WORDS)
    reducing = bool((request or vocabulary & {'less','fewer'}) and vocabulary & {'cut','skip','drop','reduce','less','fewer','trim','pare'} and vocabulary & (VERBOSE_WORDS | REPLY_WORDS | {'word'}))
    addressed_style = request and bool(vocabulary & {'it','this','version','review','reviews','be','reply','respond','answer'})
    excess_detail = bool(re.search(r'\b(?:more|too much)\s+detail\b.{0,25}\b(?:than|again)\b',lower))
    short_correction = brief and vocabulary <= BRIEF_WORDS | {'please','a','bit','little','more','much','less','fewer','and','just','the'}
    concise_expression = bool(re.search(
        r'\b(?:get|come|stick)\s+(?:straight |directly )?to\s+(?:the )?point\b|\b(?:boil|dial|cut|strip|scale)\b.{0,40}\b(?:down|back)\b|'
        r'\b(?:just|only)\s+(?:the )?(?:essentials|key points|gist|core)\b|\b(?:couple|few|one|two|three|1|2|3)\b.{0,12}\bsentences?\b|'
        r'\b(?:wall of text|taking paragraphs|losing the point)\b', lower))
    zh_brief = bool(re.search(r'精炼|精练|简练|简明|浓缩|压缩|压短|缩短|收紧|精简|抓住重点|简洁|简短|太长|短答复|短些|短点|短一点|少一点|少些|啰嗦|冗长|废话|干脆|绕来绕去|'
        r'(?:保留|只讲|只说).{0,8}(?:核心|关键|重点)|(?:直接|少).{0,8}(?:重点|铺垫|前言)|(?:说|讲)得太多|'
        r'(?:控制|只要|用).{0,6}(?:两三|几|一|二|三|1|2|3).{0,3}句话|(?:两三|几|一|二|三|1|2|3).{0,3}句话.{0,4}(?:够|就好)|(?:铺垫|前言).{0,10}(?:太多|多了)',text))
    if not artifact and ((brief and (reply or addressed_style)) or excessive or reducing or short_correction or concise_expression or zh_brief or excess_detail):
        cues.add(('response_length','concise'))
    omitted_reasoning = bool(re.search(r'\b(?:skip|skips|leave out|leaves out|missing|fill(?:ed)? in)\b.{0,35}\b(?:reasoning|explanation|detail)\b',lower))
    if not artifact and not excess_detail and ((vocabulary & DETAIL_WORDS and (reply or request)) or (vocabulary & {'more','missing','additional'} and 'detail' in vocabulary) or omitted_reasoning or re.search(r'\bin detail\b',lower) or (vocabulary & {'too'} and vocabulary & {'brief','short','terse'})):
        cues.add(('response_length','detailed'))
        if vocabulary & {'too'} and vocabulary & {'brief','short','terse'}:
            cues.discard(('response_length','concise'))
    if not artifact and re.search(r'详细|细节.{0,10}(?:讲透|讲清|展开)|太简略|太简短|太笼统|展开.{0,10}(?:讲|说)|'
        r'(?:解释|讲解|说明).{0,12}不够(?:完整|详细)|(?:推导|细节|道理|理由).{0,8}(?:讲清|讲透|展开)|过于简略|(?:论证|解释|说明).{0,8}充分|(?:完整|关键).{0,5}细节|(?:关键推导).{0,15}(?:需要|说明)',text):
        cues.add(('response_length','detailed'))
        if re.search(r'太简短|简略|(?:只给|省掉).{0,20}(?:几句话|细节)|(?:关键|完整).{0,5}细节', text):
            cues.discard(('response_length','concise'))

    # Directed relations attach an opening/ordering verb to its object. A mere
    # co-occurrence of 'first' and 'code' could mean 'first explain the code'.
    code = r'(?:code|patch|diff|implementation|snippet|changes?|commands?|scripts?|sql|quer(?:y|ies)|something i can run)'
    result = r'(?:answer|conclusion|result|bottom line)'
    explanation = r'(?:explanation|commentary|walkthrough|reasoning|reasons?|analysis|discussion|prose|details?|explaining)'
    front = r'(?:first|up front|at the (?:top|start|beginning)|(?:ahead of|before)\s+(?:\w+\s+){0,5}'+explanation+r'|(?:should |could |would )?(?:lead|start|open)\s+(?:the |your )?(?:answer|reply|response))'
    opener = r'(?:start|begin|open|lead(?:\s+off)?)\s+(?:(?:your|the|this)\s+(?:answer|reply|response)\s+)?(?:with|by\s+(?:showing|giving|presenting))'
    for target, value in [(code,'code_first'),(result,'conclusion_first')]:
        describing = re.search(r'\b(?:explain|describe|discuss|analy[sz]e)\b[^,;]{0,20}\b'+target+r'\b',lower)
        ordered_target = re.search(r'\b'+target+r'\b[^,;]{0,35}\b'+front+r'\b',lower)
        opening_target = re.search(r'\b'+opener+r'\b[^,;]{0,35}\b'+target+r'\b',lower)
        leading_target = re.search(r'\bfirst\b\s+(?:\w+\s+){0,3}(?:show|give|paste|present|display)\b[^,;]{0,25}\b'+target+r'\b',lower)
        if not describing and (ordered_target or opening_target or leading_target):
            cues.add(('structure',value))
    if re.search(r'\b(?:give|show|paste|provide)\b.{0,50}\b(?:code|patch|diff|snippet|implementation|command|something i can paste)\b.{0,30}\b(?:then|afterward)\b.{0,30}\b(?:explain|talk|walk|reasoning)\b',lower):
        cues.add(('structure','code_first'))
    zh_order = list(re.finditer(r'(?:先|首先|开头|一开始)(.{0,18}?)'+ZH_CODE,text))
    if any(not re.search(r'解释|讲解|分析|说明|讨论',match.group(1)) for match in zh_order) or re.search(ZH_CODE+r'(?!说明|解释|分析).{0,12}(?:先(?:贴|给|展示|看)|(?:放|提到).{0,5}(?:前面|前头|开头|最前|最上面)|优先)',text) or re.search(ZH_CODE+r'.{0,20}(?:然后|再|后面).{0,10}(?:解释|讲解|说明|分析)',text):
        cues.add(('structure','code_first'))
    if re.search(r'(?:回复|回答|答复).{0,6}从'+ZH_CODE+r'开始|先.{0,15}(?:怎么写|写法).{0,35}(?:直接试|运行|执行)',text):
        cues.add(('structure','code_first'))
    if re.search(r'(?:先|首先|开头|一开始)(?:(?!解释|分析|讲解|代码|补丁).){0,14}'+ZH_RESULT+'|'+ZH_RESULT+r'.{0,20}(?:前面|前头|开头|最前|优先)',text):
        cues.add(('structure','conclusion_first'))

    # A worked example requires a concrete case plus its process, not merely
    # another example. It is a teaching method, separate from including examples.
    concrete = bool(vocabulary & EXAMPLE_WORDS or vocabulary & {'number','numbers','data','input','output','solution'})
    process = bool(re.search(r'\b(?:work|walk|talk|take)\b.{0,20}\bthrough\b|\bfrom\b.{0,15}\binput\b.{0,15}\bto\b.{0,15}\boutput\b|'
        r'\b(?:complete|whole|entire|each|every|intermediate)\b.{0,25}\b(?:step|steps|stage|stages|process|solution|example)\b|'
        r'\b(?:worked|solve|solved|solving)\b|\b(?:numbers?|numeric)\b.{0,25}\bbefore\b.{0,20}\b(?:rule|theory|formula)\b',lower))
    zh_concrete = bool(re.search(r'例子|示例|案例|实例|样例|例题|数字|数据|输入|输出|求解|具体交易',text))
    zh_process = bool(re.search(r'每一?步|一步步|中间结果|从头.{0,4}到尾|从.{0,6}输入.{0,12}(?:到|至)输出|完整.{0,8}(?:算|做|过程|求解)|'
        r'(?:走|算|做|演示|示范).{0,10}(?:一遍|整个过程|完整|做完|例题|数字)|(?:例子|例题).{0,8}(?:算给|算出|做给)|(?:带我|带着我).{0,18}(?:做|走)|先演示一遍',text))
    worked = (concrete and process) or (zh_concrete and zh_process)
    if worked:
        cues.add(('teaching','worked_example'))
    elif (vocabulary & EXAMPLE_WORDS and (request or vocabulary & (ACTION_WORDS|{'need','could','should'}))) or (vocabulary & ILLUSTRATE_WORDS and vocabulary & {'idea','concept','data','value','input','output','problem','situation'}) or re.search(r'(?:例子|示例|案例|实例)|(?:具体|实际|输入|输出).{0,20}(?:演示|展示)|(?:演示|展示).{0,20}(?:数据|输入|输出)|具体场景',text):
        cues.add(('structure','examples'))
    if 'bullet' in vocabulary or re.search(r'项目符号|要点列表|分点.{0,8}(?:列|写|说)|列成要点',text):
        cues.add(('structure','bullets'))
    if (vocabulary & {'step','action','checklist','procedure'} and (vocabulary & {'number','sequence','sequential','list','break','organize','order','ordered'} or 'step by step' in lower)) or re.search(r'分步骤|一步一步|按步骤|拆成.{0,5}步|(?:编号|序号).{0,6}步骤|步骤.{0,6}(?:编号|序号)',text):
        cues.add(('structure','steps'))
    if re.search(r'\b(?:let|have|ask)\s+me\b.{0,30}\b(?:explain|restate|retell)\b.{0,30}\b(?:back|own words)\b',lower) or re.search(r'让我.{0,8}(?:复述|用自己的话)',text):
        cues.add(('teaching','explain_back'))
    if re.search(r'(?:之前|以前|先).{0,10}(?:征求|问|确认).{0,6}我',text):
        cues.add(('initiative','ask_first'))
    if vocabulary & {'english','chinese'} and (vocabulary & {'reply','answer','respond','write','written'} or request and vocabulary & {'it','this','these'}):
        for language,value in [('english','en'),('chinese','zh')]:
            if language in vocabulary:
                cues.add(('language',value))
    if re.search(r'(?:英文|英语|中文|汉语|简体中文).{0,8}(?:回答|回复|答复|作答)|(?:回答|回复|答复|作答).{0,12}(?:英文|英语|中文|汉语)|(?:用|采用|使用|保持).{0,5}(?:英文|英语|中文|汉语)',text):
        if re.search(r'英文|英语',text):
            cues.add(('language','en'))
        if re.search(r'中文|汉语',text):
            cues.add(('language','zh'))
    return cues


def _clause_cues(clause):
    if len(clause)>600 or len(_words(clause))>80:
        return set()
    if METALANGUAGE.search(clause):
        return set()
    guard = re.sub(r'能不能|可不可以', '', clause)
    if NEGATIVE_SCOPE.search(guard):
        return _negative_correction(clause)
    cues = _composed_cues(clause)
    if not _eligible_clause(clause,_words(clause)):
        return cues
    for (dimension,value), expression in CUES.items():
        # Length and ordering use the target-aware grammar, not a substring
        # escape hatch. Other bounded legacy cues remain useful for short text.
        if dimension=='response_length' or value in {'code_first','conclusion_first','examples'}:
            continue
        if expression.search(clause):
            cues.add((dimension,value))
    return cues


def _temporary_feedback(text):
    # A completed-event complaint ("this happened again") is not a one-off
    # instruction. Only remove that bounded past-tense clause for this check.
    checked = re.sub(r'(?:这次|本次)(?:也是|还是|又)(?:(?!请|只要|希望|需要).){0,100}了[。！？]', '', text)
    return bool(TEMPORARY.search(checked) or re.search(
        r'\b(?:for|in)\s+this\s+(?:single\s+)?(?:reply|answer|message|handout)\b|'
        r'\b(?:do not|don\x27t)\s+(?:save|remember|learn).{0,20}(?:preference|habit)\b|'
        r'只针对这一|不要记成长期|别记成长期', checked,re.I))


def _sentence_cues(sentence):
    requested = re.split(r'\b(?:rather than|instead of|without)\b',sentence,maxsplit=1,flags=re.I)[0].strip()
    parts = re.split(r'[,，]|\bbut\b',requested,flags=re.I)
    full = _clause_cues(requested)
    if len(parts)==1:
        return full
    # Keep cross-clause order/process relations. Dependent phrases such as
    # ", with more detail" or ", please" are still part of the same request.
    dependent = all(re.match(r'^\s*(?:with|using|because|so|please)\b',part,re.I) for part in parts[1:])
    cues = full if dependent else {c for c in full
        if c in {('structure','code_first'),('teaching','worked_example')}}
    cues.update(_clause_cues(parts[0].strip()))
    for part in parts[1:]:
        # 'and' does not end a negative scope ("do not X and Y").
        if _eligible_clause(part.strip(),_words(part)) or re.match(r'^\s*(?:别|不要)',part):
            cues.update(_clause_cues(part.strip()))
    # An omitted object after a comma still refers to the named artifact:
    # "this function is long, shorten it" is not a reply-length preference.
    if ARTIFACT_STYLE.search(requested):
        cues = {c for c in cues if c[0]!='response_length'}
    return cues


def extract_feedback(text):
    """Return exact sourced cues; unsupported or ambiguous feedback abstains.

    Requests, short corrections and evaluations are parsed per clause. Negation
    blocks its own clause; only explicit complaints about excess prose are
    inverted. A quoted/reported or temporary paragraph still blocks all cues.
    """
    if not safe_candidate_text(text):
        return []
    masked = extraction_mask(text)
    found = {}
    reported_paragraph = False
    for original_line,line in zip(text.splitlines(),masked.splitlines()):
        if not line.strip():
            if not original_line.strip():
                reported_paragraph = False
            continue
        if REPORTED.search(line) or REPORT_CONTEXT.search(line) or THIRD_PARTY.search(line) or METALANGUAGE.match(line):
            reported_paragraph = True
        if reported_paragraph or _temporary_feedback(line) or original_line!=line:
            continue
        normalized = re.sub(r"\bI'd\b", 'I would', line.replace('’',"'"), flags=re.I)
        normalized = re.sub(r'^\s*(?:for future (?:replies|answers|responses)|going forward|from now on)[,:\s]*', '', normalized, flags=re.I)
        cues = set()
        for sentence in re.split(r'[.!?。！？；;]+',normalized):
            cues.update(_sentence_cues(sentence))
        if ('teaching','worked_example') in cues:
            cues.discard(('structure','examples'))
        for dimension,value in cues:
            if value in DIMENSIONS.get(dimension,()):
                found.setdefault(dimension,{}).setdefault(value,line.strip())
    return [{'dimension':dimension,'value':next(iter(values)),'signal':'positive',
             'quote':next(iter(values.values()))}
            for dimension,values in sorted(found.items()) if len(values)==1]


def discover_habits(profile, context, now=None):
    """Compute candidates from the current source set without modifying it."""
    key = context_key(context)
    result = {'subject_id': profile['subject_id'], 'revision': profile['revision'],
              'paused': profile['paused'], 'context': key, 'candidates': [],
              'method': 'recurring_authored_feedback',
              'limits': ['Bounded English/Chinese request and correction grammar; not unrestricted semantic learning.',
                         'Session labels are host-supplied, not verified unique people or consent.',
                         'Candidates require review before becoming response preferences.']}
    if profile['paused']:
        return result
    ephemeral = copy.deepcopy(profile)
    ephemeral['observations'] = {}
    ephemeral['dismissed_candidates'] = {}
    sources = {}
    for message in profile.get('conversation_messages', {}).values():
        if message['context'] != key:
            continue
        for cue in extract_feedback(message['excerpt']):
            dimension = cue['dimension']
            event_id = 'habit-event-' + fingerprint({'key': message['key'], 'cue': cue})[:32]
            ephemeral['observations'][event_id] = {'id': event_id, 'source_id': message['source_id'],
                'session_id': message['session_key'], 'context': key, 'dimension': dimension,
                'value': cue['value'], 'signal': cue['signal'], 'occurred_at': message['at']}
            sources.setdefault(dimension, []).append({'source_key': message['key'], 'quote': cue['quote'],
                'session_key': message['session_key'], 'at': message['at'],
                'dimension': dimension, 'value': cue['value']})
    for item in insights(ephemeral, context, now=now)['candidates']:
        evidence = sorted(sources[item['dimension']], key=lambda row: (row['at'], row['source_key']))
        # Bind all evidence, including older/shadowed messages, to both candidate
        # identity and deletion provenance. Effective voting remains latest/session.
        candidate_id = 'habit-' + fingerprint({'candidate': item['candidate_id'], 'evidence': evidence})[:32]
        if candidate_id in profile.get('dismissed_habits', {}):
            continue
        result['candidates'].append({**item, 'candidate_id': candidate_id,
            'statement': STATEMENTS[item['dimension']][item['value']],
            'source_keys': sorted({row['source_key'] for row in evidence}), 'evidence': evidence,
            'reasons': item['reasons'] + ['Found in authored conversation feedback; no observation labels were supplied by a caller.',
                                        'Source links include shadowed evidence so forgetting cannot revive older support.']})
    return result
