# DharmaShield Env — Final Master Document

### *Execution-Based Planning | Build-Ready | April 8 Deadline*


***

## Ek Line Mein Kya Hai Yeh

> **DharmaShield** ek RL environment hai jahan AI agent ek Indian social media platform ka Trust \& Safety Compliance Officer banta hai — incoming content posts review karta hai, India ke real IT Amendment Rules 2026 apply karta hai, UPI scams aur deepfakes detect karta hai, aur 3-hour legal deadline ke under time-bound decisions leta hai. Judges agent ko environment ke saath interact karake dekhte hain ki agent kitna accurately aur efficiently decisions leta hai.

***

## What We Are Building (Hinglish Mein)

**Sochlo ek scenario:**

Tum ek badi social media company ke trust \& safety team mein ho — Instagram ya Koo jaisi. Roz hazaron posts aate hain. Kuch mein UPI scams hain, kuch mein deepfake videos hain, kuch bilkul safe hain. India ki government ne February 2026 mein ek law pass kiya — **IT Amendment Rules 2026** — jisme bola gaya:

> *"Agar koi harmful content report ho, platform ko 3 ghante ke andar remove karna padega. Agar nahi kiya → safe harbour jaayegi → company legally liable hogi."*

Ab socho ki ek AI agent ko yeh kaam seekhana hai. Usse dikhao posts, rules batao, rewards do sahi decisions par, penalty do galat decisions par. **Yahi hai DharmaShield Env.**

**Tech mein:**

- Environment = Python FastAPI server
- Agent = LLM (Qwen/Llama via HuggingFace router)
- Interaction = `reset()` → observation lo → `step(action)` → reward lo → repeat
- Deploy = HuggingFace Spaces Docker container
- Evaluate = automated + human judges

***

## Complete System Architecture (No Code, Just Flow)

```
┌─────────────────────────────────────────────────┐
│              DharmaShield Environment            │
│                                                  │
│  ┌──────────┐    ┌──────────┐    ┌───────────┐  │
│  │ Task     │    │ Policy   │    │ Episode   │  │
│  │ Data     │    │ Book     │    │ State     │  │
│  │ (static) │    │(IT Rules)│    │ Manager   │  │
│  └────┬─────┘    └────┬─────┘    └─────┬─────┘  │
│       │               │                │         │
│       └───────────────┴────────────────┘         │
│                        │                         │
│              ┌──────────▼──────────┐             │
│              │   Core Environment  │             │
│              │  reset() step()     │             │
│              │  state() close()    │             │
│              └──────────┬──────────┘             │
│                         │                        │
│              ┌──────────▼──────────┐             │
│              │    Grader Engine    │             │
│              │  reward compute     │             │
│              │  clamp [0.0, 1.0]   │             │
│              └─────────────────────┘             │
└──────────────────────┬──────────────────────────┘
                       │ FastAPI HTTP
          ┌────────────▼────────────┐
          │      inference.py       │
          │  (runs on judges' side) │
          │  LLM → parse → step     │
          │  [START][STEP][END] log │
          └─────────────────────────┘
```


***

## 5 Core Components — Kya Kya Banana Hai

### Component 1 — `policy_book.py`

**Kya hai**: Python dictionary. 6 real IT Rules. Har rule mein category, required action, time window, safe harbour impact.

**Execution reality**: Yeh sirf data entry hai, coding nahi. 30 minutes research + 30 minutes type karna. Gazette Notification G.S.R. 120(E) publicly available hai MeitY website par.[^1]

**Failure risk**: Zero. Ek dictionary crash nahi karta.

***

### Component 2 — `task_data.py`

**Kya hai**: Teeno tasks ka static dataset. Hardcoded JSON arrays. Har item mein text, ground_truth_decision, ground_truth_rule, difficulty_signal.

**Exact counts**:

- Task 1 (Easy): 8 posts — 5 UPI scam, 3 legitimate
- Task 2 (Medium): 6 posts — 3 SGI/deepfake, 1 disclosed AI, 2 legitimate
- Task 3 (Hard): 5 accounts network — 4 bots, 1 legitimate

