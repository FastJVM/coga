# macOS install-test costs (2026-10-06)

Point-in-time comparison behind the path choice in
[`coga/testing/clean-install/macos-owned`](../contexts/coga/testing/clean-install/macos-owned/SKILL.md#cost-and-choosing-a-path).
Prices, plan terms and runner images change. Recheck the sources before
reusing a number, and before asking for approval to spend.

## Rates checked on 2026-10-06

| Path | Rate | Minimum or plan | Source |
|---|---|---|---|
| Owned Apple silicon Mac, Tart VM | none per run | Tart is free for personal use and for organizations up to 100 host CPU cores | [tart.run/licensing](https://tart.run/licensing/) |
| Owned Intel Mac, attached | none per run | — | — |
| AWS EC2 Mac `mac2` (M1) host, us-east-1 | USD 0.65/hour | 24-hour minimum allocation: USD 15.60 per host | AWS public price list `dedicatedhost-ondemand` (published 2026-09-25); [EC2 Mac FAQ](https://aws.amazon.com/ec2/instance-types/mac/faqs/) |
| AWS EC2 Mac `mac1` (Intel) host, us-east-1 | USD 1.083/hour | 24-hour minimum: USD 25.99 | same price list |
| GitHub Actions standard macOS (3–4 core, M1 or Intel) | USD 0.062/minute | free for public repositories; FastJVM/coga is public | [runner pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing), [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) |
| Buildkite hosted macOS, M4 Medium (6 vCPU) | USD 0.12/minute | Pro plan, USD 30 per active user per month; the Free plan has no macOS | [buildkite.com/pricing](https://buildkite.com/pricing/) |

The 2026-10-01 figures in the requesting ticket (mac2 USD 0.65/hour, GitHub
USD 0.062/minute, Buildkite M4 Medium USD 0.12/minute) still held.

## What each path can reproduce

| | Owned Apple silicon VM | Owned Intel Mac | EC2 Mac | GitHub Actions | Buildkite hosted |
|---|---|---|---|---|---|
| Missing Command Line Tools (CLT) at first `git` | Yes: the vanilla image has no CLT, and nothing is removed | No: whatever the Mac already has | Yes, after the harness removes the AMI's CLT | Not as shipped: Xcode and Homebrew are preinstalled. Removing them on the ephemeral VM gives only the headless shim error | Not as shipped: Xcode and Homebrew are preinstalled |
| CLT install dialog (GUI) | Yes, over VNC | — | Yes, over VNC | No | Possibly, through desktop access; untested |
| Intel (x86_64) | No | Yes | Only `mac1`, at USD 25.99 minimum | Yes: `macos-15-intel`, `macos-26-intel` | No: Apple silicon only |
| Interactive agent login and first ticket | Yes (SSH) | Yes (SSH) | Yes (SSH) | No built-in access | Terminal and desktop access |
| Fresh machine per run | Yes (clone, delete) | No: a fresh user only | Yes, but each host costs at least a day | Yes | Yes |
| Admin rights | passwordless sudo | the test account's sudo | passwordless sudo | passwordless sudo | not documented |

GitHub's runner labels and sudo statement come from its
[GitHub-hosted runners reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
Buildkite's architecture, preinstalled software and access features come from
its [macOS hosted agents](https://buildkite.com/docs/pipelines/hosted-agents/mac)
page. The vanilla image's contents (no added software, `admin`/`admin`,
passwordless sudo) come from the Packer templates in
[cirruslabs/macos-image-templates](https://github.com/cirruslabs/macos-image-templates).

## Recommendation

1. **Default to the owned Apple silicon VM** for fresh-install evidence: the
   missing-CLT first run, PyPI and `main` wheel walks, and attended agent
   login and first ticket. Each run costs nothing extra and starts from a
   clean clone.
2. **Use the owned Intel Mac for x86_64 compatibility only.** It cannot show
   a fresh install.
3. **Keep EC2 Mac optional**, for when the owned Macs are unavailable. Each
   use costs at least USD 15.60 and needs spend approval.
4. **Hosted CI suits only the automated, non-interactive part**: install the
   PyPI artifact and the `main` wheel, then run `coga init` and
   `coga validate` on `macos-latest` and an Intel label. That check covers
   compatibility with a preinstalled-Xcode machine, not a new user's
   experience. GitHub Actions fits better than Buildkite: it is free for this
   public repository, offers Intel, and needs no plan fee. Buildkite adds
   desktop access, which the owned VM already gives at no cost.

Adding that workflow would change the repository's no-CI posture
([coga/testing](../contexts/coga/testing/SKILL.md#ci-posture-and-receipts)).
It needs an explicit owner decision and is not part of this comparison.
