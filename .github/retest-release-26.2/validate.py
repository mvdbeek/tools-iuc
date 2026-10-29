"""Require complete coverage of the selected original failures, including no empty green runs."""
import json
import os
from pathlib import Path
import sys


def key(test):
    data = test['data']
    return data['tool_id'], data['tool_version'], data['test_index']


tool_ids = set(os.environ['TOOL_IDS'].split(','))
previous = json.loads(Path(__file__).with_name('previous-failures.json').read_text())
expected = {key(t) for t in previous['tests'] if t['data']['tool_id'] in tool_ids}
assert expected, 'No tests selected'
if '--list' in sys.argv:
    for tool, version, index in sorted(expected):
        print(f'{tool} {version}, test {index + 1}')
    sys.exit(0)

report = json.loads(Path('upload/tool_test_output.json').read_text())
tests = report['tests']
actual = {key(t) for t in tests}
lines = ['| Tool | Version | Test | Result |', '|---|---|---|---|']
for test in tests:
    tool, version, index = key(test)
    lines.append(f"| {tool} | {version} | {index + 1} | {test['data']['status']} |")
summary = '\n'.join(lines) + '\n'
print(summary)
if os.environ.get('GITHUB_STEP_SUMMARY'):
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as handle:
        handle.write(summary)
assert actual == expected, f'Missing tests: {expected - actual}; unexpected tests: {actual - expected}'
assert len(tests) == len(expected), 'Duplicate test results'
assert all(t['data']['status'] == 'success' for t in tests), 'Some selected tests still fail'
