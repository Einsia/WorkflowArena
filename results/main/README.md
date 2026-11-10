# Main experiment

These tables reproduce the paper-reported aggregates for 25 model-effort configurations across 145 tasks. Overall is the equal-weight mean of eight domain values.

## Resolved rates (%)

A task is resolved when all required acceptance criteria hold. Paper Table 1, page 7.

| model | harness | effort | overall | SWE | OPS | SCI | MATH | FIN | LAW | CDN | 3D |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Claude Opus 5.5 | Claude Code | max | 36.95 | 29.41 | 22.22 | 56.25 | 95.83 | 12.50 | 0.00 | 57.14 | 22.22 |
| Claude Opus 5.5 | Claude Code | high | 34.11 | 17.65 | 16.67 | 50.00 | 87.50 | 18.75 | 4.55 | 50.00 | 27.78 |
| Claude Opus 5.5 | Claude Code | xhigh | 33.23 | 11.76 | 16.67 | 43.75 | 91.67 | 12.50 | 4.55 | 57.14 | 27.78 |
| Claude Sonnet 5.5 | Claude Code | max | 33.21 | 11.76 | 11.11 | 50.00 | 79.17 | 12.50 | 9.09 | 64.29 | 27.78 |
| GPT-6 Astra | Codex | xhigh | 30.80 | 0.00 | 22.22 | 50.00 | 83.33 | 12.50 | 4.55 | 57.14 | 16.67 |
| GPT-6 Astra | Codex | high | 29.82 | 0.00 | 27.78 | 43.75 | 83.33 | 12.50 | 4.55 | 50.00 | 16.67 |
| GPT-6.1 Sol | Codex | xhigh | 29.50 | 0.00 | 16.67 | 43.75 | 79.17 | 12.50 | 4.55 | 57.14 | 22.22 |
| Claude Opus 5.5 | Claude Code | medium | 29.14 | 11.76 | 16.67 | 50.00 | 70.83 | 18.75 | 0.00 | 42.86 | 22.22 |
| GPT-6 Astra | Codex | medium | 28.11 | 0.00 | 16.67 | 43.75 | 79.17 | 12.50 | 4.55 | 57.14 | 11.11 |
| GPT-6.1 Sol | Codex | max | 28.04 | 0.00 | 22.22 | 43.75 | 83.33 | 12.50 | 4.55 | 35.71 | 22.22 |
| GPT-6 Astra | Codex | low | 27.80 | 5.88 | 16.67 | 43.75 | 70.83 | 12.50 | 4.55 | 57.14 | 11.11 |
| GPT-6.1 Sol | Codex | low | 27.59 | 0.00 | 16.67 | 43.75 | 75.00 | 12.50 | 4.55 | 57.14 | 11.11 |
| GPT-6 Astra | Codex | max | 27.34 | 0.00 | 22.22 | 43.75 | 83.33 | 12.50 | 4.55 | 35.71 | 16.67 |
| GPT-6.1 Sol | Codex | medium | 27.30 | 0.00 | 11.11 | 43.75 | 79.17 | 18.75 | 4.55 | 50.00 | 11.11 |
| GPT-6.1 Sol | Codex | high | 25.63 | 0.00 | 22.22 | 43.75 | 79.17 | 12.50 | 4.55 | 42.86 | 0.00 |
| Claude Sonnet 5.5 | Claude Code | high | 25.26 | 0.00 | 11.11 | 43.75 | 62.50 | 12.50 | 0.00 | 50.00 | 22.22 |
| Claude Sonnet 5.5 | Claude Code | xhigh | 23.24 | 0.00 | 11.11 | 43.75 | 70.83 | 6.25 | 0.00 | 42.86 | 11.11 |
| Claude Opus 5.5 | Claude Code | low | 22.02 | 0.00 | 11.11 | 43.75 | 66.67 | 6.25 | 0.00 | 42.86 | 5.56 |
| Claude Sonnet 5.5 | Claude Code | medium | 19.78 | 0.00 | 11.11 | 37.50 | 58.33 | 18.75 | 0.00 | 21.43 | 11.11 |
| Claude Sonnet 5.5 | Claude Code | low | 16.88 | 0.00 | 5.56 | 37.50 | 54.17 | 6.25 | 4.55 | 21.43 | 5.56 |
| Kimi K3.1 Pro | Claude Code | max | 16.48 | 0.00 | 16.67 | 43.75 | 37.50 | 12.50 | 0.00 | 21.43 | 0.00 |
| GPT-6 Luna | Codex | max | 13.32 | 0.00 | 5.56 | 37.50 | 25.00 | 12.50 | 4.55 | 21.43 | 0.00 |
| Doubao-Seed-Evolving | Claude Code | high | 10.84 | 0.00 | 27.78 | 31.25 | 0.00 | 6.25 | 0.00 | 21.43 | 0.00 |
| DeepSeek V4.1 Flash | Claude Code | max | 6.08 | 0.00 | 11.11 | 25.00 | 0.00 | 12.50 | 0.00 | 0.00 | 0.00 |
| GLM-5.3 Flash | Claude Code | max | 4.43 | 0.00 | 16.67 | 18.75 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

