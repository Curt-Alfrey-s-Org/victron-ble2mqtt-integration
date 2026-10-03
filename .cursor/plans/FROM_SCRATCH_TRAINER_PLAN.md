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

**Wheel.** PyTorch **2.14** with the **cu130** wheel
(`pip install torch --index-url https://download.pytorch.org/whl/cu130`).
That stable line (2 September 2026) ships CUDA 13.0 by default, and the
CUDA 13.0 / 13.2 Linux and Windows x86 wheels include both Ampere sm_86 and
Blackwell sm_120 ([PyTorch RELEASE.md](https://github.com/pytorch/pytorch/blob/main/RELEASE.md),
[2.14 blog](https://pytorch.org/blog/pytorch-2-14-release-blog/)). CUDA 12.6
and older wheels stop at Hopper. sm_120 has been in stable wheels since
2.7 plus CUDA 12.8; cu130 is the pin so one install sees all four cards.
Before any training run, do a bf16 matmul on one 5070 and one 3060 with that
same install. Verify the op, do not trust `torch.cuda.is_available()`.

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
2. Then turn on **Muon** for the 2D hidden matrices, and keep **fused
   AdamW** (`fused=True`) for embeddings, the output head, and 1D
   parameters. Newton–Schulz runs in bf16. `torch.optim.Muon` is in PyTorch
   main; the 2.14 blog does not mention it, so import-check the wheel and
   fall back to the Keller implementation if the symbol is missing
   ([torch/optim/_muon.py](https://github.com/pytorch/pytorch/blob/main/torch/optim/_muon.py)).
   On the speedrun's FineWeb setup, Muon is described as about 1.5× better
   sample efficiency, under 2% wall-clock overhead, and less memory than
   Adam ([modded-nanogpt Muon section](https://github.com/KellerJordan/modded-nanogpt/blob/master/README.md),
   [writeup](https://kellerjordan.github.io/posts/muon/)). A 4× RTX A4000
   reproduction measured the synthetic step at 1.15× AdamW (slower), with
   the optimizer itself heavier and only a small slice of that fake step
   ([A4000 note](https://huggingface.co/blog/bird-of-paradise/reproducing-and-validating-distributed-muon)).
   The win to confirm here is tokens to a held-out loss, not a faster
   microstep.

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

**Tokenizer.** Use the tokenizer the 7B fine-tune already uses, or a
StarCoder-family code BPE if that 7B tokenizer is a poor fit for these
repos. Record the id in the run config. A SentencePiece model fit only to a
few private repos is sparse, and it cannot be loaded into the 7B. StarCoder2
trained a 49,152-token byte-level BPE on a large code corpus and found that
jumping to 100k did not help ([StarCoder2](https://arxiv.org/abs/2402.19173)).

**Packing.** Pack files from the same repo into a window. Dependency order
when the import graph is cheap; otherwise random order inside the repo.
DeepSeek-Coder applied fill-in-the-middle to about half of packed documents
for completion training ([DeepSeek-Coder](https://arxiv.org/abs/2401.14196)).
That is a flag, on by default if the job is completion, off if the job is
only next-token loss on whole files.

**Data size.** The corpus is these repos. That is the goal. It is also far
below the token budgets code models are trained with. Luo et al. fit code
scaling from 0.2B to 3.8B and, at one large budget, saw lower validation
loss near 150 tokens per parameter than at the natural-language ratio of
about 20, with the preferred ratio rising as compute grew
([arXiv 2510.08702](https://arxiv.org/abs/2510.08702)). A few private repos
cannot reach that. Repeating them for on the order of four epochs is the
useful limit: at fixed compute, about four epochs of repeated data barely
changes loss versus fresh data, and further repetition stops helping
([Muennighoff et al.](https://arxiv.org/abs/2305.16264)). Stop when held-out
perplexity flattens or rises.

A private-only run memorizes this codebase's APIs and style. It will not be
a general coder. If that specialist is not enough, mix in license-clean
public code in the languages these repos use, and upsample the private
snapshot so it still appears every epoch. There is no published
private-to-public ratio. Watch held-out private perplexity and one public
code benchmark together, and change the mix only if one moves the wrong way.
Train the mixture in one run. Walking repos one after another, with a fresh
learning-rate cycle each time, was worse than mixing them
([Ibrahim et al.](https://arxiv.org/abs/2403.08763)).

Shards and checkpoints go on the TrueNAS hub layout already documented in
alfa-ai `docs/HUB_ARTIFACTS.md` and `docs/CLUSTER_SHARED_STORAGE.md`.

## Speed techniques that stay at bf16

Ranked by what to implement. Gains below are the authors' claims for their
hardware. Re-measure tokens/sec on one 5070 and one 3060 before trusting them.

| Order | Technique | Why it is in this plan |
|---|---|---|
| 1 | bf16 autocast, no GradScaler | Right dtype for Ampere and Blackwell together ([torch.amp](https://docs.pytorch.org/docs/2.13/amp.html)) |
| 2 | SDPA | Only attention path that is real on both sm_86 and sm_120 today |
| 3 | `torch.compile` per block | Compile the block, not the whole DDP step. Compiling the full forward and backward stops DDP from overlapping allreduce with backward ([DDP notes](https://docs.pytorch.org/docs/stable/notes/ddp.md)). First call is slow (about 7 minutes on the speedrun). TorchTitan's measured gain on Llama 3.1 8B was about 7% on 8×H100 ([TorchTitan](https://arxiv.org/html/2410.06511v3)). |
| 4 | Document packing and EoS alignment | Concatenate files from the same repo with an EOS between them so a 2048 window is full. The ~2× packing number is for short, variable-length SFT (FLAN on 8×A100), not for an already-packed pretrain stream ([HF packing](https://huggingface.co/blog/packing-with-FA2)). |
| 5 | Muon on 2D weights, fused AdamW on the rest | Sample efficiency on the speedrun. Wall-clock can go the other way; measure both. |
| 6 | bf16 activations | Speedrun record 10. Do this with the autocast, not a second dtype. |
| 7 | DDP on all four GPUs | Default, so the 3060s stay in the from-scratch job. Before a long run, measure tokens/sec of the two 5070s alone against all four. If the 3060 gates the step so hard that the 5070 pair finishes more tokens per wall-clock second, move the 3060s to a second job (eval, or their own shard) for that run. Published DiLoCo also assumes the devices inside one island are homogeneous ([DiLoCo](https://arxiv.org/html/2311.08105v3)). |
| 8 | Selective activation checkpointing | Only if a 12 GB card OOMs. Full per-layer recompute costs about 30–40% step time ([Korthikanti et al.](https://proceedings.mlsys.org/paper_files/paper/2023/file/80083951326cf5b35e5100260d64ed81-Paper-mlsys2023.pdf)). Recompute pointwise ops first and keep the matmuls. |
| 9 | Cut cross-entropy, then bf16 CE | Do not materialize the full `[tokens, vocab]` logit tensor on 12 GB. Apple's cut cross-entropy is the memory win when vocab is large relative to hidden size ([CCE](https://machinelearning.apple.com/research/cut-your-losses)). bf16 CE (speedrun record 37) stays a flag until loss matches fp32 CE. |

Skip for this cluster:

- FP8, MXFP8, NVFP4, and Transformer Engine FP8 recipes. A mixed 5090+3090
  run already crashed because Triton emitted `tl.float8e4nv` and sm_86 cannot
  execute it ([club-3090 #762](https://github.com/noonghunna/club-3090/issues/762)).
- FlashAttention-3, stock `flash-attn` wheels, and Liger's CuTe DSL backend
  (`LIGER_KERNEL_IMPL=cutedsl` is SM90 / SM100 / SM110 only).
- CUDA graphs. The published Llama 405B speedup is an FP4 result, and the
  same note reports no speedup in FP8 because the GEMMs already hide launch
  overhead. Variable-length packing also fights fixed-shape graphs
  ([NVIDIA CUDA graphs](https://docs.nvidia.com/dl-cuda-graph/latest/examples/llama-31-405b.html)).
- Whole-model `torch.compile` under DDP.
- NCCL `torchrun` between the house and the friend.
- DeepSpeed ZeRO-3 or FSDP full shard for the 410M run. A replica fits.
  Full shard adds all-gathers on PCIe. ZeRO pays for itself if the model
  grows toward 1B and a 12 GB card OOMs.

Value residual and logit softcap are still in the bf16 half of the speedrun.
Leave them off until the Muon A/B is done. They change the model, and the
later leaderboard minutes that use them are measured on 8×H100.

SDPA and per-block compile also apply to the 7B trainer. Muon does not.
The speedrun result is for full matrices trained from scratch. On native
Windows, official Triton is not the supported path. Keep the PowerShell
trainer on SDPA plus bitsandbytes until a WSL or Docker venv completes one
step on both a 5070 and a 3060
([triton-windows](https://github.com/triton-lang/triton-windows)).

## Continued learning

Train from scratch once. After that, keep training when repos change. Do not
restart from random weights for each new commit.

What is working is **replay of old data plus a normal learning-rate
schedule**. Elastic weight consolidation and progressive networks are not
the lever. TiC-LM compared them at web scale and ranked replay ahead of EWC;
EWC cut forgetting by giving up performance on the new data
([TiC-LM](https://arxiv.org/abs/2504.02107)).

The published replay percentages are for a huge new corpus with a little old
data sprinkled in. Ibrahim et al. matched a full retrain on the union of old
and new data by re-warming the learning rate, decaying it again, and
replaying old tokens. On a mild shift, 5% replay was enough. On a hard shift
(English to German), they used 25%. Even 1% replay cut forgetting a lot.
50% replay matched the retrain on average loss but learned the new data
worse, because those tokens replaced new tokens at fixed compute
([Ibrahim et al.](https://arxiv.org/abs/2403.08763)). A daily commit is the
opposite regime: the new text is a tiny delta. Training only on that delta
overwrites older files. Old tokens should be most of each batch, and changed
files should be upsampled by a small integer factor. That factor is a
starting guess. Held-out perplexity on unchanged files picks the real one.

Abbes et al. still matter for the other regime (a large new corpus): a small
replay rate beat a high one, and a little replay was a better use of compute
than growing the model ([Abbes et al.](https://arxiv.org/abs/2508.01908)).
Use that paper when a whole new repo or language shows up. Use the inverted
mix for ordinary commits.

Day to day:

1. Rebuild the cleaned snapshot. Scan it. Continue from the last checkpoint.
2. Each batch is the full previous clean corpus plus the new snapshot, with
   changed files upsampled. Keep a frozen probe set per repo.
3. Low learning rate. Do not re-warm for an ordinary commit. Ibrahim showed
   that re-warming spikes loss even when the data distribution has not
   changed. Re-warm, then decay, only when a large new repo or a new
   language is added, and keep the old repos in the mix.
4. Stop the update when perplexity on unchanged held-out files stops
   improving.
5. Reptile or MER interpolation (the chandar-lab hook) stays off until plain
   replay is measured. Same for GeRe, which targets continual fine-tunes
   ([GeRe](https://github.com/Qznan/GeRe)).

Log learned loss (new and changed files), retained loss (frozen probe), and
forgetting (retained loss now minus retained loss when that probe was first
learned).

## Friend over the internet

Two islands.

- **House island:** the four local GPUs. Inner step is NCCL DDP. Data is the
  operator's repos. Data does not leave the house.
- **Friend island:** their GPUs, their data, their copy of the **model**.
  They never receive the repo files.

Sync on an **outer clock**, which is the timing the operator asked for.

DiLoCo ([Douillard et al.](https://arxiv.org/html/2311.08105v3)):

- Copy the shared weights to each island.
- Each island runs H inner steps on its own data. Start at **H = 500**.
  On DeepMind's 150M C4 setup that period was the knee: syncing more often
  had diminishing returns, and H = 1000 cost about 2.9% relative perplexity
  versus H = 50. OpenDiLoCo used the same 500 on a 1.1B model (about 67
  minutes of local work on 8×H100, then a few minutes to all-reduce). Wall
  time here will differ. Size H so one compressed transfer is a small
  fraction of the inner phase on the house uplink
  ([DiLoCo](https://arxiv.org/abs/2311.08105),
  [OpenDiLoCo](https://www.primeintellect.ai/blog/opendiloco)).
- Pseudo-gradient is the parameter delta across those H steps. Inner Adam
  moments stay on the island. They are not synced.
- Average the deltas. Outer optimizer is **Nesterov SGD**, the setting
  DeepMind found robust: learning rate 0.7, momentum 0.9. Plain SGD with
  learning rate 1 is FedAvg, and it was weaker.
- Broadcast the new weights. Repeat.

OpenDiLoCo ran this on Hivemind, with FSDP inside a worker, and saw no
quality drop from reducing the outer delta in FP16. Utilization was 90–95%
on links of roughly 127–935 Mbit/s. The OpenDiLoCo repo is unmaintained; the
follow-on is [prime](https://github.com/PrimeIntellect-ai/prime-diloco).
prime adds `ElasticDeviceMesh` (a joiner pulls the latest checkpoint and
enters the next outer step with a zero pseudo-gradient), int8 outer
gradients accumulated in fp32, and a VPN because public port-forward
bandwidth was unstable. A later compression option, not the first version,
is MuLoCo: Muon inside the island and 2-bit deltas with error feedback
([MuLoCo](https://arxiv.org/html/2505.23725v1)).

**Timing.** The outer round id is the clock. Islands do not barrier every
microbatch. A friend who misses the round is **left out of that average**.
The house keeps training. The original paper's dropout simulation is the
rule: a replica that misses the sync continues from its own weights, and at
a 50% drop rate in their non-i.i.d. run the relative perplexity hit was
2.1%, with loss spikes. Do not let a missing friend freeze the 5070s.
Decoupled DiLoCo (DeepMind, April 2026) is the same idea at datacenter
scale, with a quorum and a grace window, but the released stack is
Pathways, not a homelab package
([arXiv 2604.21428](https://arxiv.org/abs/2604.21428)). A 3060 that is merely
slower does not trip the outer timeout. It is inside the house island.

**Transport.** Tailscale between the two sites, same idea as
[docs/TAILSCALE.md](../../docs/TAILSCALE.md): a private path, no training port
on the public internet. Outer all-reduce goes over that path with Hivemind
(or Gloo if a first prototype has only two islands). NCCL stays on the LAN
inside each island. `torchrun` plus NCCL across the internet fails even
after Tailscale gives both sides an address. OpenDiLoCo's
`torch.distributed` path cannot cross NAT. NCCL's process-group timeout
defaults to 10 minutes, then the job aborts
([torch.distributed](https://docs.pytorch.org/docs/2.11/distributed.html)).
A VPN fixes reachability. It does not make per-step NCCL a WAN algorithm.

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

**Privacy.** Each worker holds the full weights after every outer step.
With two islands the average is half the sum of the two deltas, so the
friend can subtract their own delta and recover the house delta. That delta
is not the corpus. It is still a function of whatever the house trained on.
There is no published DiLoCo setup that uses a friend's GPUs and also
withholds both the corpus and the weights. The corpus filter runs before
the first outer round. The friend trains on the friend's data. They do not
receive a shard of the operator's repos.

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
| [prime-diloco](https://github.com/PrimeIntellect-ai/prime-diloco) | Outer clock, elastic membership, sharded delta. OpenDiLoCo's repo is unmaintained; read prime. A first version can be a few hundred lines for exactly two islands. |

Leave the 7B QLoRA loop inside its current script. Call shared pieces
(packing, wheel check, outer sync of adapters) from both.

## 7B fine-tune

A 7B in bf16 is about 14 GB of weights before optimizer state. It does not
fit in 12 GB. The 7B job stays **QLoRA**: 4-bit frozen base, **bf16**
adapters. "16-bit" for that trainer means the adapter math and the SDPA
dtype, not a bf16 copy of the base model.

QLoRA still runs the GEMM in bf16 (`bnb_4bit_compute_dtype=bfloat16`). Stored
bf16 LoRA of a 7B does not fit these cards. Unsloth's own guide says 16-bit
LoRA is slightly faster and slightly more accurate and uses about 4× the
VRAM of QLoRA, which puts it on a 24 GB-class card
([Unsloth LoRA guide](https://unsloth.ai/docs/get-started/fine-tuning-llms-guide/lora-hyperparameters-guide)).
Their "2× training, about 70% less VRAM" claim is labeled against an 80 GB
setup and, in NVIDIA's writeup, an RTX 5090 32 GB. Quote it as their claim.
Do not treat it as a 12 GB tokens/sec number
([Unsloth benchmarks](https://unsloth.ai/docs/basics/unsloth-benchmarks),
[NVIDIA](https://developer.nvidia.com/blog/train-an-llm-on-an-nvidia-blackwell-desktop-with-unsloth-and-scale-it/)).

Changes worth making in `Start-AlfaTrain7bQlora.ps1` / the GUI, after the
from-scratch smoke test proves the wheel:

1. Same PyTorch 2.14 cu130 wheel, with the matmul check on a 5070 and a 3060.
   bitsandbytes must be a CUDA 12.8 or 13.x build (sm_120 has been in those
   wheels since about v0.45.3). A CUDA 12.6 bitsandbytes wheel omits sm_120
   ([bnb install matrix](https://github.com/bitsandbytes-foundation/bitsandbytes/blob/main/docs/source/installation.mdx)).
   Unsloth's Triton kernels and Liger are a WSL or Docker experiment on the
   Windows trainer. The PowerShell path stays SDPA plus bitsandbytes until
   that venv finishes one step on both cards.
2. SDPA. Padding-free packing needs FlashAttention varlen, which these 5070s
   do not have. Use `SFTConfig(packing=True)` and leave `padding_free` off
   ([TRL packing](https://huggingface.co/docs/trl/en/sft_trainer)).
3. One stack. Unsloth QLoRA **or** Hugging Face Trainer plus Liger. Both
   patch RMSNorm, RoPE, SwiGLU, and the loss. Liger's claim is about 20%
   multi-GPU throughput and about 60% less memory
   ([Liger](https://arxiv.org/html/2410.10989v1)). That claim is theirs.
4. Rank 16, `lora_dropout=0` (Unsloth fuses the adapter when dropout is 0),
   8-bit AdamW, gradient checkpointing if the sequence does not fit. Paged
   AdamW is the spill valve after an eviction, not a faster step
   ([bitsandbytes](https://huggingface.co/docs/bitsandbytes/en/explanations/optimizers)).
5. The 7B already fits on one 12 GB card. A DDP step that includes a 3060
   waits on that card and can be slower than the 5070 alone. Default the 7B
   job to a 5070. Give a 3060 its own QLoRA job (a different mixture, or the
   held-out eval) so the card is used and the 5070 is not gated. Same
   measurement rule as the from-scratch run: if all-four DDP wins on
   tokens/sec, use it. `device_map="auto"` across the two archs is the slow
   path for a model that already fits.
6. Friend sync: outer Nesterov on adapter deltas every H inner steps, over
   Tailscale. The base weights stay where they were loaded. Same two-party
   delta warning as the small model: the friend can recover the house
   adapter delta from the average.
7. Replay of the old instruction set if a later run forgets an earlier task.
   LoRA already forgets less than full fine-tuning and also learns less.
   Biderman et al. continued-pretrained Llama-2 7B on code: best full
   fine-tune HumanEval was 0.263 versus 0.175 for the best LoRA (rank 256,
   all target modules). LoRA was more sensitive to learning rate than to
   rank ([Biderman et al.](https://arxiv.org/abs/2405.09673)). Keep the 7B
   learning rate in the fine-tune range. Do not copy the from-scratch
   re-warmup onto it.

Muon stays on the from-scratch model. On LoRA factors it does not
consistently beat Adam, because the optimizer sees A and B while the model
sees A×B ([PoLoRA](https://arxiv.org/html/2607.17620)). The small model's
weights and tokenizer are not copied into the 7B. The data filter, packing,
and replay mixture are what the two trainers share.

## Build order

Implement in alfa-ai, in this order. Each step is runnable on its own.

1. **Corpus tool.** Read the repo map, filter secrets, pack by repo with the
   borrowed tokenizer, write shards to the hub. No GPU required.
2. **Wheel check.** PyTorch 2.14 cu130. bf16 matmul on one 5070 and one 3060.
   Import-check `torch.optim.Muon`.
3. **Single-island trainer.** 410M, fused AdamW, bf16, SDPA, per-block
   compile, packing, DDP on all four GPUs. Checkpoint to the hub.
4. **Muon flag.** A/B a few hundred steps against AdamW. Keep the winner.
5. **Replay.** Ordinary commits use the inverted mix (old corpus is most of
   the batch, changed files upsampled, no learning-rate re-warm). Log
   learned, retained, and forgetting loss per repo.
6. **Second island.** Two-worker DiLoCo over Tailscale. House data stays
   home. Friend data stays with the friend. H = 500. Outer Nesterov SGD
   (learning rate 0.7, momentum 0.9). A missed round omits that island from
   the average.
7. **7B port.** Same cu130 wheel and bitsandbytes build, SDPA, packing, 5070
   as the default device, and adapter outer-sync in the existing QLoRA
   launcher. Unsloth or Liger only after one step succeeds in WSL or Docker
   on both a 5070 and a 3060.

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
- PyTorch 2.14 cu130 wheel matrix: https://github.com/pytorch/pytorch/blob/main/RELEASE.md
- PyTorch 2.14 release: https://pytorch.org/blog/pytorch-2-14-release-blog/
- torch.optim.Muon: https://github.com/pytorch/pytorch/blob/main/torch/optim/_muon.py
- DDP compile vs allreduce overlap: https://docs.pytorch.org/docs/stable/notes/ddp.md
- Activation checkpointing cost: https://proceedings.mlsys.org/paper_files/paper/2023/file/80083951326cf5b35e5100260d64ed81-Paper-mlsys2023.pdf
- Cut cross-entropy: https://machinelearning.apple.com/research/cut-your-losses
- Mixed-arch FP8 crash: https://github.com/noonghunna/club-3090/issues/762
- bitsandbytes sm_120 wheels: https://github.com/bitsandbytes-foundation/bitsandbytes/blob/main/docs/source/installation.mdx
- torch.amp bf16 vs fp16: https://docs.pytorch.org/docs/2.13/amp.html
- Continual pretraining, replay, learning-rate re-warm: https://arxiv.org/abs/2403.08763
- TiC-LM, replay ahead of EWC: https://arxiv.org/abs/2504.02107
- Abbes et al., replay vs gradient alignment: https://arxiv.org/abs/2508.01908
- Replay implementation: https://github.com/chandar-lab/continual-pretraining
- Code scaling: https://arxiv.org/abs/2510.08702
- Repeated data, about four epochs: https://arxiv.org/abs/2305.16264
- StarCoder2 tokenizer and latest-revision corpus: https://arxiv.org/abs/2402.19173
- DeepSeek-Coder packing and FIM: https://arxiv.org/abs/2401.14196
- LoRA learns less and forgets less: https://arxiv.org/abs/2405.09673
- MuLoCo, 2-bit outer deltas: https://arxiv.org/html/2505.23725v1
- Decoupled DiLoCo (quorum; Pathways, not the homelab package): https://arxiv.org/abs/2604.21428
- NCCL process-group timeout: https://docs.pytorch.org/docs/2.11/distributed.html
- Dec-LoRA: https://arxiv.org/html/2501.15361v1
- Adapter-only DiLoCo sketch: https://github.com/ArioMoniri/moregpu/blob/main/examples/lora_distributed.py
- Unsloth QLoRA vs 16-bit LoRA: https://unsloth.ai/docs/get-started/fine-tuning-llms-guide/lora-hyperparameters-guide
- Liger kernels: https://arxiv.org/html/2410.10989v1
- Muon on LoRA factors: https://arxiv.org/html/2607.17620
