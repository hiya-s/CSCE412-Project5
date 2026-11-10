REAL EXECUTION LOGS — README template

Execution date/time: [actual]
Model/provider: [actual]
Website URL: [actual]
Sequence:
1. requirements agent: outputs/requirements.json
2. infrastructure agent: outputs/infrastructure.json
3. security agent: outputs/security.json
4. deterministic local/HTTP/AWS tools: logs/execution.jsonl
5. verification agent: outputs/verification.json
6. failure/restore runs: logs/execution.jsonl

Explanation: These files are generated from actual agent/tool execution. No log is an invented success claim. Redact secrets/tokens/personal data before submission. Include real failure and recovery entries after running the AWS demonstration.