**Execution reality**: Content likhna padega. Realistic Hinglish + English mix posts. 2-3 hours. Sirf creativity chahiye, koi library nahi.[^2]

**Failure risk**: Agar content shallow laga → judges "toy" bolenge. **Mitigation**: RBI ke documented top-5 UPI fraud patterns use karo, fabricate mat karo.[^2]

***

### Component 3 — `environment.py`

**Kya hai**: Core logic. `reset()`, `step()`, `state()` implement karta hai. Task queue manage karta hai. Episode state track karta hai.

**Execution reality**: Sabse zyada code yahan hoga — but logic simple hai. State = current step number + queue index + episode stats. No ML, no external API, pure Python dict operations.

**Failure risk**: Shared mutable state bug — agar reset() properly deepcopy nahi karta, dusra episode pehle episode ka data inherit kar lega. **Mitigation**: `deepcopy()` har reset mein. Test: do consecutive resets karo, check karo state fresh hai.

***

### Component 4 — `grader.py`

**Kya hai**: Reward computation. Agent ka action + ground truth → normalized score [0.0, 1.0].

**Formula breakdown**:

```
Per-step reward =
  + 0.40 × decision_correct (0 or 1)
  + 0.30 × rule_correct (1.0 exact / 0.5 category match / 0.0 wrong)
  + 0.15 × time_efficiency (1 - time_used / window)
  + 0.10 × evidence_quality (matched signals / valid signals)
  - 0.40 × false_positive (agar legitimate content remove kiya)

Always clamped: max(0.0, min(1.0, result))
```

**Execution reality**: Sirf arithmetic. Zero external dependency.

**Failure risk**: Negative reward clamp miss ho jaaye → `[END]` mein score < 0 → automated validator flag karega. **Mitigation**: Clamp every single time, wrap mein.

***

### Component 5 — `inference.py`

**Kya hai**: Root directory mein. LLM ko environment se connect karta hai. `[START][STEP][END]` format mein print karta hai.

**Execution reality**: Sample script already provided hai hackathon ne. Tumhe sirf adapt karna hai — env class import karo, action parsing add karo, log format maintain karo.

**Most critical execution rule**: `[END]` log HAMESHA print hona chahiye — chahe episode crash kare, chahe exception aaye. `finally:` block mein rakho.

***

## Improved Failure Points + Better Mitigations

| \# | Failure Point | Old Mitigation | Improved Mitigation |
| :-- | :-- | :-- | :-- |
| 1 | **LLM action parsing fails** | Try/except + fallback action | **Two-layer parsing**: First JSON strict parse → fail → regex keyword extract → fail → default `request_human_review`. Plus: system prompt mein strict format example dena with `respond only in this JSON format:` |
| 2 | **Reward goes outside [^3]** | Simple clamp | **Double clamp**: Har intermediate calculation ke baad bhi clamp, final ke baad bhi. Unit test: grader ko extreme inputs do — max everything, min everything, contradictory inputs — sab [^3] mein aane chahiye |
| 3 | **Episode never terminates** | Hard step cap | **Two-layer termination**: (a) max steps cap (b) queue exhaustion check — agar queue empty ho jaaye toh bhi `done=True`. Both conditions OR se check karo |
| 4 | **Shared mutable state bug** | deepcopy on reset | **Stateless task data**: `TASK_DATA` ko module-level immutable constant rakho. Episode state alag object ho. Reset mein `TASK_DATA` se fresh copy bana — original kabhi mutate na ho |
| 5 | **Inference script crashes mid-run** | try/catch around everything | **Task-level isolation**: Har task ek separate try/except block mein. Agar Task 2 crash kare, Task 1 aur 3 ke scores still valid rahein. `[END]` log score = average of completed tasks only |
| 6 | **Docker build fails on judge machine** | Minimal deps | **Explicit version pinning**: `requirements.txt` mein exact versions — `fastapi==0.115.0`, `pydantic==2.6.0`. No `latest`. No `>=`. Judges ka machine ka environment unknown hai — pinning guarantee karta hai reproducibility |
| 7 | **HF Space /reset times out** | FastAPI lightweight | **Warmup endpoint**: `/health` GET endpoint jo sirf `{"status": "ok"}` return kare. Space startup pe yahi ping hoti hai. Plus: Dockerfile mein `HEALTHCHECK` CMD add karo |
| 8 | **Hinglish text breaks LLM** | Pre-written posts | **Fallback in observation**: Har Hinglish post ke saath ek `english_summary` field optional mein add karo — agent chahe Hinglish padhe, chahe summary. Grader sirf decision aur rule check karta hai, text comprehension nahi |
| 9 | **Hard task graph too complex** | 5-node graph | **Progressive reveal**: Agent pehle sirf Account_A dekhe. `step()` ke baad linked_accounts reveal ho. Yeh zyada realistic hai aur execution mein zyada manageable — agent ko sab ek saath nahi process karna |
| 10 | **`openenv validate` fails on yaml** | Typed models | **Validate locally first**: Build se pehle `openenv validate` locally run karo. Agar fail kare → yaml fields check karo. Common mistake: `tasks` array missing ya `reward_range` field wrong format |


