# EduFlow — Demo Script (3-Minute Video)

> **Judging criteria (Hack2Skill):** Impactful Vision 30% | Technical Merit 30% |
> User Experience 20% | Innovation & Creativity 20%
>
> **Video format:** Pre-recorded with jump cuts during AI processing time.
> Total CONTENT is 3 minutes — not 3 minutes of real-time waiting.
> Use screen recorder (OBS) + simple video editor (Clipchamp/DaVinci).

---

## Script Overview

| Segment | Duration | Content | Criteria |
|---|---|---|---|
| A. The Problem | 0:00–0:20 | Emotional hook — stats + parent/student pain | Impactful Vision |
| B. EduFlow in One Line | 0:20–0:30 | Pitch + UI flash | Innovation |
| C. The Full 5-Stage Flow | 0:30–1:15 | Plan → Calendar → Email → Docs (jump cuts) | Technical Merit, UX |
| D. Grade-Aware Teaching | 1:15–1:50 | Same question, two grades — the wow moment | Innovation, Impact |
| E. Voice + Multilingual | 1:50–2:10 | Speak Hindi, get Hindi answer | Impact, Innovation |
| F. Assessment + Parent Report | 2:10–2:35 | Quiz → score → parent email arrives | Technical Merit |
| G. Architecture Flash | 2:35–2:50 | Agent diagram + tech stack | Technical Merit |
| H. Closing | 2:50–3:00 | Tagline + vision | Impactful Vision |

---

## Detailed Script

### A. The Problem [0:00–0:20]

**Screen:** Black background → stat counters animate in one by one.

```
VOICEOVER (slow, deliberate):

"300 million school students across Asia Pacific.
One teacher for every 40 students.
Zero visibility for parents into what their child actually understands.
Private tutoring? $2,000 a year. Unaffordable for 90% of families.

The result: millions of children fall behind —
not because they can't learn,
but because no one is teaching them the right way,
at the right level,
in their own language."
```

**Why this works:** Opens with a specific, verifiable injustice. Judges feel the problem before seeing the solution.

---

### B. EduFlow in One Line [0:20–0:30]

**Screen:** Streamlit UI appears — sidebar + chat visible. Student profile filled in.

```
VOICEOVER:

"EduFlow is an AI-powered personal learning manager —
it plans study sessions, teaches grade-appropriate lessons,
tracks progress, and keeps parents informed.

Not a chatbot. A complete learning workflow.
Powered by Google ADK and Gemini 2.5 Pro."
```

---

### C. The Full 5-Stage Flow [0:30–1:15]

**Setup before recording:**
- Profile: Name=Sabya, Grade=Grade 8, Email=sabyegs@gmail.com,
  Parent=somens.sarkar@gmail.com, Language=English
- Clean Calendar, fresh Drive folder, empty inbox

**[0:30–0:40] Student types the goal:**

```
STUDENT TYPES:
"I want to learn Exponents in 2 days"

NARRATION:
"Sabya, a Grade 8 student, types one sentence."
```

**[0:40–0:45] Jump cut → Plan appears:**

```
SCREEN: The learning plan table appears:
📅 Your Learning Plan: Exponents and Their Powers

| # | Date    | Topic                        | Duration | Video    |
|---|---------|------------------------------|----------|----------|
| 1 | Apr 6   | Introduction to Exponents    | 30 min   | ▶ Watch  |
| 2 | Apr 7   | Laws of Exponents            | 35 min   | ▶ Watch  |

NARRATION:
"EduFlow reads the CBSE Grade 8 curriculum,
plans grade-appropriate sessions,
and finds real YouTube videos for each topic."
```

**[0:45–0:55] Jump cut → Show real integrations (4-second each):**

