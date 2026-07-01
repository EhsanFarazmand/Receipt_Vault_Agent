The following tables of contents are extracted from the provided resources, highlighting the structural organization and key concepts of the "Spec-Driven Development in the Age of Vibe Coding" series.

### **1. Agent Skills (Day 3)**
This resource focuses on equipping agents with procedural memory through modular "skills" to prevent context rot and ensure portability.

**Table of Contents:**
*   **Introduction**
*   **What is an Agent Skill (and How to Build Your First One):** Skill Anatomy & Progressive Disclosure; Path A (Translating existing knowledge); Path B (Crystallizing agent actions); Skill installation
*   **Why did Agent Skills become so popular, so fast?** Use cases for chatbots, coding, and enterprise
*   **Evaluating Skills:** The Evaluation Toolkit; Trigger gates; Output quality and tool trajectories; Token budgets
*   **From Prototype to Production:** Agent runtimes; Skills as units of improvement; Context overflow failure modes
*   **On Meta-Skills and Self-Improving Skills**
*   **Composing and Packaging Skills:** DAG Orchestration; Capability Profiles; Skill Taxonomy
*   **How to Decide Among the Hundreds of Skills That Exist**
*   **Conclusion**
*   **Appendix A – The Practical Cheatsheet:** SKILL.md templates, folder structures, and quality rules
*   **Appendix B – Case Study:** Vertical Skills in Retail

**Important Topics:**
*   **Skill Anatomy:** The standard structure using `SKILL.md` and progressive disclosure (metadata > body > resources) to save token costs.
*   **Evaluation Tiers:** Graduation of skills through Read-Only, Draft-Only, and Action-Allowed tiers based on rigorous testing.
*   **Context Management:** Solving "context rot" by loading specialist instructions exclusively on demand.

---

### **2. Agent Tools & Interoperability (Day 2)**
This paper explores standardized protocols that allow isolated agents to function as a modular, interoperable workforce.

**Table of Contents:**
*   **Introduction**
*   **The Vibe Coder’s View of MCP:** Discovery, Configuration, and Connection
*   **Bypassing the NxM Prototyping Problem**
*   **Debugging Issues with MCP Servers & Best Practices**
*   **Agent-to-Agent (A2A) Interoperability:** Evolution of architectures; Bounded vs. Unbounded domains; The GOTO problem
*   **Building the Virtual Workforce:** The Agent Card; Public vs. Private registries
*   **Implementing A2A Protocols:** Exposing and connecting remote agents
*   **The Extensibility Layer:** A2A as the foundation for UI and Commerce; Monetization
*   **Agent-to-UI (A2UI) Interoperability:** Generative UI; Secure implementations; Interactive Artifacts and The Canvas
*   **Agents and Commerce (AP2 and UCP):** Autonomous procurement; Universal Commerce and Agent Payments protocols

**Important Topics:**
*   **Model Context Protocol (MCP):** Acts as the "USB-C" for agent harnesses, standardizing connections to tools and data.
*   **Agent-to-Agent (A2A):** A "Factory Radio" protocol that allows specialized agents to negotiate and delegate tasks across network boundaries.
*   **Autonomous Commerce:** Protocols like **UCP** (for universal store interaction) and **AP2** (for secure, rule-based payments).

---

### **3. Spec-Driven Production Grade Development (Day 5)**
This guide defines the transition from rapid "vibe" prototypes to reliable production systems using rigorous specifications.

**Table of Contents:**
*   **Introduction**
*   **Spec-Driven Development (SDD):** Creating good specifications; Format choices (Markdown + YAML); Behavior Driven Development (BDD)
*   **Where do the instructions live?** Chat interfaces, spec folders, agent skills, and system prompts
*   **Different Prompts for Different Use Cases:** Project vs. Feature generation; Bug fixing; Documentation and Data Engineering
*   **Team Culture & Process Evolution:** Code reviews; Sustainability and approval fatigue
*   **Zero-Trust Development:** Implementing guardrails; Sandboxing; Human-in-the-Loop
*   **AI Generated Test Coverage & Evaluation**
*   **Policy Server:** Structural and semantic gating
*   **Context Hygiene & Prompt Sanitization**

**Important Topics:**
*   **Behavior-Driven Development (BDD):** Using Gherkin syntax (Scenario/Given/When/Then) to eliminate guessing and enforce precise logic.
*   **Zero-Trust Safety:** Using isolated **sandboxes** and **Policy Servers** to intercept and validate tool calls before execution.
*   **Context Hygiene:** Dynamic sanitization of prompts to prevent PII leaks and "Context Hallucination".

---

### **4. The New SDLC With Vibe Coding (Day 1)**
This resource outlines the paradigm shift from writing raw syntax to expressing high-level intent in the Software Development Life Cycle.

**Table of Contents:**
*   **Introduction**
*   **The shift from syntax to intent:** AI Agents refresher; Vibe coding defined; The spectrum to agentic engineering
*   **Context engineering:** The six types of context; Static vs. Dynamic context
*   **The new software development life cycle:** How AI transforms Requirements, Design, Implementation, Testing, and Maintenance
*   **The Factory Model:** Building the system that builds software
*   **Harness Engineering:** What surrounds the model
*   **The developer's evolving role:** Conductors vs. Orchestrators
*   **The 80% problem**
*   **Coding agents in practice:** Editor, Terminal, and Background agents
*   **Vibe Coding Production-ready Agents:** The Agents CLI workflow
*   **The Economics of AI Development:** Vibe coding debt vs. Agentic engineering investment; Token economics

**Important Topics:**
*   **The Harness Equation:** Agent = Model + Harness. The harness provides the state, tools, and constraints that make a model useful.
*   **The Orchestrator Role:** Shifting from hands-on coding (Conductor) to high-level, asynchronous task delegation (Orchestrator).
*   **Context Engineering:** Strategically managing the agent's "Working Memory" to improve accuracy and optimize token spend.

---

### **5. Vibe Coding Agent Security and Evaluation (Day 4)**
This paper provides a framework for securing non-deterministic agents and measuring their alignment with developer intent.

**Table of Contents:**
*   **Introduction**
*   **The Foundation: The 7-Pillar Agent Security Architecture**
*   **Sandboxes and Supply Chain Defence:** Ephemeral states; Mitigating hallucinated "slopsquatting" packages
*   **Securing Application Logic:** Application vulnerabilities; MCP spoofing defense
*   **Identity, Trust & High-Stakes Actions:** The Confused Deputy problem; JIT downscoping; The "Vibe Diff"
*   **Red, Blue, and Green Security Teaming:** Agent attackers, defenders, and fixers
*   **Observability:** Tracing the "Vibe Trajectory"; Intent drift and trust decay
*   **Evaluation:** Why vibe coding evaluation is different; What and How to evaluate

**Important Topics:**
*   **7-Pillar Security Architecture:** A defense-in-depth model covering Infrastructure, Data, Model, App/Runtime, IAM, Observability, and Governance.
*   **Slopsquatting:** Securing the supply chain against attackers who publish malicious packages with names that LLMs are known to hallucinate.
*   **The "Vibe Diff":** Translating complex generated code back into plain language for human approval before high-stakes actions.