***

## 🔴 Hard Testing Plan — Break It Before Judges Do

Yeh section sabse important hai execution mein. **Judges ka automated pipeline tumhara environment exact usi tarah test karega jaise tumne nahi socha hoga.** Isliye pehle tum khud worst-case scenarios run karo.

***

### Test Category 1 — Worst-Case LLM Output

Yeh test karo: inference.py mein LLM call ko temporarily bypass karo aur manually yeh outputs feed karo environment ke `step()` mein. Dekhna yeh hai ki environment kaise respond karta hai.

**Scenario 1.1 — Empty String**

```
LLM returns: ""
```

Kya hona chahiye: Parser layer empty string pakde → fallback action `request_human_review` → reward 0.0 → episode continue kare, crash na kare. `done=False`, next step pe jaaye.

Agar crash kare to matlab: Parser mein empty string check missing hai → fix karo.

**Scenario 1.2 — Invalid JSON (Most Common Real Failure)**

```
LLM returns: "I think this post should be removed because it looks like a scam."
```

Kya hona chahiye: JSON parse fail → regex layer "remove" keyword detect kare → partial action construct ho → grader ko jaaye → score mile (low, kyunki rule_cited missing hai, but non-zero). Episode continue kare.

Agar crash kare to matlab: Regex fallback implement nahi hua → fix karo.

**Scenario 1.3 — Partially Valid JSON**

```
LLM returns: {"decision": "remove", "rule_cited": null}
```

Kya hona chahiye: Pydantic validation fail kare null rule_cited pe → fallback with `rule_cited="UNKNOWN"` → grader rule_accuracy = 0.0, decision_accuracy = 1.0 → partial reward mile. No crash.

**Scenario 1.4 — Completely Random Text**

```
LLM returns: "banana 12345 @#$% lorem ipsum"
```

Kya hona chahiye: JSON fail → regex koi keyword nahi milta → absolute fallback action triggered → reward 0.0 → `done=False` → next step. Environment stable rahe.

**Scenario 1.5 — Valid JSON But Wrong Field Names**

```
LLM returns: {"action": "remove", "law": "IT_2021"}
```

Kya hona chahiye: Pydantic model field `decision` expect karta hai, `action` nahi → validation fail → fallback triggered. Yeh common LLM mistake hai — field name slightly different deta hai.

***

### Test Category 2 — Edge Cases in Agent Behavior

**Scenario 2.1 — Agent Har Step Pe Same Action Deta Hai**

```
All 8 steps: {"decision": "remove", "rule_cited": "IT_2021_3_1_b_iii"}
```

Kya hona chahiye: Task 1 mein 3 legitimate posts bhi hain jo approve hone chahiye. Agent sab remove kare → false positive penalty for each legitimate post → final score heavily penalized (around 0.2-0.3). `[END]` log print ho. No crash.

Yeh test important hai kyunki judges' automated agent (Nemotron) bhi kisi task pe monotonous behavior deta hai. Environment ko handle karna chahiye.

