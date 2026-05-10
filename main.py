import os
import time
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from exa_py import Exa
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
EXA_API_KEY = os.getenv("EXA_API_KEY")

exa_client = Exa(api_key=EXA_API_KEY)

llm = LLM(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)


# ============================================================
# TOOLS
# ============================================================

@tool("Fetch Cybersecurity Threats")
def fetch_cybersecurity_threats_tool(query: str) -> str:
    """Search for latest cybersecurity threats and malware campaigns. Input is a search query string."""
    try:
        result = exa_client.search_and_contents(query, summary=True)
    except Exception as e:
        return f"Exa search failed: {str(e)}"

    if not result.results:
        return "No cybersecurity threats found."

    items = []
    for item in result.results[:3]:
        summary = getattr(item, "summary", "") or ""
        summary = summary[:300]
        items.append(
            f"Title: {getattr(item, 'title', 'N/A')}\n"
            f"Date: {getattr(item, 'published_date', 'Unknown')}\n"
            f"Summary: {summary}"
        )
    return "\n---\n".join(items)


@tool("Fetch Latest CVEs")
def fetch_latest_cves_tool(query: str) -> str:
    """Search for latest CVEs and security vulnerabilities. Input is a search query string."""
    try:
        result = exa_client.search_and_contents(query, summary=True)
    except Exception as e:
        return f"Exa search failed: {str(e)}"

    if not result.results:
        return "No CVEs found."

    items = []
    for item in result.results[:3]:
        summary = getattr(item, "summary", "") or ""
        summary = summary[:300]
        items.append(
            f"Title: {getattr(item, 'title', 'N/A')}\n"
            f"Date: {getattr(item, 'published_date', 'Unknown')}\n"
            f"Summary: {summary}"
        )
    return "\n---\n".join(items)


# ============================================================
# AGENTS
# ============================================================

threat_analyst = Agent(
    role="Threat Intelligence Analyst",
    goal="Gather and analyze real-time cybersecurity threat intelligence using available tools.",
    backstory="Expert analyst tracking malware campaigns, nation-state attacks, and cyberattacks.",
    verbose=True,
    allow_delegation=False,
    llm=llm,
    max_iter=3,
    memory=False,
    tools=[fetch_cybersecurity_threats_tool],
)

vulnerability_researcher = Agent(
    role="Vulnerability Researcher",
    goal="Identify and analyze the latest CVEs and software vulnerabilities.",
    backstory="Cybersecurity researcher specializing in CVE analysis and patch management.",
    verbose=True,
    allow_delegation=False,
    llm=llm,
    max_iter=3,
    memory=False,
    tools=[fetch_latest_cves_tool],
)

incident_response_advisor = Agent(
    role="Incident Response Advisor",
    goal="Produce a comprehensive mitigation and incident response plan.",
    backstory="Cybersecurity defense specialist focused on incident response and threat containment.",
    verbose=True,
    allow_delegation=False,
    llm=llm,
    max_iter=3,
    memory=False,
)

cybersecurity_writer = Agent(
    role="Cybersecurity Report Writer",
    goal="Write a detailed, comprehensive SOC technical report from collected intelligence.",
    backstory="Senior security analyst writing in-depth SOC-level threat intelligence reports.",
    verbose=True,
    allow_delegation=False,
    llm=llm,
    max_iter=5,
    memory=False,
)

executive_writer = Agent(
    role="Executive Report Writer",
    goal="Write a detailed C-suite brief covering full business risk from cyber threats.",
    backstory="CISO-level communicator translating technical threats into board-level business risk language.",
    verbose=True,
    allow_delegation=False,
    llm=llm,
    max_iter=5,
    memory=False,
)


# ============================================================
# TASKS
# ============================================================

threat_analysis_task = Task(
    description=(
        "Use 'Fetch Cybersecurity Threats' to search 'latest cybersecurity threats 2026'. "
        "Analyze all results thoroughly. For each threat provide: threat name, threat actor (if known), "
        "attack vector, targeted industries, geographic spread, technical indicators, and business impact. "
        "Cover at least 3 threats in detail."
    ),
    expected_output=(
        "A detailed structured report of 3 cybersecurity threats. Each entry must include: "
        "threat name, description (3-4 sentences), attack method, targeted sectors, "
        "severity level (Critical/High/Medium), and potential business impact."
    ),
    agent=threat_analyst,
)

vulnerability_research_task = Task(
    description=(
        "Use 'Fetch Latest CVEs' to search 'latest critical CVEs vulnerabilities 2026'. "
        "For each CVE provide full analysis including: CVE ID, affected vendor and product, "
        "CVSS score, attack vector, privileges required, patch availability, and exploitation status. "
        "Cover at least 3 CVEs in detail."
    ),
    expected_output=(
        "A detailed structured report of 3 CVEs. Each entry must include: "
        "CVE ID, affected software/vendor, CVSS score, vulnerability description (3-4 sentences), "
        "exploitation status (active/PoC/none), patch status, and recommended remediation steps."
    ),
    agent=vulnerability_researcher,
)