## Continuous scores (0-100)

Continuous scores credit partial progress. Paper Table 6, page 21.

| model | harness | effort | overall | SWE | OPS | SCI | MATH | FIN | LAW | CDN | 3D |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Claude Opus 5.5 | Claude Code | high | 80.21 | 96.98 | 54.94 | 87.97 | 97.44 | 81.69 | 74.36 | 79.72 | 68.60 |
| Claude Opus 5.5 | Claude Code | max | 79.94 | 79.26 | 52.91 | 94.71 | 95.83 | 87.79 | 74.63 | 82.60 | 71.82 |
| Claude Opus 5.5 | Claude Code | xhigh | 78.77 | 91.10 | 50.03 | 82.03 | 97.67 | 84.29 | 74.64 | 83.13 | 67.27 |
| GPT-6 Astra | Codex | xhigh | 77.69 | 74.24 | 62.65 | 82.18 | 96.96 | 84.01 | 73.58 | 81.86 | 66.05 |
| GPT-6.1 Sol | Codex | xhigh | 77.52 | 76.11 | 65.68 | 82.21 | 95.35 | 85.02 | 71.10 | 81.65 | 63.05 |
| GPT-6 Astra | Codex | max | 77.29 | 74.67 | 64.97 | 78.78 | 97.20 | 82.30 | 73.30 | 80.14 | 66.93 |
| GPT-6.1 Sol | Codex | max | 76.50 | 71.19 | 72.97 | 79.76 | 95.36 | 77.43 | 71.36 | 77.66 | 66.28 |
| GPT-6 Astra | Codex | high | 76.47 | 77.85 | 64.84 | 78.74 | 95.84 | 80.92 | 70.64 | 79.08 | 63.87 |
| GPT-6.1 Sol | Codex | low | 76.32 | 78.43 | 62.06 | 82.43 | 91.02 | 82.05 | 70.91 | 80.84 | 62.85 |
| GPT-6 Astra | Codex | medium | 76.12 | 76.09 | 64.02 | 77.46 | 92.63 | 83.00 | 71.01 | 80.04 | 64.67 |
| GPT-6.1 Sol | Codex | high | 76.11 | 76.16 | 66.58 | 79.47 | 94.71 | 81.33 | 70.79 | 76.25 | 63.56 |
| GPT-6.1 Sol | Codex | medium | 74.87 | 76.82 | 63.98 | 78.57 | 88.06 | 75.57 | 72.72 | 80.38 | 62.84 |
| Claude Opus 5.5 | Claude Code | medium | 74.39 | 84.86 | 53.04 | 86.26 | 77.63 | 80.94 | 72.26 | 77.50 | 62.63 |
| GPT-6 Astra | Codex | low | 74.02 | 71.64 | 63.28 | 77.82 | 83.11 | 80.05 | 71.99 | 80.88 | 63.42 |
| Claude Sonnet 5.5 | Claude Code | max | 73.11 | 73.35 | 52.45 | 84.31 | 90.39 | 70.23 | 61.84 | 80.97 | 71.32 |
| Claude Opus 5.5 | Claude Code | low | 72.44 | 84.50 | 45.70 | 79.14 | 72.44 | 77.59 | 73.87 | 78.61 | 67.62 |
| Claude Sonnet 5.5 | Claude Code | high | 70.15 | 69.87 | 45.61 | 77.36 | 79.58 | 70.71 | 71.61 | 79.80 | 66.61 |
| Claude Sonnet 5.5 | Claude Code | xhigh | 70.00 | 80.18 | 37.95 | 82.11 | 81.00 | 58.01 | 73.75 | 81.79 | 65.18 |
| Claude Sonnet 5.5 | Claude Code | medium | 63.90 | 67.96 | 43.01 | 72.45 | 70.56 | 49.67 | 71.40 | 74.33 | 61.82 |
| Claude Sonnet 5.5 | Claude Code | low | 63.71 | 60.37 | 45.57 | 68.78 | 70.76 | 62.20 | 70.16 | 73.71 | 58.11 |
| Kimi K3.1 Pro | Claude Code | max | 62.73 | 52.79 | 50.35 | 74.10 | 54.37 | 67.26 | 74.14 | 76.94 | 51.86 |
| GPT-6 Luna | Codex | max | 55.44 | 51.66 | 34.36 | 66.87 | 36.55 | 68.50 | 66.24 | 76.20 | 43.12 |
| Doubao-Seed-Evolving | Claude Code | high | 48.66 | 35.87 | 52.73 | 63.68 | 4.07 | 55.12 | 70.29 | 66.47 | 41.04 |
| GLM-5.3 Flash | Claude Code | max | 39.03 | 25.75 | 50.60 | 54.99 | 7.61 | 57.13 | 63.90 | 21.56 | 30.71 |
| DeepSeek V4.1 Flash | Claude Code | max | 34.48 | 34.45 | 43.48 | 52.25 | 10.36 | 46.81 | 56.28 | 0.00 | 32.25 |

Machine-readable tables: [resolved rates](resolved_rates.json) and [continuous scores](continuous_scores.json).