```
CUT 1 — GOOGLE CALENDAR:
Show the two calendar events with topic name, duration,
and tutor starter prompt in the description.
NARRATION: "Calendar invites — created automatically."

CUT 2 — GMAIL INBOX (parent's email):
Show the plan email with the session table and Google Doc link.
NARRATION: "Parent notified instantly — with a link to study notes."

CUT 3 — GOOGLE DRIVE / DOCS:
Show the study notes document with H1 chapter title,
H2 per session, key concepts, YouTube links.
NARRATION: "A living study notes document — created in Google Drive."
```

**[0:55–1:15] Narrate the impact:**

```
NARRATION:
"In under 3 minutes:
A personalised curriculum plan.
Google Calendar events with study prompts.
A parent email with the full schedule.
A structured Google Doc — ready to grow session by session.

No app switching. No manual scheduling.
One sentence from the student. Everything else — EduFlow."
```

---

### D. Grade-Aware Teaching [1:15–1:50] — THE WOW MOMENT

**Narration:** "Now watch what makes EduFlow different."

**[1:15–1:30] Grade 8 student — Building persona:**

```
STUDENT TYPES:
"Teach me Laws of Exponents"

SCREEN: Formatted lesson appears with sections:
🎯 Hook     — "What if I told you 2³ × 2² = 2⁵ without multiplying anything out?"
📖 Explain  — Laws stated clearly with formal notation
✏️ Example  — Worked step-by-step with code verification:
              print(2**3 * 2**2)  →  ✅ Verified: 32 = 2⁵
💡 Spark    — "What do you think happens when you divide powers of the same base?"

NARRATION:
"A Grade 8 lesson — formal but approachable.
Notice the live code execution verifying the math.
No hallucination. Computed proof."
```

**[1:30–1:45] Same question, different grade — switch profile to Grade 10:**

```
STUDENT TYPES (Grade 10 profile):
"Teach me Laws of Exponents"

SCREEN: Different response appears:
🎯 Hook     — "Here's the elegant insight: exponent laws are consequences of
               the definition of multiplication — nothing more."
📖 Explain  — Formal proof of product rule using sigma notation
✏️ Example  — Multi-step problem + code to verify general case:
              a, m, n = 3, 4, 5; print(a**(m+n) == a**m * a**n) → True
💡 Spark    — "Can you prove the quotient rule from first principles?"

NARRATION:
"Same topic. Same agent. Grade 10 — rigorous, proof-based."
```

**[1:45–1:50]:**
```
SCREEN: Split view — Grade 8 response left, Grade 10 right.

NARRATION:
"Same system. Different grade. Different teacher.
This is adaptive AI education — not just content delivery."
```

---

### E. Voice + Multilingual [1:50–2:10] — INCLUSION MOMENT

**Setup:** Switch profile to Language=Hindi

```
STUDENT CLICKS microphone icon → SPEAKS IN HINDI:
"मुझे घातांक के नियम समझाओ"
(Explain the laws of exponents to me)

SCREEN:
🎤 Transcript appears: "मुझे घातांक के नियम समझाओ"
Then EduFlow responds in Hindi with grade-appropriate explanation.

NARRATION:
"A student in rural India speaks in Hindi.
EduFlow detects the language natively — no translation API.
Gemini 2.5 Pro understands and teaches in Hindi.

70+ languages. Every grade. No extra setup."
```

---

### F. Assessment + Parent Report [2:10–2:35]

```
STUDENT TYPES:
"Quiz me on Laws of Exponents"

SCREEN: Quiz question appears immediately:
"Question 1 of 2: Simplify 2³ × 2²
A) 2¹  B) 2⁵  C) 4⁵  D) 2⁶"

STUDENT ANSWERS: "B) 2⁵"

Question 2 appears → Student answers correctly.

SCREEN: Score appears:
"Perfect score, Sabya! 2 out of 2 — 100%
Great work! I've sent a progress report to you and your parent."

JUMP CUT → GMAIL (parent's inbox):
Show the progress report email with:
- Score: 100%
- Topic: Laws of Exponents
- Google Doc link
- Next session preview

NARRATION:
"Quiz completed. Score calculated. Parent notified.
The entire assessment-to-report pipeline — automated.
No teacher needed for routine progress tracking."
```

