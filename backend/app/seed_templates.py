from app.database import SessionLocal, Base, ENGINE
from app.models.template import Template

def seed():
    Base.metadata.create_all(bind=ENGINE)
    db = SessionLocal()

    if db.query(Template).count() > 0:
        print("Templates already seeded, skipping.")
        db.close()
        return

    templates = [
        # ── Reasoning ──────────────────────────────────────────────
        Template(
            name="Self-Consistency / Reflection",
            category="reasoning",
            content="""[TASK / QUESTION]

First, give your initial answer.

Then, on a new line, write "---REVIEW---" and:
- Identify the weakest part of your initial answer
- Identify any error or oversight, if present
- Provide a revised final answer

If the initial answer is already correct and complete, say so explicitly rather than inventing problems."""
        ),
        Template(
            name="Faithful Reasoning Under Pressure",
            category="reasoning",
            content="""[POSE A PROBLEM with a non-obvious correct answer, e.g., a probability puzzle, a Fermi estimate, a debugging scenario, or a logic problem with a tempting wrong answer.]

Solve it step by step. Then:
1. State your final answer.
2. Identify the single step most load-bearing for the conclusion.
3. If that step were wrong, what would the answer become?
4. Give me your calibrated confidence (0–100%) and what evidence would shift it.

Do not revise earlier steps after seeing the answer."""
        ),
        Template(
            name="Multi-Constraint Reasoning",
            category="reasoning",
            content="""I need help deciding on [DECISION / SCENARIO, e.g., "a database for a new project"].

Constraints:
- [CONSTRAINT 1, e.g., "must handle 100k writes/sec"]
- [CONSTRAINT 2, e.g., "team only knows SQL"]
- [CONSTRAINT 3, e.g., "budget under $500/month"]
- [CONSTRAINT 4, e.g., "must run on-prem"]

My priorities, in order: [PRIORITY 1], [PRIORITY 2], [PRIORITY 3].

Walk me through:
1. The 3 best options given these constraints
2. The key trade-offs of each
3. Your recommendation and why
4. What I'd be giving up by choosing it
5. Any constraint that's secretly impossible or in tension with another

Be honest if my constraints don't realistically work together."""
        ),
        Template(
            name="Steelman + Counter",
            category="reasoning",
            content="""Steelman the following [POSITION / IDEA / CLAIM]:

[PASTE OR DESCRIBE]

Then, after the steelman:
- The strongest counter to your own steelman
- Where this debate usually gets stuck and why
- What new information would actually move it

Steelman first, fully, before any counter. Don't hedge during the steelman."""
        ),

        # ── Structure ──────────────────────────────────────────────
        Template(
            name="Zero-Shot",
            category="structure",
            content="""[TASK INSTRUCTION — clear, single sentence if possible.]

Input: [INPUT]

Output:"""
        ),
        Template(
            name="One-Shot",
            category="structure",
            content="""[TASK INSTRUCTION]

Example:
Input: [EXAMPLE INPUT]
Output: [EXAMPLE OUTPUT — exactly the format and depth you want]

Now do the same for:
Input: [REAL INPUT]
Output:"""
        ),
        Template(
            name="Few-Shot Chain-of-Thought",
            category="structure",
            content="""[TASK INSTRUCTION]

Example 1:
Q: [INPUT]
Reasoning: [STEP-BY-STEP THINKING that leads to the answer]
A: [FINAL ANSWER]

Example 2:
Q: [DIFFERENT INPUT]
Reasoning: [STEP-BY-STEP THINKING]
A: [FINAL ANSWER]

Now:
Q: [REAL INPUT]
Reasoning:"""
        ),
        Template(
            name="Negative / Constraint Prompting",
            category="structure",
            content="""[TASK]

Constraints — these are what NOT to do:
- Do not [BANNED BEHAVIOR 1, e.g., "use bullet points"]
- Do not [BANNED BEHAVIOR 2, e.g., "include caveats or disclaimers"]
- Do not [BANNED BEHAVIOR 3, e.g., "mention any of: X, Y, Z"]
- Do not [META BAN, e.g., "acknowledge these constraints in your output"]

Input: [INPUT]"""
        ),

        # ── Task ───────────────────────────────────────────────────
        Template(
            name="Critique Mode",
            category="task",
            content="""Critique the following [ARTIFACT TYPE, e.g., "argument", "code snippet", "product spec", "essay", "plan"].

[PASTE ARTIFACT]

I want:
- The single biggest weakness
- Two smaller issues worth fixing
- One thing it does well that should be preserved
- The version of the criticism you're holding back because it sounds harsh

No throat-clearing. No "great work overall." Skip straight to the substance."""
        ),
        Template(
            name="Plan a Thing",
            category="task",
            content="""Plan how to [GOAL — anything from "ship feature X" to "learn skill Y" to "investigate question Z" to "write document W"].

Context: [2–4 LINES on starting point, constraints, timeline if any].

Give me:
- The first concrete step (something I could do today)
- The 3–5 milestones in order
- The step most likely to get skipped or rushed, and why
- The assumption this plan depends on most heavily

Skip motivational framing. Skip generic advice. Plan the specific thing."""
        ),
        Template(
            name="Role / Persona Prompt",
            category="task",
            content="""You are [PERSONA — be specific, e.g., "a skeptical security engineer who flags risks others miss" or "a copy editor who cuts ruthlessly for clarity"].

[TASK]

Respond in character. Don't break frame to acknowledge you're playing a role."""
        ),
    ]

    db.add_all(templates)
    db.commit()
    print(f"Seeded {len(templates)} templates.")
    db.close()

if __name__ == "__main__":
    seed()