**Scenario 2.2 — Agent Sirf `approve` Karta Rahe**

```
All steps: {"decision": "approve"}
```

Kya hona chahiye: Scam posts approve ho jaayein → decision_accuracy = 0 for those → per-step reward sirf time component (0.15) → final score ~0.15. No crash, valid output.

**Scenario 2.3 — Agent Action Mein `rule_cited` Field Missing**

```
{"decision": "remove", "confidence": 0.9, "reason": "looks bad", "notify_user": true}
```

Kya hona chahiye: Pydantic `rule_cited` required field hai. Missing → validation error → fallback with `rule_cited="UNKNOWN"` → rule_accuracy = 0.0 → partial reward only from decision. No crash.

**Scenario 2.4 — Agent `confidence: 2.5` Deta Hai (Out of Range)**

```
{"decision": "remove", "rule_cited": "IT_2021_3_1_b_iii", "confidence": 2.5}
```

Kya hona chahiye: Pydantic `confidence: float = Field(ge=0.0, le=1.0)` → validation fail → clamp to 1.0 ya fallback. Confidence field grader mein directly use nahi hota scoring mein, so impact minimal. No crash.

**Scenario 2.5 — Agent Task 3 Mein Account_D Ko Remove Kare (Intended Hard Case)**

```
Hard task mein agent correctly sab bots remove kare lekin Account_D (legitimate) bhi remove kare
```

Kya hona chahiye: Yeh design by intent hai. Grader `false_positive_penalty = -0.40` apply kare. Score significantly drop ho. `[END]` mein score dikhega — low but valid. Yeh grader ka "depth" demonstrate karta hai judges ke liye.

***

### Test Category 3 — System Stress Testing

**Scenario 3.1 — Multiple Consecutive Resets**

Manual test plan:

1. `reset()` call karo → note karo starting state
2. `step()` 3 times karo with valid actions
3. `reset()` phir se call karo
4. Check: kya state bilkul fresh hai? Step counter 0 hai? Queue original hai? Previous episode ka koi data nahi?
5. Repeat 5 times

**What to verify**: Har reset ke baad observation bilkul identical ho. Agar koi bhi difference hai — mutable state bug hai. Yeh automated pipeline mein tab break karta hai jab judges multiple runs karte hain.

**Scenario 3.2 — Max Steps Forcefully Reached**

Manual test plan:

1. `reset()` karo
2. Max steps se zyada `step()` calls karo (jaise Task 1 mein max 10 hai, tum 15 calls karo)
3. Check: 10th step ke baad `done=True` return hua? 11th call pe kya hota hai?

**Kya hona chahiye**: 10th step pe `done=True`. Agar 11th call ho bhi jaaye → environment gracefully handle kare — ya toh last observation return kare ya error info deke `done=True`. Never crash, never hang.

**Scenario 3.3 — Time Exceeded Simulation**

Task 3 mein `time_remaining_hours` field countdown karta hai. Manually simulate karo:

1. Episode start karo
2. Har step mein time value manually 0.1 se reduce karo
3. Jab `time_remaining_hours <= 0` ho jaaye → kya `time_efficiency` reward correctly 0 ho jaata hai?
4. Kya episode `done=True` hota hai ya continue karta hai?

**Design decision**: Time expiry pe episode `done=True` ya sirf penalty? **Recommendation**: Episode continue kare (realistic — platform still has to process) but `time_compliance_score = 0.0` for all remaining steps. Isse agents sirf time waste karke episode end nahi kar sakta.

**Scenario 3.4 — Rapid Fire Steps Without Reset**

```
reset() → step() → step() → step() ... 50 times
```

Kya hona chahiye: Max steps cap hit ho → `done=True` → agar 51st step call ho toh environment gracefully handle kare. 50 rapid calls mein memory leak na ho, response time consistent rahe (yeh vcpu=2 constraint hai).

**Verify**: Har step response time < 500ms. Agar kisi step mein slow ho jaaye → bottleneck find karo. (Most likely: agar koi logging ya file write hai step mein → remove karo.)

***

