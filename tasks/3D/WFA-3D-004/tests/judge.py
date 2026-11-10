"""Gemini judge adapter for the task rubric's judge(prompt, images) contract."""
import json
import os
from pathlib import Path
from gemini_client import JudgeError, judge as gemini_judge, media


def image_mime(path):
    with open(path, 'rb') as handle:
        head = handle.read(12)
    if head.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if head.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        return 'image/webp'
    raise JudgeError('Unsupported evidence image format')


def judge(prompt, images):
    response = gemini_judge(prompt, [media(p, image_mime(p)) for p in images],
                            max_tokens=int(os.environ.get('JUDGE_MAX_TOKENS', '6000')))
    verdict = response['verdict']
    if not isinstance(verdict, dict) or any(
        not isinstance(v, dict) or v.get('verdict') not in ('pass', 'fail', 'na')
        for v in verdict.values()
    ):
        raise JudgeError('Malformed rubric verdict')
    log = Path(os.environ.get('WS_LOG', '/logs/verifier'))
    log.mkdir(parents=True, exist_ok=True)
    with (log / 'judge-usage.jsonl').open('a') as handle:
        handle.write(json.dumps({k: response[k] for k in
                                ('model', 'model_version', 'usage', 'attempts')}) + '\n')
    return verdict
