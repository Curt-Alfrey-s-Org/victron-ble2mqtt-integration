# From-scratch trainer plan

Spec for a new trainer in the **alfa-ai** repo. This file lives in
`victron-ble2mqtt-integration` because that is the only checkout this session
can write. Implementation belongs in alfa-ai at `train/from-scratch/`. Nothing
here runs on the Pi.

The alfa-ai tree was not readable from this session (`Curt-Alfrey-s-Org/alfa-ai`
returns not found for this GitHub token). Reuse notes below name files from
cluster rules and from this repo. Open alfa-ai and copy the real helpers
instead of retyping them.

## Goal

Train a new language model from random initialization on the operator's git
repos. Keep all four GPUs in the job: 2× RTX 5070 and 2× RTX 3060. The 3060s
set the step time. That is accepted.

Compute stays **bfloat16**. A friend can join over the internet as a second
island that syncs on an outer clock, not on every step. The same outer-clock
idea, plus packing and the Blackwell wheel, should be ported onto the existing
7B QLoRA trainer.

## Hardware and precision

| GPU | Arch | Capability | Role |
|---|---|---|---|
| RTX 5070 ×2 | Blackwell | sm_120, 12 GB | Fast ranks in the local island |
| RTX 3060 ×2 | Ampere | sm_86, 12 GB | Same data-parallel step, slower |