### Test Category 4 — Docker Fresh Machine Test

Yeh sabse important test hai. **"Works on my machine" syndrome se bachna hai.**

**Step 1 — Nuclear Reset Test**
Apne system se image completely remove karo:

```
docker rmi dharma-shield-env --force
docker system prune -a
```

Phir fresh se:

```
docker build -t dharma-shield-env .
docker run -p 7860:7860 dharma-shield-env
```

Agar yahan fail ho → requirements.txt mein kuch missing hai ya Dockerfile mein path wrong hai.

**Step 2 — No Pre-Installed Packages Assumption**
Dockerfile mein explicitly verify karo:

- Python version specified hai? (`python:3.11-slim` — not just `python:latest`)
- Sab dependencies `requirements.txt` mein hain?
- Koi local file path hai jo container mein nahi hogi? (common mistake: `../utils/helper.py` type imports)
- `WORKDIR` correctly set hai?

**Step 3 — Port Binding Test**

```
docker run -p 7860:7860 dharma-shield-env
curl -X POST http://localhost:7860/reset -H "Content-Type: application/json" -d '{}'
```

Expected: 200 OK + valid JSON observation. Agar connection refused → FastAPI server properly start nahi hua → `CMD` instruction Dockerfile mein check karo.

**Step 4 — Environment Variable Test**
Judges ke pipeline mein `HF_TOKEN`, `API_BASE_URL`, `MODEL_NAME` env vars inject hote hain. Verify karo:

- Agar `HF_TOKEN` missing ho → inference.py crash na kare, meaningful error message de
- `API_BASE_URL` ka default value set hai (`https://router.huggingface.co/v1`)
- `MODEL_NAME` ka default value set hai (`Qwen/Qwen2.5-72B-Instruct`)

**Step 5 — HF Space Simulation**
HF Spaces mein environment variables alag inject hote hain. Local mein simulate karo:

```
docker run -p 7860:7860 \
  -e HF_TOKEN="test_token" \
  -e API_BASE_URL="https://router.huggingface.co/v1" \
  -e MODEL_NAME="Qwen/Qwen2.5-72B-Instruct" \
  dharma-shield-env
```

Phir inference.py run karo. Agar work kare → HF Space pe bhi work karega.

**Step 6 — Memory Constraint Test (vcpu=2, 8GB RAM)**
HF Space pe resource constraint hai. Verify karo:

- Container idle mein kitna memory use karta hai? (Should be < 500MB)
- Ek full inference run (3 tasks, ~30 LLM calls) mein peak memory? (Should be < 2GB)
- Agar zyada hai → koi bhi list unnecessarily accumulate ho rahi hai history mein → cap karo last 5 items tak

***

### Test Category 5 — [START][STEP][END] Log Format Verification

**Yeh Phase 1 automated evaluation ka core hai.** Log format bilkul exact hona chahiye — ek bhi field name wrong → score 0.

**Correct format verify karo**:

```
[START] task=upi-scam-triage env=dharma-shield model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=remove reward=0.70 done=false error=null
[STEP] step=2 action=approve reward=0.55 done=false error=null
[END] success=true steps=8 score=0.823 rewards=0.70,0.55,0.70,0.70,0.40,0.70,0.55,0.70
```

**Check karo**:

- `done` lowercase hai? (`false` not `False`) ✓
- `success` lowercase hai? ✓
- `score` 2 decimal places hai? (`.3f` format) ✓
- `rewards` comma-separated, 2 decimal each? ✓
- `error=null` jab koi error nahi? ✓
- Koi extra newline nahi hai line ke andar? ✓
- `[END]` line HAMESHA print hoti hai, exception ke baad bhi? ✓

**Test**: Manually grep karo output:

```
python inference.py 2>&1 | grep -E "^\[START\]|^\[STEP\]|^\[END\]"
```

Sirf yeh 3 types ki lines dikhni chahiye, koi format deviation nahi.

***

## 3-Day Execution Timeline (April 5-8)

### Day 1 — Today Evening (April 5, 4 PM - 11 PM)