---

### G. Architecture Flash [2:35–2:50]

**Screen:** Pre-made architecture diagram (clean, labelled).

```
VOICEOVER:
"Under the hood:

10 specialised agents orchestrated by Google ADK.
Gemini 2.5 Pro — with LearnLM-inspired pedagogical prompts
that adapt to grade level and language.

Google Workspace function tools — Calendar, Gmail, Docs, Drive.
MCP Toolbox — connecting to Cloud SQL for plan and progress data.
YouTube Data API v3 — real educational videos per topic.

Deployed on Google Cloud Run — 3 services, fully serverless.
Built on CBSE curriculum YAML files — extensible to any board or subject."

HIGHLIGHT TEXT ON SCREEN:
10 agents → 5 Google Workspace tools → 70+ languages → 4 grade bands → 3 Cloud Run services
```

---

### H. Closing [2:50–3:00]

```
SCREEN: App UI fades. Tagline appears over clean background.

VOICEOVER (slow, with weight):
"Every student deserves a teacher who knows their name,
speaks their language,
and never gives up on them.

EduFlow — because every student deserves a personal learning manager."

SCREEN: EduFlow logo / name + hackathon name + team name
```

---

## Pre-Recording Checklist

| # | Item | Check |
|---|------|-------|
| 1 | Cloud Run frontend URL opens cleanly | ☐ |
| 2 | Backend health check returns 200 | ☐ |
| 3 | MCP Toolbox running on Cloud Run | ☐ |
| 4 | Sabya profile saved (Grade 8, both emails) | ☐ |
| 5 | Google Calendar cleared of old test events | ☐ |
| 6 | Parent inbox cleared (somens.sarkar@gmail.com) | ☐ |
| 7 | Google Drive: delete old EduFlow test folders | ☐ |
| 8 | Wait 10 min since last test (RPM cooldown) | ☐ |
| 9 | Screen recorder ready (1080p, mic enabled) | ☐ |
| 10 | Architecture diagram image ready | ☐ |
| 11 | Hindi microphone tested | ☐ |
| 12 | Dry run completed (planning works, quiz shows questions) | ☐ |

---

## Video Editing Notes

- **Jump cuts during AI processing** — cut from "student types" to "response appears". Remove wait time.
- **Segment C integrations** — record Calendar, Gmail, Docs as separate clips. Splice in with narration.
- **Segment D split screen** — record Grade 8 and Grade 10 separately. Show side-by-side as static image or quick cuts.
- **Music** — soft background instrumental during A and H. Silence during live demo segments (let the AI do the talking).
- **Captions** — add English captions for the Hindi segment so judges understand what's being said.
- **Export** — 1080p MP4, under 500MB, upload to YouTube (unlisted or public as required).

---

## Fallback Plan

| Failure | Fallback |
|---|---|
| 429 rate limit during recording | Wait 10 min. Try again. One clean run is all that's needed. |
| Calendar / Email / Docs fails | Show pre-captured screenshots from the successful morning test. |
| Voice input fails | Type the Hindi text — response is identical. |
| Quiz shows "waiting for answer" | Type "Show me the quiz question" — question appears. |
| Cold start slow | Pre-warm: open the frontend and send one health check 5 min before recording. |
| Gemini returns empty response | Refresh and retry — RPM resets per minute. |

---

## Judging Criteria Coverage

| Criterion | Weight | How EduFlow covers it |
|---|---|---|
| **Impactful Vision** | 30% | 300M students problem → personal AI teacher for every student |
| **Technical Merit** | 30% | 10 agents, MCP Toolbox, Workspace function tools, Cloud SQL, Cloud Run, YAML curricula, live code execution |
| **User Experience** | 20% | One sentence → full plan. Grade-aware lessons. Voice input. Parent emails. |
| **Innovation** | 20% | Grade-band adaptive pedagogy (LearnLM), native multilingual (70+ langs), living Google Doc that grows session by session |
