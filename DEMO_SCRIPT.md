# EduFlow — Demo Script (3-Minute Video) & Test Plan

> **Judging criteria (Hack2Skill):** Impactful Vision 30% | Technical Merit 30% |
> User Experience 20% | Innovation & Creativity 20%.
> Every second of the demo must hit at least one criterion.

---

## Script Overview

| Segment | Duration | Purpose | Criteria targeted |
|---|---|---|---|
| A. The Problem | 0:00–0:20 | Emotional hook — why this matters | Impactful Vision |
| B. EduFlow in One Line | 0:20–0:30 | Elevator pitch | Innovation |
| C. Live Demo — Planning | 0:30–1:10 | Student creates a learning plan | Technical Merit, UX |
| D. Live Demo — Grade-Aware Teaching | 1:10–1:50 | Split-screen wow moment | Innovation, Impact |
| E. Live Demo — Voice + Multilingual | 1:50–2:15 | Student speaks in Hindi | Impact, Innovation |
| F. Live Demo — Real Integrations | 2:15–2:35 | Calendar + Tasks + Docs + Email proof | Technical Merit |
| G. Architecture Flash | 2:35–2:50 | Agent diagram + tech stack | Technical Merit |
| H. Closing | 2:50–3:00 | Tagline + impact statement | Impactful Vision |

---

## Detailed Script with Exact Inputs & Expected Outputs

### A. The Problem [0:00–0:20] — Voiceover + Stats on Screen

```
VOICEOVER:
"In Asia Pacific, over 250 million school students struggle without
structured learning support. Teachers handle 40+ students per class.
Parents have no visibility into what their child actually understands.
Private tutoring costs $2,000 per year — unaffordable for most families."

SCREEN: Animated stat counters or simple text slides with key numbers.
```

**Test checkpoint:** N/A (pre-recorded voiceover + slides)

---

### B. EduFlow in One Line [0:20–0:30] — Voiceover + Product Shot

```
VOICEOVER:
"EduFlow is an AI teaching assistant that plans, schedules, teaches,
and reports — in the student's own language, at their own level.
Not a chatbot. A complete learning workflow."

SCREEN: Quick flash of the Streamlit UI with sidebar + chat visible.
```

**Test checkpoint:** App loads, sidebar shows profile form + quick actions.

---

### C. Live Demo — Planning [0:30–1:10]

**Setup:** Student profile already filled: Name=Priya, Grade=8, Subject=Math,
Language=English, Parent Email=parent@example.com

```
STUDENT TYPES:
"I want to learn Quadratic Equations in 1 week"

EXPECTED AGENT RESPONSE (orchestrator → planning_pipeline):
"Great, Priya! I've created a learning plan for Quadratic Equations.
Based on the topic depth, I've planned [N] sessions:

 Session 1 (Mon): Basics & Standard Form
 Session 2 (Wed): Factoring Method
 Session 3 (Fri): ...
 ... (AI determines session count based on concept depth & prerequisites)

Each session includes a recommended video. I've also added these to your
Google Calendar and sent the plan to your parent's email."

NOTE: Session count is NOT hardcoded — the curriculum_planner_agent
determines it based on topic depth, prerequisites, and grade band.

SCREEN SHOWS:
✓ Sidebar updates with plan progress (Sessions listed)
✓ Each session shows topic name + video title
```

**Test checkpoints:**
- [ ] `curriculum_planner_agent` reads YAML for Grade 8 Math → Quadratic Equations
- [ ] `content_agent` returns YouTube video URLs for each session topic
- [ ] `calendar_agent` creates Google Calendar events for each session (verify in Calendar)
- [ ] `email_agent` sends learning plan email to parent (verify in inbox)
- [ ] Sidebar plan tracker renders correctly
- [ ] Session state keys populated: `current_plan_id`, `session_topic`

---

### D. Live Demo — Grade-Aware Teaching [1:10–1:50] — THE WOW MOMENT

**Narration:** "Watch what happens when two different students ask the same question."

**Scene 1 — Grade 6 student (Foundation band):**

```
STUDENT PROFILE: Name=Arjun, Grade=6, Language=English
STUDENT TYPES: "What is the area of a circle?"

EXPECTED TUTOR RESPONSE (Foundation persona):
"Did you know that if you cut a pizza into lots of tiny slices
and rearrange them, you get a rectangle?

The long side is half the crust — that's π times the radius (r).
The short side is just the radius.

So the area = long side × short side = π × r × r

Try this: If your pizza has a radius of 7 cm, what's the area?
What do you think — is a bigger pizza always a better deal?"

YOUTUBE VIDEO: Animated "Area of Circle" for kids
```