One **local island**: NCCL data parallel across the four cards on the LAN.
Step time equals the slower 3060. DiLoCo's own writeup says devices inside one
island should be homogeneous, and that different islands may be different
hardware ([DiLoCo](https://arxiv.org/html/2311.08105v3)). These four cards are
one island anyway, because the operator wants the 3060s in the same step.

**bfloat16, not fp8.** The NanoGPT speedrun's latest records use FP8 for the
MLP and the output head on H100s ([modded-nanogpt](https://github.com/KellerJordan/modded-nanogpt)).
Ampere tensor cores on the 3060 do not run FP8. A kernel that only the 5070
can execute will not run in a joint step. bf16 works on both. fp16 needs loss
scaling and a narrower range; use it only if a bf16 matmul fails on a given
wheel.

**Wheel.** PyTorch built with CUDA 12.8 or newer. Those builds are the ones
that contain sm_120 kernels; CUDA 12.1 and 12.4 wheels do not
([PyTorch forum](https://discuss.pytorch.org/t/nvidia-geforce-rtx-5070-ti-with-cuda-capability-sm-120/221509)).
Before any training run, do a bf16 matmul on one 5070 and one 3060 with the
same install. Windows 5070 hosts have shipped broken wheels before (partial
2.7, missing embedding kernels in early cu128 nightlies). Verify the op, do
not trust `torch.cuda.is_available()`.

**Attention.** `scaled_dot_product_attention` in that PyTorch build. FlashAttention-3
kernels are Hopper (sm_90); Karpathy's nanochat falls back to SDPA on
Blackwell ([nanochat flash_attention.py](https://github.com/karpathy/nanochat/blob/0aaca568/nanochat/flash_attention.py)).
Building FlashAttention-2 for sm_120 was segfaulting nvcc as of March 2026
([flash-attention #2361](https://github.com/Dao-AILab/flash-attention/issues/2361)).
SDPA is the kernel that exists on both cards.

## Model

About **410M** parameters so AdamW states fit in 12 GB with activation
checkpointing off, unless a smoke test OOMs.

- 24 layers, hidden 1024, 16 heads, sequence 2048, vocab 32768
- Rotary embeddings, QK-norm, ReLU² activations
- Those three are the architecture half of the speedrun, separate from the
  FP8 half ([modded-nanogpt README](https://github.com/KellerJordan/modded-nanogpt/blob/master/README.md))
- Tie embeddings and the output head at the start. Untie later only if a
  held-out loss curve says it helps. The speedrun unties at two thirds of
  training; that schedule was tuned for FineWeb on 8×H100, so it is a flag,
  not the default.

**Inner optimizer, two stages.**

1. Ship **AdamW** in bf16 first. That is the inner optimizer DiLoCo measured.
2. Then turn on **Muon** for the 2D hidden matrices, and keep AdamW for
   embeddings, the output head, and 1D parameters. Newton–Schulz runs in
   bf16. On the speedrun's FineWeb setup, Muon is described as about 1.5×
   better sample efficiency, under 2% wall-clock overhead, and less memory
   than Adam ([modded-nanogpt Muon section](https://github.com/KellerJordan/modded-nanogpt/blob/master/README.md),
   [writeup](https://kellerjordan.github.io/posts/muon/)). Those figures are
   their benchmark, not a measurement on 5070s. Treat them as the reason to
   try Muon, then confirm on a short A/B here.

Do not start from the speedrun's full record script. It assumes 8×H100, FP8,
and FlashAttention-3. Copy the bf16 Muon update and the architecture pieces.
Leave the rest.

## Corpus

Train on the current tree of every repo listed in alfa-ai
`docs/REPO_HOST_MAPPING.md`. Known siblings include alfa-ai,
victron-ble2mqtt-integration, monitoring, market-pie5-bot, ATEMS, and
alfa-homelab. The mapping file is the list. Do not hardcode it in the trainer.

Pack source, scripts, Markdown, YAML, and JSON. Skip binaries, wheels,
`node_modules`, `.git`, and lockfiles that dwarf the code.

**Secrets.** Reuse the denylist already written in
[SECURITY_REMOVE_SECRETS.md](../../SECURITY_REMOVE_SECRETS.md): `.env`,
`*.env`, TLS keys, tokens, `user_settings.py` when it contains credentials.
Scan the packed text again before it becomes a shard. Train on the **current
tree**, not full git history, so deleted credentials are not the default
corpus. A history pass is a separate, explicit job after a purge.

**Tokenizer.** Train a SentencePiece BPE (32k) on that filtered text. The
model is randomly initialized, so the vocab should match this code. If the
packed corpus is too small for a stable vocab, fall back to a public code
tokenizer and record that choice in the run config.

**Data size.** A few private repos will not behave like FineWeb. The model
will be a specialist in this codebase. If held-out loss flattens early, the
next lever is more of the operator's own text (docs, issues, scripts), not a
larger model. Mixing a public code corpus is a later decision and only for
code whose license allows training.

Shards and checkpoints go on the TrueNAS hub layout already documented in
alfa-ai `docs/HUB_ARTIFACTS.md` and `docs/CLUSTER_SHARED_STORAGE.md`.

## Speed techniques that stay at bf16

Ranked by what to implement. Gains below are the authors' claims for their
hardware. Re-measure tokens/sec on one 5070 and one 3060 before trusting them.

| Order | Technique | Why it is in this plan |
|---|---|---|
| 1 | bf16 autocast, no GradScaler | Right dtype for Ampere and Blackwell together ([torch.amp](https://docs.pytorch.org/docs/2.13/amp.html)) |
| 2 | SDPA | Only attention path that is real on both sm_86 and sm_120 today |
| 3 | `torch.compile` | Standard win on the speedrun. First call is slow (they note about 7 minutes on their stack). Compile once per machine. |
| 4 | Document packing | Concatenate files with an EOS between them so a 2048 window is full. The speedrun also aligns batch starts to EOS. Windows that cross files without EOS teach the model that one repo continues into the next. |
| 5 | Muon on 2D weights | Sample efficiency on their benchmark, bf16 Newton–Schulz, less optimizer state than Adam on those matrices |
| 6 | bf16 activations | Speedrun record 10. Do this with the autocast, not a second dtype. |
| 7 | DDP, equal microbatch | User asked to keep the 3060s in the step. Uneven batches are a later option if the 5070s sit idle inside the step and a profile shows it. |
| 8 | Activation checkpointing | Only if a 12 GB card OOMs. It trades speed for memory. |
| 9 | bf16 cross-entropy | Speedrun record 37. Flag, default off, until loss is stable in fp32 CE. |

Skip for this cluster:

- FP8 MLP, FP8 head, FP4
- FlashAttention-3, and a from-source FlashAttention-2 build for sm_120
- NCCL `torchrun` between the house and the friend
- DeepSpeed ZeRO for the 410M run. Optimizer state fits. ZeRO pays for itself if the model grows toward 1B and a 12 GB card OOMs.

`torch.compile` and SDPA also apply to the 7B trainer. Muon does not, until
someone measures it on LoRA adapters. The speedrun result is for full
matrices trained from scratch.

## Continued learning

Train from scratch once. After that, keep training when repos change. Do not
restart from random weights for each new commit.

What is working in 2025–2026 for continual pretraining is **replay of old
data**, not a new optimizer. Abbes et al. (CoLLAs 2025) trained Llama-family
models with a replay buffer plus a cheap Reptile/MER interpolation and found
that a **small** replay rate beats a high replay rate, and that a little
replay is a better use of compute than growing the model to fight forgetting
([paper](https://arxiv.org/abs/2508.01908),
[chandar-lab/continual-pretraining](https://github.com/chandar-lab/continual-pretraining)).
Secondary writeups of other CPT runs put a practical mix around 10–30% old
tokens ([survey notes](https://www.emergentmind.com/topics/continual-pretraining-cp)).
Use the paper's result: start small, measure, raise replay only if a frozen
repo gets worse.

Day to day:

1. Pack new and changed files into a "current" shard.
2. Keep a disk replay buffer of older packed shards (one snapshot per repo per
   week is enough).
3. Each batch is mostly current text plus a small draw from the buffer.
4. Every k steps, optional Reptile interpolate toward the weights from k
   steps ago. The chandar-lab hook is the reference. Skip it until plain
   replay is measured. It is cheap, and it is still the second knob.
5. Log three numbers from their repo: learned loss (current shard), retained
   loss (frozen replay validation), forgetting (retained loss now minus
   retained loss when that shard was first learned).

EWC, progressive networks, and activation-matching replay (GeRe) are for
later. GeRe targets continual **fine-tunes** with a fixed general replay set
([GeRe](https://github.com/Qznan/GeRe)). Useful for the 7B trainer if
adapter runs start wiping earlier tasks. Not the first from-scratch loop.

## Friend over the internet

Two islands.

- **House island:** the four local GPUs. Inner step is NCCL DDP. Data is the
  operator's repos. Data does not leave the house.
- **Friend island:** their GPUs, their data, their copy of the **model**.
  They never receive the repo files.

Sync on an **outer clock**, which is the timing the operator asked for.

DiLoCo ([Douillard et al.](https://arxiv.org/html/2311.08105v3)):

- Copy the shared weights to each island.
- Each island runs H inner steps on its own data. H starts at **500**, the
  period OpenDiLoCo published (about 67 minutes between syncs on their
  1.1B / 8×H100 run, which will be a different wall time here)
  ([OpenDiLoCo](https://www.primeintellect.ai/blog/opendiloco)).
- Pseudo-gradient is the parameter delta across those H steps.
- Average the deltas. Outer optimizer is **Nesterov momentum**. That is the
  outer optimizer the paper found best. Plain averaging is FedAvg, and they
  showed it is weaker.
- Broadcast the new weights. Repeat.

OpenDiLoCo ran this across countries on Hivemind's DHT all-reduce, with FSDP
inside a worker, pseudo-gradients reduced in FP16, and 90–95% compute
utilization on links of roughly 127–935 Mbit/s. Inner compute stayed on the
GPUs the whole time because the sync is rare.
[prime](https://github.com/PrimeIntellect-ai/prime-diloco) (the follow-on)
adds `ElasticDeviceMesh`: heartbeats, a node can leave without killing the
job, and a VPN path when public port-forward bandwidth is unstable. They
shard the pseudo-gradient so several connections share the uplink.

**Timing.** The outer round id is the clock. Islands do not barrier every
microbatch. If the friend is late, wait for a timeout, then let the house
continue and let the friend catch the next broadcast. prime's heartbeat is
the pattern. A 3060 that is merely slower does not trip this. It is inside
the house island, and the house step already waits for it.

**Transport.** Tailscale between the two sites, same idea as
[docs/TAILSCALE.md](../../docs/TAILSCALE.md): a private path, no training port
on the public internet. Outer all-reduce goes over that path with Hivemind
(or Gloo if a first prototype has only two islands). NCCL stays on the LAN
inside each island. NCCL across WAN is the wrong tool: it expects a low-latency
fabric, and a missed timeout takes down the job.

**What crosses the wire.** For the 410M model, the pseudo-gradient (bf16
compute, fp16 on the wire if that matches OpenDiLoCo's reduction). On the
order of a gigabyte per outer round, not per step. For the 7B trainer, do
**not** ship the full 7B delta. Ship **LoRA adapter** deltas only. Federated
LoRA keeps the frozen base local and averages adapters
([FedAvg-style LoRA pattern](https://www.spheron.network/blog/federated-learning-gpu-cloud/);
Dec-LoRA is the decentralized variant,
[arxiv 2501.15361](https://arxiv.org/html/2501.15361v1)). A small reference
for "DiLoCo, but the averaged tensor is the adapter" is the MoreGPU example
[lora_distributed.py](https://github.com/ArioMoniri/moregpu/blob/main/examples/lora_distributed.py).
Copy the schedule (H inner AdamW steps, outer Nesterov, average adapters).
Do not take that repo as a dependency.

**Privacy.** Each worker holds the weights. A model trained on private code
can memorize a secret that passed the filter, and the friend has the
weights. The corpus filter runs before the first outer round, not after.
Pseudo-gradients can also leak training text. The friend brings their own
data. They do not get a shard of the operator's repos, and the operator does
not get a shard of theirs.

**Petals.** If alfa-ai already vendors Hivemind for Petals, reuse that
library for the outer all-reduce. Petals itself is an inference pipeline.
Do not send training steps through Petals servers. The Pi stays off both
paths.

## What to copy, and what to leave

Copy behavior, not a second trainer.

| Already exists | Use it for |
|---|---|
| alfa-ai `docs/REPO_HOST_MAPPING.md` | Which repos enter the corpus |
| alfa-ai `docs/NODE_INVENTORY.md` | Which host has the 5070s and which has the 3060s. Discover with `nvidia-smi` and record it. Do not guess in the launcher. |
| alfa-ai `docs/HUB_ARTIFACTS.md`, `docs/CLUSTER_SHARED_STORAGE.md` | Shard and checkpoint paths on `.111` |
| alfa-ai `Start-AlfaTrain7bQlora.ps1` and the Trainer GUI | How a job is started, logged, and pointed at a host. The new pretrain gets its own launcher beside this one. |
| alfa-ai Petals/Hivemind dependency, if present | Outer-island all-reduce only |
| This repo `SECURITY_REMOVE_SECRETS.md` | Denylist for the corpus scanner |
| [modded-nanogpt](https://github.com/KellerJordan/modded-nanogpt) Muon + RoPE + QK-norm | bf16 from-scratch loop. Pin a commit. Do not vendor the FP8 record. |
| [prime-diloco](https://github.com/PrimeIntellect-ai/prime-diloco) / OpenDiLoCo | Outer clock, elastic membership, sharded delta. Read it. A first version can be a few hundred lines for exactly two islands. |

Leave the 7B QLoRA loop inside its current script. Call shared pieces
(packing, wheel check, outer sync of adapters) from both.

## 7B fine-tune

A 7B in bf16 is about 14 GB of weights before optimizer state. It does not
fit in 12 GB. The 7B job stays **QLoRA**: 4-bit frozen base, **bf16**
adapters. "16-bit" for that trainer means the adapter math and the SDPA
dtype, not a bf16 copy of the base model.

Changes worth making in `Start-AlfaTrain7bQlora.ps1` / the GUI, after the
from-scratch smoke test proves the wheel:

1. Same cu128 (or newer) PyTorch, with the matmul check on a 5070 and a 3060.
2. SDPA, if the script still asks for a FlashAttention wheel that has no
   sm_120 build.
3. Pack short instruction examples so a step is not padding.
4. DDP with a full 4-bit replica on each GPU, including the 3060s. The step
   waits for the 3060. Device-map splitting is the fallback if one card OOMs.
5. Friend sync: outer Nesterov on adapter deltas every H inner steps, over
   Tailscale. The base weights stay where they were loaded.
6. If a later QLoRA run forgets an earlier task, add a small replay of the
   old instruction set (GeRe's idea: a fixed replay mix). Measure retained
   loss the same way as the from-scratch run.

Muon stays off the 7B path until the from-scratch A/B says it is worth a
separate experiment on adapters.

## Build order

Implement in alfa-ai, in this order. Each step is runnable on its own.

1. **Corpus tool.** Read the repo map, filter secrets, train the tokenizer,
   write packed shards to the hub. No GPU required.
2. **Wheel check.** bf16 matmul on one 5070 and one 3060.
3. **Single-island trainer.** 410M, AdamW, bf16, SDPA, compile, packing, DDP
   on all four GPUs. Checkpoint to the hub.
4. **Muon flag.** A/B a few hundred steps against AdamW. Keep the winner.
5. **Replay.** Current shard plus a small replay buffer. Log learned,
   retained, and forgetting loss per repo.
6. **Second island.** Two-worker DiLoCo over Tailscale. House data stays
   home. Friend data stays with the friend. H = 500. Outer Nesterov.
   Timeout so a missing friend does not stop the house.
7. **7B port.** Wheel check, SDPA, packing, and adapter outer-sync in the
   existing QLoRA launcher.

## Non-goals

- Training this model on the Pi, or joining the Pi to Petals.
- FP8 or FP4 on the mixed 5070 + 3060 island.
- Replacing the 7B QLoRA trainer with the from-scratch loop.
- Sending private repos, `.env` files, or raw checkpoints of a secret-trained
  model to the friend before the corpus filter has run.
- A public, open DHT membership for the outer sync. Two named Tailscale
  peers are the first version.

## Sources

- DiLoCo: https://arxiv.org/html/2311.08105v3
- OpenDiLoCo: https://www.primeintellect.ai/blog/opendiloco
- prime (ElasticDeviceMesh): https://github.com/PrimeIntellect-ai/prime-diloco
- modded-nanogpt (bf16 Muon, RoPE, QK-norm; FP8 records are out of scope): https://github.com/KellerJordan/modded-nanogpt
- Muon writeup: https://kellerjordan.github.io/posts/muon/
- SDPA on non-Hopper, including Blackwell: https://github.com/karpathy/nanochat/blob/0aaca568/nanochat/flash_attention.py
- FlashAttention-2 sm_120 build failure: https://github.com/Dao-AILab/flash-attention/issues/2361
- PyTorch cu128 and sm_120: https://discuss.pytorch.org/t/nvidia-geforce-rtx-5070-ti-with-cuda-capability-sm-120/221509
- torch.amp bf16 vs fp16: https://docs.pytorch.org/docs/2.13/amp.html
- Continual pretraining replay: https://arxiv.org/abs/2508.01908
- Replay implementation: https://github.com/chandar-lab/continual-pretraining
- Dec-LoRA: https://arxiv.org/html/2501.15361v1
- Adapter-only DiLoCo sketch: https://github.com/ArioMoniri/moregpu/blob/main/examples/lora_distributed.py
