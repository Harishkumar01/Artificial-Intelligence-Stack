"""Local setup checks; does not call any API or complete starter exercises."""
import ast
import importlib
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
if Path.cwd().resolve() != root:
    raise SystemExit('Run this command from the bundle root containing README.md.')
if sys.version_info < (3, 12):
    raise SystemExit('Python 3.12 or 3.13 is required.')
from dotenv import dotenv_values
print('Python:', sys.version.split()[0])
for requirement in (root / 'requirements.txt').read_text().splitlines():
    if requirement.startswith(('#', '-')) or not requirement.strip():
        continue
    name = requirement.split('==')[0]
    module = {'openai-agents': 'agents', 'python-dotenv': 'dotenv'}.get(name, name)
    importlib.import_module(module)
    print('Import OK:', module)
for path in sorted((root / 'labs').rglob('*.py')):
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path.relative_to(root)))
print('Python syntax OK (starters may still be intentionally incomplete)')
for path in sorted((root / 'labs/data').glob('sample_*.jsonl')):
    rows = [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]
    assert rows and all(isinstance(x.get('item'), dict) and 'input' in x['item'] for x in rows)
    print('Dataset:', path.name, len(rows), 'rows')
key = dotenv_values(root / '.env').get('OPENAI_API_KEY')
print('Root .env API key:', 'present (access unverified)' if key else 'missing; complete credential setup before paid tasks')
print('No API calls made.')