**Scene 2 — Grade 10 student (Bridging band):**

```
STUDENT PROFILE: Name=Meera, Grade=10, Language=English
STUDENT TYPES: "What is the area of a circle?"

EXPECTED TUTOR RESPONSE (Bridging persona):
"Here's the insight that makes this click — we can derive it from
first principles using integration.

Imagine the circle as infinite thin concentric rings of width dr
at distance r from center. Each ring has circumference 2πr and
area 2πr·dr. Integrating from 0 to R:

A = ∫₀ᴿ 2πr dr = 2π · [r²/2]₀ᴿ = πR²

The code below verifies this numerically:"
[code_executor runs integration, outputs πR²]

"Why does integrating rings give us the area, but integrating
slices (like pizza) gives us the same answer through a completely
different geometric argument?"

YOUTUBE VIDEO: Lecture-style proof of circle area
```

**NARRATION:** "Same system. Same agent. Different grade. Different teacher."

**Test checkpoints:**
- [ ] Grade 6 profile → `get_grade_band()` returns "foundation"
- [ ] Grade 10 profile → `get_grade_band()` returns "bridging"
- [ ] Tutor uses simple vocabulary + pizza analogy for Grade 6
- [ ] Tutor uses integration + code_executor for Grade 10
- [ ] YouTube results differ: animated vs lecture-style
- [ ] Response follows HOOK → EXPLAIN → EXAMPLE → SPARK pattern

---

### E. Live Demo — Voice + Multilingual [1:50–2:15] — INCLUSION MOMENT

**Narration:** "EduFlow works in 70+ languages. Let's switch to Hindi."

```
STUDENT PROFILE: Name=Rahul, Grade=7, Language=Hindi
STUDENT SPEAKS INTO MICROPHONE (in Hindi):
"मुझे गति और वेग के बीच का अंतर समझाओ"
(Explain the difference between speed and velocity)

EXPECTED TUTOR RESPONSE (in Hindi, Building persona):
"क्या तुमने कभी सोचा है कि दो बच्चे एक ही तेज़ी से दौड़ रहे हैं,
लेकिन एक सीधा दौड़ रहा है और दूसरा गोल-गोल? कौन ज़्यादा आगे पहुँचेगा?

गति (Speed) = कितनी तेज़ी से चल रहे हो — बस एक नंबर।
वेग (Velocity) = कितनी तेज़ी से + किस दिशा में — नंबर + दिशा।

उदाहरण: अगर तुम 5 km/h से उत्तर की तरफ चलो, तो तुम्हारी गति 5 km/h है
और वेग 5 km/h उत्तर है।

सोचो: अगर तुम गोल-गोल दौड़कर वापस शुरू की जगह आ जाओ, तो तुम्हारी
औसत गति शून्य होगी या वेग?"

YOUTUBE VIDEO: Hindi physics tutorial on speed vs velocity
```

**NARRATION:** "A Grade 7 student in rural India speaks in Hindi,
asks about physics, and gets a friendly grade-appropriate explanation
in Hindi. No translation API. No speech-to-text service.
Just Gemini's native multimodal capability."

**Test checkpoints:**
- [ ] `st.audio_input` captures audio correctly
- [ ] Gemini auto-detects Hindi from audio
- [ ] Response is in Hindi (not English)
- [ ] Vocabulary matches "building" band (Grade 7)
- [ ] YouTube search includes Hindi/grade-appropriate modifiers
- [ ] Physics subject handled correctly (Motion chapter from seed data)

---

### F. Live Demo — Real Integrations [2:15–2:35] — PROOF IT'S REAL

**Narration:** "Five Google Workspace tools. One MCP server. All real."

```
SCREEN SHOWS (quick cuts, 4 seconds each):

1. GOOGLE CALENDAR: Open Calendar app → show study session events
   with correct dates, times, and video links in description.
   "These events were created by the AI — not by us."

2. GOOGLE TASKS: Open Tasks → show TaskList with sessions,
   Session 1 ✅ completed, remaining ☐ pending.
   YouTube links and key concept notes attached to each task.
   "The student's progress — tracked automatically."

3. GOOGLE DOCS: Open the study notes document → show formatted
   headings, key concepts, YouTube links, practice problems.
   "Study notes — created and updated after every session."

4. GMAIL INBOX: Open Gmail → show learning plan email sent to parent.
   Includes Google Doc link for parent to review.
   "The parent stays informed — with one click to the notes."

5. STREAMLIT SIDEBAR: Show plan progress tracker with session statuses.
   "The student sees their entire journey at a glance."
```

