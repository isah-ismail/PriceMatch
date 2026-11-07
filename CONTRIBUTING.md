# Contributing

Status: proposed Week 1 conventions for team review. Existing repository settings are not changed by this document.

## Branches and commits

Keep main as the integration branch. Use short-lived topic branches:
- docs/<issue>-<topic>
- test/<issue>-<topic>
- fix/<issue>-<topic>
- feat/<issue>-<topic>

Omit the issue number if none exists. The Week 1 upstream review branch is docs/week1-integration-final. Agent-created branches ordinarily use codex/<topic> unless an explicit branch name is requested.

Use clear commit and PR titles such as `docs: document Week 1 integration contracts`. Keep one focused purpose per PR.

## Pull requests

Use draft PRs while work is incomplete. Explain purpose, scope, validation, dependencies, open decisions and operational impact where relevant. Link existing issues; do not invent issue references.

Proposed merge requirements: one reviewer, resolved discussions and applicable checks. Prefer squash merging and deleting the topic branch after an approved merge. Branch protection and required checks must be configured separately by maintainers; this document does not imply they are active.

Do not edit migrations already applied to a database. Propose a new numbered migration in a separate implementation PR. Preserve component documentation and discuss contract changes with its owners.

## Reviewing the Week 1 fork branch

1. Compare the fork branch against the original repository's main.
2. Confirm the head is ayseozmen:docs/week1-integration-final.
3. Inspect the diff for the root README and eight documentation/template files.
4. Open the rendered Markdown files to check links and Mermaid diagrams.
5. Review open integration decisions with the relevant teams. Record setup evidence if commands are executed.
6. Leave comments or request changes before approving. Do not merge without the user's explicit approval.

## Submitting to the original team repository later

Original parent verified from GitHub metadata: [isah-ismail/PriceMatch](https://github.com/isah-ismail/PriceMatch).
Fork: [ayseozmen/PriceMatch](https://github.com/ayseozmen/PriceMatch).

After review and authorization to submit upstream:
1. On the original repository, choose Pull requests, New pull request, then compare across forks.
2. Select base repository isah-ismail/PriceMatch and base branch main (confirm the team's intended target).
3. Select head repository ayseozmen/PriceMatch and compare branch docs/week1-integration-final.
4. Inspect the complete diff against the current upstream base. If unrelated changes or conflicts appear, reconcile them on the fork branch and review again.
5. Describe the reviewed changes, noting this is documentation only and listing unresolved decisions.
6. Create the upstream PR and request team review. Opening a PR does not merge the changes.

The final branch starts at the reviewed upstream commit. You can submit it directly from the fork. The fork branch must remain available until upstream review is complete.
