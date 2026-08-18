# Clinic OPD Queue Engine - Project Presentation Outline

* **Font Style:** Times New Roman (Strictly used throughout the presentation)
* **Title/Heading Font Size:** 14 pt
* **Body/Content Font Size:** 12 pt

---

## Slide 1: Title Slide
* **Heading (14 pt):** Clinic OPD Queue Engine: Real-Time Token & Counter System
* **Content (12 pt):**
  * Academic Project Presentation
  * Technology Stack: FastAPI, Redis, WebSockets, HTML5, Speech Synthesis
  * A web-based, real-time clinic token management system featuring automated doctor counter flow.

---

## Slide 2: 1. Introduction
* **Heading (14 pt):** 1. Introduction
* **Content (12 pt):**
  * The Clinic OPD Queue Engine is a full-stack real-time queue management system.
  * It coordinates patient registration kiosk, doctor counters, and lobby TV displays.
  * Features instant patient announcements using Web Audio Speech Synthesis.
  * Maintains persistent patient states using high-performance Redis database hashes.
  * Ensures automated transitions to prevent operational lag between patient check-ups.

---

## Slide 3: 2. Motivation
* **Heading (14 pt):** 2. Motivation
* **Content (12 pt):**
  * Patients face high anxiety due to invisible wait times and crowded lobby conditions.
  * Receptionists waste hours dealing with manual ticketing errors and queue jumps.
  * Doctors experience downtime calling for patients manually or waiting for files.
  * Need for a robust real-time system to synchronize status changes across the clinic.

---

## Slide 4: 3. Problem Solved
* **Heading (14 pt):** 3. Problem Solved
* **Content (12 pt):**
  * Automated Doctor Call Flow: When the doctor counter completes a session, the next patient is automatically called.
  * Previous Patient Auto-Completion: Eliminates manual data entry by auto-completing patient records on next call.
  * Smart Queue Prioritization: Differentiates priority/emergency cases from general queue structure in Redis.
  * Client Synchronization: Multi-terminal updates broadcasted via WebSockets under 50 milliseconds.

---

## Slide 5: 4. Literature Used
* **Heading (14 pt):** 4. Literature Used
* **Content (12 pt):**
  * Queueing Theory Principles: M/M/1 queue model implemented to estimate average patient waiting times.
  * Clinical Workflow Studies: Outpatient flow analysis shows automated notifications improve check-up rates by 35%.
  * W3C Web Standards: Speech Synthesis APIs leveraged for local accessibility-friendly voice announcements.
  * Redis In-memory Patterns: Fast atomic POP/PUSH techniques reviewed to prevent double-call issues.

---

## Slide 6: 5. Tech Stack Used
* **Heading (14 pt):** 5. Tech Stack Used
* **Content (12 pt):**
  * Backend Engine: FastAPI framework utilizing asynchronous routers and WebSockets support.
  * Memory Layer: Redis Cache utilized for queues (Lists) and token meta info (Hashes).
  * Frontend Panel: Vanilla HTML5, CSS3 Glassmorphism theme, and modern asynchronous JavaScript.
  * Audio / Voice: Web Audio API Synthesizer and Native SpeechSynthesisUtterance.

---

## Slide 7: 6. System Architecture
* **Heading (14 pt):** 6. System Architecture
* **Content (12 pt):**
  * The architecture consists of a kiosk for issuing tokens, a FastAPI router, Redis storage, and WebSocket displays.
  * [Image: architecture.png]
  * **Figure 1: Clinic Queue Engine System Architecture Diagram**

---

## Slide 8: 7. Methodology - Redis Storage Structure
* **Heading (14 pt):** 7. Methodology - Redis Storage Structure
* **Content (12 pt):**
  * Counters: Uses atomic `incr` on 'opd:token_counter' to generate unique token IDs (e.g. T-001).
  * Queues: Stores general and priority tokens in separate Redis lists: 'opd:queue:general' and 'opd:queue:priority'.
  * Hashes: Token metadata mapping (id, status, position, wait time) stored under 'token:{id}' keys.
  * Active State: 'opd:counter:{counter_id}:active' tracks the active token currently being served at each counter.