**NARRATION:** "Calendar schedules. Tasks track. Docs remember.
Gmail reports. A complete productivity ecosystem — for learning."

**Test checkpoints:**
- [ ] Google Calendar has real events with correct details
- [ ] Google Tasks has TaskList with tasks, links, notes, correct statuses
- [ ] Google Docs has formatted study notes with headings + YouTube links
- [ ] Drive has organized folder structure (EduFlow/{Subject}/{Grade}/)
- [ ] Gmail inbox has learning plan email with Doc link
- [ ] Sidebar progress tracker reflects current plan state

---

### G. Architecture Flash [2:35–2:50] — TECHNICAL CREDIBILITY

```
SCREEN: Pre-made architecture diagram (CLAUDE.md Section 8.1 style) with labels.

VOICEOVER:
"Under the hood: 8 specialized sub-agents orchestrated by Google ADK.
One Google Workspace MCP server covers Calendar, Tasks, Gmail,
Docs, and Drive. MCP Toolbox connects to AlloyDB.
Gemini 2.5 Flash powers every agent — with LearnLM-inspired
pedagogical prompts that adapt to grade level and language.
Deployed on Google Cloud Run. Built for scale."

HIGHLIGHT (animated or pointed):
  "8 sub-agents → 2 MCP servers → 5 Workspace tools → 70+ languages → 4 grade bands"
```

**Test checkpoint:** Architecture diagram is accurate and matches actual implementation.

---

### H. Closing [2:50–3:00] — LEAVE A MARK

```
VOICEOVER:
"250 million students need a teacher who adapts to them —
their grade, their language, their pace.

EduFlow: Because every student deserves a personal learning manager."

SCREEN: App UI fades to tagline + team name.
```

---

## Pre-Demo Setup Checklist

| # | Item | Status |
|---|---|---|
| 1 | Backend running (Cloud Run or local) | ☐ |
| 2 | Frontend running (Streamlit) | ☐ |
| 3 | AlloyDB running + custom tables created | ☐ |
| 4 | MCP Toolbox running and connected | ☐ |
| 5 | `gws mcp` running with valid OAuth (`gws auth login` done) | ☐ |
| 6 | Verify: `gws` can create Calendar event, Task, Doc, send Gmail | ☐ |
| 7 | YouTube API key valid (check quota) | ☐ |
| 8 | YAML curriculum files loaded (Math Grade 6, 8, 10) | ☐ |
| 9 | 3 student profiles pre-created: Arjun (Grade 6), Priya (Grade 8), Meera (Grade 10) | ☐ |
| 10 | Hindi profile ready: Rahul (Grade 7, Hindi) | ☐ |
| 11 | Google Calendar cleared of old test events | ☐ |
| 12 | Google Tasks cleared of old test task lists | ☐ |
| 13 | Parent email inbox cleared for clean demo | ☐ |
| 14 | Microphone tested for voice input | ☐ |
| 15 | Screen recorder ready (OBS or similar) | ☐ |
| 16 | Architecture diagram image prepared | ☐ |
| 17 | Dry run completed successfully at least once | ☐ |

---

## Fallback Plan (If Something Breaks Live)

| Failure | Fallback |
|---|---|
| `gws mcp` fails entirely | Fall back to direct Google API function tools (pre-built backup). |
| Calendar doesn't create event | Show a pre-captured screenshot. Tasks still proves scheduling works. |
| Tasks doesn't create list | Calendar events + Doc notes still show the workflow. |
| Docs/Drive fails | Show tutor output directly. Notes are a bonus, not the core flow. |
| Gmail fails | Show a pre-captured screenshot of a previously sent email. |
| Voice input fails | Type the Hindi text instead. Gemini handles Hindi text equally well. |
| YouTube API quota hit | YAML `youtube_search_hints` provide pre-seeded video IDs as fallback. |
| Slow response (cold start) | Pre-warm backend 5 min before recording. Have a pre-recorded backup clip. |
| Gemini rate limit | Use API key (not Vertex AI) for demo. Lower RPM but sufficient for demo. |
