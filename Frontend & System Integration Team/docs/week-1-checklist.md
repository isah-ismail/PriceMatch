# Week 1 integration deliverables

Status: documentation prepared for review on 2026-11-08. No authoritative course Week 1 rubric was found in the reviewed repository; reconcile this list with the team's actual requirements.

| Deliverable | Current evidence | Remaining acceptance work | Suggested reviewer |
|---|---|---|---|
| Repository baseline | main at 202b03a inspected | Confirm scope and review findings | Team |
| Architecture and data flow | Mermaid drafts in architecture.md | Agree boundaries and responsibilities | All component teams |
| README navigation | Team overview and component links | Review accuracy and preserve original description | Team |
| Integration contract | Candidate mapping and INT-01 through INT-12 | Resolve decisions with relevant owners | Data, matching, database/backend |
| Local setup | Platform-aware guide | Execute on clean environment and record results | Integration + teammate |
| Branch and PR conventions | CONTRIBUTING.md and PR template | Team adoption; settings remain unchanged | Maintainers |
| Test strategy | Existing backend tests plus a cross-team matrix and fixture catalogue | Assign owners and approve expected outcomes | Component owners, integration |
| Deployment plan | Decisions and future release checklist | Choose environment and operational owners | Team |
| Work tracking | This checklist | Create/assign issues only when authorized | Team |

## Review gates

- [ ] Existing versus proposed functionality is accurate.
- [ ] Team documentation, code, CSVs and existing migrations remain unchanged.
- [ ] The Mermaid flow, sequence and ER diagrams render in GitHub.
- [ ] Links and commands use the actual repository layout.
- [ ] Open decisions have reviewers and are not presented as adopted policy.
- [ ] Clean-environment setup evidence is attached.
- [ ] Fixture and test expectations are accepted.
- [ ] Original team repository requirements are reconciled.
- [ ] Fork branch diff is reviewed before upstream submission.
- [ ] No merge occurs without explicit approval.

## Setup evidence template

- Reviewer and date:
- OS:
- Python / PostgreSQL versions:
- Commit:
- Commands executed:
- Expected and actual results:
- Failures or limitations:
- Follow-up issue links:

## Validation of this documentation change

Static review covers changed-file scope, preserved original README description, relative links and consistency with the baseline. Runtime setup, database tests, live scrapers and deployment are not executed by this documentation change. GitHub diagram rendering remains a reviewer check.

## Fork and upstream

Working repository: ayseozmen/PriceMatch.
Original parent: isah-ismail/PriceMatch.
Branch: docs/week1-integration-final.

The final fork branch starts at the reviewed upstream main commit. Compare it directly against the original repository before opening an upstream PR. See CONTRIBUTING.md for the submission steps.
