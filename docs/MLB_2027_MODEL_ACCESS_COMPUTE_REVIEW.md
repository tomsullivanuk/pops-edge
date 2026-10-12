# Model access and compute: read-only due diligence

October 12, 2026. Requested setup investigation completed; **no installation,
login, terms acceptance, account/key creation, weight download, spending or fit**.
The [modern-ML proposal](MLB_2027_MODERN_ML_PROPOSAL.md) remains unapproved.

## Decision

**TabPFN-3.5 is not presently cleared for this personal hobby project. Licensing
eligibility, not a demonstrated need to rent compute, is the first blocker.**
Seek explicit written permission if 3.5 is the desired version, or discuss an
explicitly different v2 comparison. Keep a local CPU boosting baseline as the
lowest-friction compute route after its bounded experiment/setup is approved.
Do not acquire GPU capacity first or silently substitute versions.

## Actual terms and access

The [3.5 weight license](https://huggingface.co/Prior-Labs/tabpfn_3_5/raw/main/LICENSE)
is v1.0, revised September 9. It expressly says the license is unavailable to
consumers and requires professional status. It also restricts production and
revenue-related use, including outputs. Therefore personal research eligibility
is not established merely by calling the project noncommercial. Later using
predictions for personal wagers needs explicit clarification; no categorical
permission follows from the free evaluation description. Download/access/use
itself binds the license, so no weights were downloaded.

The [service terms](https://priorlabs.ai/general-terms-and-conditions), dated
June 23, 2026, also limit customers to businesses; the
[AUP](https://priorlabs.ai/aup) excludes consumers. Account registration forms a
contract. Thus the hosted API is not an established workaround for an individual
hobbyist. Service terms additionally grant model-improvement use of uploaded
content unless opted out, and require sufficient content rights. No API upload,
account or opt-out change was attempted; licensed data stays private/local.

The [pricing page](https://priorlabs.ai/pricing) advertises limited free evaluation
and free API tiers, but does not establish hobbyist eligibility. Paid production
license/API plans are contact-sales, with no verified public numeric quote for
this use. A legal exception/price remains unknown, not assumed free or expensive.

The [v2 classifier license](https://huggingface.co/Prior-Labs/TabPFN-v2-clf/raw/main/LICENSE.txt)
is Prior Labs License v1.1 (May 2025), based on Apache 2.0 plus attribution.
It includes individuals and contains no analogous consumer/production/revenue
prohibition in the inspected text. Public distribution triggers its license,
notice and branding obligations; publishing a reusable model can create further
naming obligations. This appears a substantially more suitable **standalone-local**
route, subject to the complete dependencies/terms and approved setup. It is an
older checkpoint, not the latest 3.5, and has not been adopted as a fallback.

Current [official README](https://github.com/PriorLabs/TabPFN) documents login and
license acceptance for recent releases. Public Hugging Face metadata for 3.5 and
v2 currently says `gated: false`; the 3.5 card nevertheless describes a license
access request. Technical file visibility is not a grant of rights. Inspected
loader code explicitly treats v2 as the version with a direct-download option;
this was read, not executed. No token or model cache was searched for or altered.

## Provenance and contamination

The [3.5 model card](https://huggingface.co/Prior-Labs/tabpfn_3_5/blob/main/README.md)
declares training solely on synthetic tables. That materially reduces the specific
concern that pretraining memorized actual baseball results, but is the developer's
statement, not our independent training-corpus audit. Benchmark/prior tuning is
still external selection; our reused 2024–2026 seasons remain development. Freeze
the exact model/package/checkpoint before any fresh 2027 confirmation.

Metadata-only candidate pins inspected, without downloading binaries:

| Candidate | Public repository revision | Default checkpoint size |
|---|---|---:|
| 3.5 core | `06bf2ba35c80a92a3b9abb436b99cf49e7a0365e` | 876,027,932 bytes |
| v2 classifier | `f851f2a3c941544733b712d8c0f96dfae9b28862` | 29,009,539 bytes |

3.5 core filename is `tabpfn-v3.5-20260909.safetensors`; v2 default is
`tabpfn-v2-classifier-v2_default.ckpt`. Repository revision/file size is not a
verified local weight checksum. Actual checkpoint hashes must be checked only
after authorized acquisition. Plus/Thinking are distinct proprietary variants. A v2 alternative requires its own pretraining/model-card check; do not transfer the 3.5 synthetic-only statement to another checkpoint.

## Hardware/software actually checked

Read-only local hardware, architecture, memory, GPU/Metal and disk inspection
was completed. Exact machine details and a sanitized receipt remain private,
not in the public repository. Default and retained modeling Python are 3.14.5;
torch, tabpfn and catboost are absent in both inspected environments. The retained
NumPy/sklearn reference environment remains unchanged. No executable MPS test
was possible without installing PyTorch; Metal hardware support is not a
successful `torch.backends.mps.is_available()` or an inference-capacity result.

Public PyPI metadata verified potential matching wheels (metadata only):

| Package | Inspected version | Matching distribution |
|---|---|---|
| PyTorch | 2.14.1 | CPython 3.14, macOS 14+, arm64 |
| TabPFN | 9.1.0 | Python >=3.10, pure-Python wheel; requires torch >=2.5 |
| CatBoost | 1.2.10 | CPython 3.14 macOS 11+ universal2 |

Sources: [torch metadata](https://pypi.org/pypi/torch/2.14.1/json),
[TabPFN metadata](https://pypi.org/pypi/tabpfn/9.1.0/json),
[CatBoost metadata](https://pypi.org/pypi/catboost/1.2.10/json).
Matching tags/declared dependencies establish plausible installation compatibility,
not successful runtime ABI/kernel tests. A later approved isolated environment
should preserve the old modeling environment and pin resolved dependencies.

[CatBoost documentation](https://catboost.ai/docs/en/installation/python-installation-method-pip-install)
supports macOS arm64 **CPU**, with no macOS CUDA GPU support. Apple's GPU is not
an NVIDIA CUDA device. The roughly 9,704 × 10 largest table is small for a bounded
CPU tree baseline; feasible local fitting is an engineering assessment, not a
measured runtime guarantee. No need for GPU purchase to establish that baseline.

[PyTorch MPS](https://docs.pytorch.org/docs/2.14/notes/mps.html) and the TabPFN
README support Apple-Silicon acceleration. TabPFN recommends recent PyTorch for
that route. CPU defaults limit 3.5 to 5,000 training rows and older models to
1,000; the 7,278/9,704 annual folds exceed those defaults. Documented CPU override
does not establish affordable full-fold runtime. Do not truncate the dataset
silently to fit. Local shared-memory MPS is worth checking after rights/setup
approval, but full cache/activation memory and timing are unmeasured.

If later approved: test installation and MPS availability first; then one
synthetic, non-baseball capacity rehearsal of the actual 9,704 × 10 context and
representative prediction batches, with fixed memory/time ceilings. This checks
feasibility without inspecting baseball evaluation outcomes. It still involves
model use and must wait for license/setup authority. Only then run approved fits.

## Compute alternatives and verified current prices

No callable read-only GPU-provider allocation/account inventory is exposed in
this task. No saved cloud allocation, credit or authenticated instance was
verified. This is not evidence that the Owner owns none. No cloud configuration
was read from credential files, and no service was started.

| Route | Verified marginal price/status | Practical assessment |
|---|---|---|
| Existing local CPU | No rental cost; packages not installed | Prefer for CatBoost and reference; inference timing still to measure |
| Existing local MPS | No rental cost; runtime absent/unverified | Prefer a bounded capacity check after model rights are cleared |
| Lambda single A6000, 48 GB | Public list $1.09/GPU-hour, plus applicable tax | Possible controlled CUDA fallback; actual inventory/account access unknown |
| Lambda single A10, 24 GB | Public list $1.29/GPU-hour, plus applicable tax | Another published capacity tier; benchmark memory before selecting |
| Runpod RTX A5000, 24 GB | Public table $0.27/hour | Advertised rate only; cloud tier/region and actual availability not authenticated |
| PriorLabs API/Plus/Thinking | Free limited tier advertised; larger plans contact sales | Business-only eligibility and data-content rights make this unsuitable as an assumed fallback |

Sources checked October 12: [Lambda single-instance table](https://lambda.ai/instances),
[Runpod pricing](https://www.runpod.io/pricing), [PriorLabs pricing](https://priorlabs.ai/pricing).
These are listed rates, not a reserved offer. As an explicit billed-time scenario,
two A6000 hours cost $2.18 and eight cost $8.72 before tax; two A5000 hours cost
$0.54 before storage/other charges. Those are arithmetic scenarios, **not predicted
experiment duration**. Setup time and retained storage can also be billable.
No full comparison has been timed, so no reliable total price can yet be quoted.

A rented GPU does not solve the model license. Any future cloud execution also
needs separate spending/account/terms authorization and confirmation that the
licensed derived feature table may be processed there. Do not upload raw provider
data or private credentials. Local evaluation is preferred while those rights
remain unestablished; no upload occurs under this review.

## Smallest next Owner actions

Choose either (a) pursue explicit 3.5 permission or (b) discuss a pinned v2 local
comparison. For (a), authorize a specific vendor inquiry or ask the vendor
directly; no message has been sent. The concrete question is whether an individual
personal hobbyist may evaluate 3.5 locally on retained private baseball data and
later use outputs for personal manual-wager decisions, despite consumer and
production/output restrictions, and what written license/price would cover both.
No misstatement of professional/business status is acceptable.

For (b), approve the version change and isolated setup/capacity check explicitly;
v2 remains a modern tabular foundation baseline but is not the latest model.
Neither choice automatically approves all baseball training, spending, cloud
upload, paper/live policy or trading. A specific bounded comparative protocol is
still required. No need to create accounts, accept terms or rent GPUs now.

This review corrects the earlier broad research-availability assumption: **3.5
eligibility is unresolved for the stated personal use.** PR #86 remains draft;
existing collectors, T−6h protocols, model artifacts and failed-result history
are unchanged.

## Licensing inquiry status — October 12 follow-up

The coordinating parent confirms that an Owner-approved inquiry was sent to the model vendor about personal baseball-performance analytics, private research/experimentation, the consumer exclusion, permission options and costs. This supersedes the earlier “no message has been sent” status for that specific inquiry only. The approved inquiry scope is narrow; it does not establish permission for broader product uses. Personal correspondence identifiers and account details remain private.

Vendor permission remains pending. No terms acceptance, login, installation, model download, training, spending or v2 substitution is approved. The parent owns receipt/review of the response; this task will not send a duplicate or broaden the inquiry. Any response must be recorded with its actual scope before treating access as cleared.
