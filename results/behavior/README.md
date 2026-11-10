# Delegation and resource use

These are the figures as reported in the paper. Token totals include main-agent and worker usage. Cost figures use the paper's API price snapshot. Workflow calls per task include zero-call tasks unless the caption explicitly conditions on nonempty tasks; workers per Workflow uses launched Workflows as the denominator.

## Figure 3

Resolved rate versus mean tokens per task; input, output and cached input include main agents and workers.

![Resolved rate versus mean tokens per task; input, output and cached input include main agents and workers.](../../docs/assets/resolved-vs-tokens.png)

## Figure 4

Resolved rate versus estimated mean inference cost per task, using the paper's pricing snapshot.

![Resolved rate versus estimated mean inference cost per task, using the paper's pricing snapshot.](../../docs/assets/resolved-vs-cost.png)

## Figure 5

Workflow invocation frequency and worker invocations per Workflow at high effort.

![Workflow invocation frequency and worker invocations per Workflow at high effort.](../../docs/assets/workflow-and-workers.png)

## Figure 6

Delegation frequency and size distributions, conditioned on nonempty tasks and Workflows.

![Delegation frequency and size distributions, conditioned on nonempty tasks and Workflows.](../../docs/assets/workflow-distributions.png)

## Figure 7

Delegation across reasoning effort settings.

![Delegation across reasoning effort settings.](../../docs/assets/effort-profiles.png)

## Figure 8

Delegation across eight domains and nine models, at max effort except Doubao at high.

![Delegation across eight domains and nine models, at max effort except Doubao at high.](../../docs/assets/domain-workflows.png)

## Figure 10

Continuous score versus mean tokens per task.

![Continuous score versus mean tokens per task.](../../docs/assets/score-vs-tokens.png)

## Figure 11

Continuous score versus estimated mean inference cost per task.

![Continuous score versus estimated mean inference cost per task.](../../docs/assets/score-vs-cost.png)