incident_response_task = Task(
    description=(
        "Using the threats and CVEs identified by prior agents, produce a comprehensive incident "
        "response and mitigation plan. Cover: immediate containment steps, short-term hardening actions, "
        "long-term strategic recommendations, tools and technologies to deploy, and team responsibilities. "
        "Address each identified threat and CVE individually."
    ),
    expected_output=(
        "A full incident response plan with 3 sections:\n"
        "1) Immediate Actions (within 24 hrs) — at least 5 steps, "
        "2) Short-Term Hardening (1-4 weeks) — at least 5 steps, "
        "3) Long-Term Strategy (1-3 months) — at least 4 recommendations. "
        "Each step must be 2-3 sentences explaining what to do and why."
    ),
    agent=incident_response_advisor,
    context=[threat_analysis_task, vulnerability_research_task],
)

write_threat_report_task = Task(
    description=(
        "Write a comprehensive SOC technical threat intelligence report consolidating all findings. "
        "Structure it professionally with an executive summary, detailed threat analysis section, "
        "vulnerability analysis section, attack chain analysis, IOCs (indicators of compromise) if available, "
        "and a full mitigation roadmap. This report is for the security operations team."
    ),
    expected_output=(
        "A full SOC technical report with these sections:\n"
        "1. Executive Summary (1 paragraph)\n"
        "2. Threat Landscape Overview (2-3 paragraphs)\n"
        "3. Detailed Threat Analysis (each threat: 1 paragraph)\n"
        "4. Vulnerability Analysis (each CVE: 1 paragraph)\n"
        "5. Attack Chain & TTPs (MITRE ATT&CK mapping if applicable)\n"
        "6. Indicators of Compromise (IPs, hashes, domains if available)\n"
        "7. Mitigation Roadmap (immediate, short-term, long-term)\n"
        "8. Conclusion\n"
        "Minimum 500 words. Use headers and bullets where appropriate."
    ),
    agent=cybersecurity_writer,
    context=[threat_analysis_task, vulnerability_research_task, incident_response_task],
)

executive_report_task = Task(
    description=(
        "Write a detailed C-suite executive brief that communicates the full business risk picture. "
        "Translate all technical findings into financial, operational, and reputational risk language. "
        "Quantify risks where possible (e.g. average breach cost, downtime estimates, regulatory fines). "
        "Make leadership understand urgency and what decisions they must make this week."
    ),
    expected_output=(
        "A polished executive brief with these 5 sections, each 2-3 paragraphs long:\n"
        "1. SITUATION SUMMARY — what is happening and why it matters now\n"
        "2. BUSINESS IMPACT — financial exposure, operational risk, reputational damage with estimates\n"
        "3. REGULATORY & COMPLIANCE RISK — specific regulations at risk (GDPR, HIPAA, SOC2, PCI-DSS) "
        "and potential fine ranges\n"
        "4. WHAT WE ARE DOING — current response actions explained in plain business terms\n"
        "5. DECISION REQUIRED — specific budget approvals, policy changes, or escalations needed\n"
        "Minimum 400 words. No technical jargon. Professional WSJ op-ed tone."
    ),
    agent=executive_writer,
    context=[threat_analysis_task, vulnerability_research_task, incident_response_task],
)


# ============================================================
# CREW
# ============================================================

def rate_limit_step(step_output):
    time.sleep(5)


crew = Crew(
    agents=[
        threat_analyst,
        vulnerability_researcher,
        incident_response_advisor,
        cybersecurity_writer,
        executive_writer,
    ],
    tasks=[
        threat_analysis_task,
        vulnerability_research_task,
        incident_response_task,
        write_threat_report_task,
        executive_report_task,
    ],
    verbose=True,
    process=Process.sequential,
    full_output=True,
    share_crew=False,
    manager_llm=llm,
    max_iter=15,
    step_callback=rate_limit_step,
)

results = crew.kickoff()


# ============================================================
# OUTPUT
# ============================================================

def safe_get_output(tasks_output, index, label):
    try:
        content = tasks_output[index].raw
        if not content or not content.strip():
            return f"_{label} output was empty._"
        return content
    except (IndexError, AttributeError):
        return f"_{label} output unavailable._"


executive_report = safe_get_output(results.tasks_output, -1, "Executive Brief")
technical_report = safe_get_output(results.tasks_output, -2, "Technical Report")

from IPython.display import display, Markdown

display(Markdown("---"))
display(Markdown("# 📊 EXECUTIVE BRIEF (C-Suite)"))
display(Markdown(executive_report))

display(Markdown("---"))
display(Markdown("# 🔧 TECHNICAL REPORT (SOC Team)"))
display(Markdown(technical_report))

with open("executive_brief.md", "w") as f:
    f.write(f"# Executive Cybersecurity Brief\n\n{executive_report}")

with open("technical_report.md", "w") as f:
    f.write(f"# SOC Technical Report\n\n{technical_report}")

print("✅ Reports saved: executive_brief.md | technical_report.md")

from markdown_pdf import MarkdownPdf, Section

def md_to_pdf(title: str, md_content: str, filename: str):
    pdf = MarkdownPdf(toc_level=2)
    pdf.add_section(Section(f"# {title}\n\n{md_content}"))
    pdf.save(filename)

md_to_pdf("Executive Cybersecurity Brief", executive_report, "executive_brief.pdf")
md_to_pdf("SOC Technical Report", technical_report, "technical_report.pdf")