```
4:00 PM  →  GitHub repo scaffold karo (folder structure)
5:00 PM  →  policy_book.py — 6 rules research + type karo (MeitY docs)
6:30 PM  →  task_data.py — 8+6+5 posts likhna (RBI UPI patterns use karo)
8:30 PM  →  models.py — Pydantic types define karo
10:00 PM →  grader.py — reward formula implement karo
11:00 PM →  Locally test: grader ko mock inputs do, rewards check karo
```


### Day 2 — April 6 (Full Day)

```
Morning  →  environment.py — reset/step/state implement
Midday   →  FastAPI server wrap karo (/reset /step /state endpoints)
Afternoon → inference.py — LLM connect karo, [START][STEP][END] logs
Evening  →  End-to-end local run: inference.py → env → output dekhna
Night    →  Hard Testing Plan execute karo (ALL 5 categories above)
           Fix every failure found
```


### Day 3 — April 7 (Polish + Deploy)

```
Morning  →  Dockerfile write karo, docker build locally test karo
           Docker Fresh Machine Test (Category 4) run karo
Midday   →  HuggingFace Space create karo, push karo, /reset ping karo
Afternoon → openenv.yaml finalize, openenv validate run karo
Evening  →  Full pre-submission checklist run karo
           [START][STEP][END] log format verify karo (Category 5)
Night    →  README write karo, submit karo
```


### April 8 — Buffer Day

```
Only for fixes. Agar kuch broken ho toh fix karo.
Agar sab perfect ho — rest karo.
```


***

## What Makes DharmaShield Win (Final Summary)

**Vs. Generic Teams**: Unka environment `email_triage_env` ya `customer_support_env` hoga — problem statement ke examples seedha copy. DharmaShield ek **India-specific regulatory framework** pe based hai jo 45 days pehle enforce hua. Koi generic team is depth tak nahi jayegi.[^4][^1]

**Vs. Professional Teams**: Professionals complex banate hain — real ML models integrate karte hain, Kubernetes simulate karte hain. Unka environment execution mein break karta hai ya 20 min timeout hit karta hai. DharmaShield mein **koi ML model nahi, koi external API nahi** — pure Python dict operations. Execution perfect hogi.[^5]

**Vs. International Teams**: UPI scam patterns, Aadhaar-linked signals, Hinglish content, IT Rules 2026 India-specific obligations — **koi international team is context ko match nahi kar sakti**.[^6][^2]

***

## Final Hinglish Summary — Koi Bhi Samjhe

> **DharmaShield kya hai?**
> Ek AI training environment hai jahan ek AI agent ek social media company ka "digital police officer" banta hai. Usse posts dikhaye jaate hain — kuch mein UPI scam hota hai, kuch mein AI se banaya fake video hota hai, kuch bilkul safe hote hain. Agent ko yeh decide karna hota hai: "Remove karo? Label karo? Approve karo? Escalate karo?" — aur yeh bhi batana hota hai ki **konsa law apply hua** aur **kyun**. India ka real law (IT Amendment Rules 2026) use hota hai — koi made-up rules nahi. Agar agent sahi decision le — reward milta hai. Agar galti kare — penalty milti hai. Agar koi safe post galti se remove kare — badi penalty. Teen tasks hain: easy se hard tak. Puri cheez ek Docker container mein chalti hai, HuggingFace Spaces pe deploy hoti hai, aur ek `inference.py` script judges ke testing pipeline se connect hoti hai.

> **Hum kya use kar rahe hain?**
> Python + FastAPI (server) → Pydantic (typed data models) → Static hardcoded data (no ML, no external APIs) → HuggingFace LLM router (Qwen 72B agent ke liye) → Docker (packaging) → HuggingFace Spaces (deployment) → Real India laws (IT Rules 2026, UPI fraud patterns from RBI data)

> **Hum kyun jeetenge?**
> Kyunki yeh environment **real hai, executable hai, crash-proof hai, aur India ka apna hai** — koi duplicate nahi kar sakta.[^1][^2]

***

**Idea phase over. Testing plan ready. Ab build karo.**

<div align="center">⁂</div>
