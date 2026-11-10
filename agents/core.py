"""Four specialized agents: LLM reasoning, validated JSON, real auditable tool calls."""
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / 'logs' / 'execution.jsonl'
OUT = ROOT / 'outputs'


def record(event: str, **fields: Any) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    item = {'timestamp': datetime.now(timezone.utc).isoformat(), 'event': event, **fields}
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(item, default=str) + '\n')
    print(json.dumps(item, indent=2, default=str))


def write_json(name: str, value: dict) -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')
    record('tool_result', tool='write_json', path=str(path.relative_to(ROOT)), status='success')
    return str(path)


SYSTEMS = {
    'requirements': '''You are a cloud requirements analyst. Interpret requests for a five-page static AWS website. Return ONLY a JSON object with keys summary (str), pages (list of exactly 5 distinct strings), services (list of strings), security_requirements (list of strings), questions (list of strings). Never claim deployment has occurred.''',
    'infrastructure': '''You are an AWS infrastructure planner. Based on validated requirements, propose secure S3/CloudFront/ACM/Route53 infrastructure. Return ONLY JSON with keys plan (list of strings), services (list of strings), dependencies (list of strings), risks (list of strings). No AWS calls or success claims.''',
    'security': '''You are a cloud security reviewer. Inspect the proposed architecture. Return ONLY JSON with keys findings (list of strings), controls (list of strings), requires_human_approval (list of strings), approved_for_deployment (boolean). Set approved_for_deployment false if details are uncertain; approval means a recommendation only, NOT actual human authorization.''',
    'verification': '''You are an independent site verification and recovery advisor. Evaluate observed checks (not guesses). Return ONLY JSON with keys diagnosis (str), corrective_actions (list of strings), checks_passed (list of strings), checks_failed (list of strings), needs_human_approval (boolean). Never say success when checks failed or were not run.'''
}
SCHEMAS = {
    'requirements': {'summary': str, 'pages': list, 'services': list, 'security_requirements': list, 'questions': list},
    'infrastructure': {'plan': list, 'services': list, 'dependencies': list, 'risks': list},
    'security': {'findings': list, 'controls': list, 'requires_human_approval': list, 'approved_for_deployment': bool},
    'verification': {'diagnosis': str, 'corrective_actions': list, 'checks_passed': list, 'checks_failed': list, 'needs_human_approval': bool},
}


def validate(role: str, output: Any) -> dict:
    if not isinstance(output, dict):
        raise ValueError('Expected JSON object')
    for field, field_type in SCHEMAS[role].items():
        if field not in output or type(output[field]) is not field_type:
            raise ValueError(f'{role}.{field} must be {field_type.__name__}')
        if field_type is list and not all(isinstance(x, str) for x in output[field]):
            raise ValueError(f'{role}.{field} must contain strings')
    if role == 'requirements' and len(output['pages']) != 5:
        raise ValueError('Exactly five pages required')
    return output


def run_agent(role: str, payload: dict) -> dict:
    if role not in SYSTEMS:
        raise ValueError('Unknown agent')
    if not os.getenv('OPENAI_API_KEY'):
        raise RuntimeError('OPENAI_API_KEY missing: copy .env.example to .env and add your key')
    record('agent_input', agent=role, payload=payload)
    from openai import OpenAI
    client = OpenAI()
    model = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
    last_error = None
    for attempt in range(1, 3):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{'role': 'system', 'content': SYSTEMS[role]},
                          {'role': 'user', 'content': json.dumps(payload)}],
                response_format={'type': 'json_object'}, temperature=0)
            raw = response.choices[0].message.content
            result = validate(role, json.loads(raw))
            record('agent_decision', agent=role, model=model, attempt=attempt, decision=result)
            write_json(f'{role}.json', result)
            return result
        except Exception as exc:
            last_error = str(exc)
            record('agent_error', agent=role, attempt=attempt, error=last_error)
    raise RuntimeError(f'Agent {role} failed: {last_error}')