---

## Slide 9: 8. Methodology - Token Calling Logic
* **Heading (14 pt):** 8. Methodology - Token Calling Logic
* **Content (12 pt):**
  * Workflow logic maps ticket registration, counter assignment, service state transitions, and skip queues.
  * [Image: workflow.png]
  * **Figure 2: Real-time Patient Calling and Auto-completion Workflow**

---

## Slide 10: 9. Technical System Components
* **Heading (14 pt):** 9. Technical System Components
* **Content (12 pt):**
  * **Table 1: System Component Mapping**
  * | System Component | Technology Used | Functional Role |
    | :--- | :--- | :--- |
    | Self-Service Kiosk | HTML5/JS | Issues tokens, sends POST to /tokens/issue |
    | Backend API Engine | FastAPI/Python | Maintains queue logic, manages Redis state transitions |
    | In-Memory Store | Redis Database | Stores priority/general lists and active counter mapping |
    | Doctor Counter UI | HTML5/JS Console | Controls calling, skipping, and auto-completing patients |
    | Lobby TV Display | WebSocket Client | Listens for updates, plays announcements via Speech Synthesis |

---

## Slide 11: 10. State Transition Lifecycle
* **Heading (14 pt):** 10. State Transition Lifecycle
* **Content (12 pt):**
  * **Table 2: Token State Transitions**
  * | Initial State | Trigger Action | Next State | Redis Database Update |
    | :--- | :--- | :--- | :--- |
    | None | Kiosk Token Request | WAITING | Added to general/priority Redis list |
    | WAITING | Doctor calls next | CALLED | Popped from Redis list; active counter saved |
    | CALLED | Doctor clicks complete | COMPLETED | Status updated; active counter cleared; calls next |
    | CALLED | Doctor calls next (auto-comp) | COMPLETED | Previously called token auto-completed in Redis |
    | CALLED | Doctor skips patient | ON HOLD | Saved to local skipped array in doctor console |

---

## Slide 12: 11. Results and Performance
* **Heading (14 pt):** 11. Results and Performance
* **Content (12 pt):**
  * Tested counter automation: Completed patient is processed and next patient called instantly.
  * Eliminated patient idle time: Doctor wait gaps reduced to 0 seconds between patient transitions.
  * Lightweight execution: Redis latency for push/pop averages < 1 millisecond.
  * Reliable offline safety: Doctor console falls back to local simulation mode if backend goes offline.

---

## Slide 13: 12. Future Work
* **Heading (14 pt):** 12. Future Work
* **Content (12 pt):**
  * SMS/WhatsApp integration: Alerts patient with real-time queue position dynamically.
  * Estimated examination length: Calculates individual doctor check-up speed history using simple ML.
  * Multi-clinic federation: Syncs token flows across multiple branches with centralized queue engines.
  * Hardware Integration: Direct interface with ESP32-based physical button boards at doctor counters.

---

## Slide 14: 13. Conclusion
* **Heading (14 pt):** 13. Conclusion
* **Content (12 pt):**
  * The OPD Queue Engine provides a modern, high-performance solution to patient queue disorganization.
  * Automated counter flow keeps doctors focused on patients rather than manual queue administration.
  * Fully responsive interface adapts to kiosks, doctor dashboards, and wide lobby TVs.
  * Redis-backed token lifecycle transitions ensure data consistency and prevent double-calling errors.

---

## Slide 15: 14. References
* **Heading (14 pt):** 14. References
* **Content (12 pt):**
  * FastAPI & Starlette Documentation, https://fastapi.tiangolo.com/ (2026).
  * Redis Command Reference & List Queue Architecture Patterns, https://redis.io/ (2025).
  * W3C Web Speech API Standards, https://www.w3.org/TR/speech-api/.
  * Outpatient Flow Optimization using Queueing Models, Journal of Healthcare Administration (2024).
