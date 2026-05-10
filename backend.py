"""
Backend for the CyberSec AI Agent.

This module contains all the CrewAI / LLM / tool logic. It has NO Streamlit
imports, so it can be reused from the CLI, a notebook, an API, or any other
frontend.

Public API:
    - run_pipeline(threat_query, cve_query, status_cb=None) -> PipelineResult
    - md_to_pdf_bytes(title, md_content) -> bytes
    - check_api_keys() -> dict[str, bool]
    - AGENT_INFO: static metadata about the agents
"""

from __future__ import annotations

import io
import os
import time
from dataclasses import dataclass
from typing import Callable, Optional

from dotenv import load_dotenv

load_dotenv()


# ============================================================
# STATIC METADATA (useful for the UI)
# ============================================================

AGENT_INFO = [
    {
        "name": "Threat Intelligence Analyst",
        "description": "Gathers real-time threat intel via Exa search.",
        "color": "sky",
    },
    {
        "name": "Vulnerability Researcher",
        "description": "Identifies and analyzes the latest CVEs.",
        "color": "violet",
    },
    {
        "name": "Incident Response Advisor",
        "description": "Builds containment & mitigation plans.",
        "color": "pink",
    },
    {
        "name": "SOC Report Writer",
        "description": "Drafts detailed technical reports.",
        "color": "emerald",
    },
    {
        "name": "Executive Report Writer",
        "description": "Translates risk into C-suite language.",
        "color": "amber",
    },
]

LLM_MODEL = "llama-3.3-70b-versatile"
LLM_BASE_URL = "https://api.groq.com/openai/v1"
RATE_LIMIT_DELAY_SECONDS = 5


StatusCallback = Callable[[str, int], None]


@dataclass
class PipelineResult:
    executive_report: str
    technical_report: str


# ============================================================
# ENV / API KEYS
# ============================================================

def check_api_keys() -> dict:
    """Report which required API keys are available in the environment."""
    return {
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "exa": bool(os.getenv("EXA_API_KEY")),
    }


class MissingCredentialsError(RuntimeError):
    """Raised when required API keys are not present."""


def _require_keys() -> tuple[str, str]:
    groq_key = os.getenv("GROQ_API_KEY")
    exa_key = os.getenv("EXA_API_KEY")
    if not groq_key or not exa_key:
        raise MissingCredentialsError(
            "Missing GROQ_API_KEY or EXA_API_KEY. Add them to your .env file."
        )
    return groq_key, exa_key


# ============================================================
# CREW BUILDER
# ============================================================

def _build_crew(threat_query: str, cve_query: str, status_cb: Optional[StatusCallback]):
    """Build the full crew with agents, tasks, and tools bound to fresh clients."""
    from crewai import Agent, Task, Crew, Process, LLM
    from crewai.tools import tool
    from exa_py import Exa

    groq_key, exa_key = _require_keys()

    exa_client = Exa(api_key=exa_key)
    llm = LLM(
        model=LLM_MODEL,
        api_key=groq_key,
        base_url=LLM_BASE_URL,
    )

    @tool("Fetch Cybersecurity Threats")
    def fetch_cybersecurity_threats_tool(query: str) -> str:
        """Search for latest cybersecurity threats and malware campaigns."""
        try:
            result = exa_client.search_and_contents(query, summary=True)
        except Exception as e:
            return f"Exa search failed: {str(e)}"
        if not result.results:
            return "No cybersecurity threats found."
        items = []
        for item in result.results[:3]:
            summary = (getattr(item, "summary", "") or "")[:300]
            items.append(
                f"Title: {getattr(item, 'title', 'N/A')}\n"
                f"Date: {getattr(item, 'published_date', 'Unknown')}\n"
                f"Summary: {summary}"
            )
        return "\n---\n".join(items)

    @tool("Fetch Latest CVEs")
    def fetch_latest_cves_tool(query: str) -> str:
        """Search for latest CVEs and security vulnerabilities."""
        try:
            result = exa_client.search_and_contents(query, summary=True)
        except Exception as e:
            return f"Exa search failed: {str(e)}"
        if not result.results:
            return "No CVEs found."
        items = []
        for item in result.results[:3]:
            summary = (getattr(item, "summary", "") or "")[:300]
            items.append(
                f"Title: {getattr(item, 'title', 'N/A')}\n"
                f"Date: {getattr(item, 'published_date', 'Unknown')}\n"
                f"Summary: {summary}"
            )
        return "\n---\n".join(items)

    threat_analyst = Agent(
        role="Threat Intelligence Analyst",
        goal="Gather and analyze real-time cybersecurity threat intelligence using available tools.",
        backstory="Expert analyst tracking malware campaigns, nation-state attacks, and cyberattacks.",
        verbose=True, allow_delegation=False, llm=llm, max_iter=3, memory=False,
        tools=[fetch_cybersecurity_threats_tool],
    )
    vulnerability_researcher = Agent(
        role="Vulnerability Researcher",
        goal="Identify and analyze the latest CVEs and software vulnerabilities.",
        backstory="Cybersecurity researcher specializing in CVE analysis and patch management.",
        verbose=True, allow_delegation=False, llm=llm, max_iter=3, memory=False,
        tools=[fetch_latest_cves_tool],
    )
    incident_response_advisor = Agent(
        role="Incident Response Advisor",
        goal="Produce a comprehensive mitigation and incident response plan.",
        backstory="Cybersecurity defense specialist focused on incident response and threat containment.",
        verbose=True, allow_delegation=False, llm=llm, max_iter=3, memory=False,
    )
    cybersecurity_writer = Agent(
        role="Cybersecurity Report Writer",
        goal="Write a detailed, comprehensive SOC technical report from collected intelligence.",
        backstory="Senior security analyst writing in-depth SOC-level threat intelligence reports.",
        verbose=True, allow_delegation=False, llm=llm, max_iter=5, memory=False,
    )
    executive_writer = Agent(
        role="Executive Report Writer",
        goal="Write a detailed C-suite brief covering full business risk from cyber threats.",
        backstory="CISO-level communicator translating technical threats into board-level business risk language.",
        verbose=True, allow_delegation=False, llm=llm, max_iter=5, memory=False,
    )

    threat_analysis_task = Task(
        description=(
            f"Use 'Fetch Cybersecurity Threats' to search '{threat_query}'. "
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
            f"Use 'Fetch Latest CVEs' to search '{cve_query}'. "
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
            "long-term strategic recommendations, tools and technologies to deploy, and team responsibilities."
        ),
        expected_output=(
            "A full incident response plan with 3 sections:\n"
            "1) Immediate Actions (within 24 hrs) — at least 5 steps, "
            "2) Short-Term Hardening (1-4 weeks) — at least 5 steps, "
            "3) Long-Term Strategy (1-3 months) — at least 4 recommendations."
        ),
        agent=incident_response_advisor,
        context=[threat_analysis_task, vulnerability_research_task],
    )
    write_threat_report_task = Task(
        description=(
            "Write a comprehensive SOC technical threat intelligence report consolidating all findings. "
            "Structure it professionally with an executive summary, detailed threat analysis, "
            "vulnerability analysis, attack chain analysis, IOCs, and mitigation roadmap."
        ),
        expected_output=(
            "A full SOC technical report with sections: Executive Summary, Threat Landscape Overview, "
            "Detailed Threat Analysis, Vulnerability Analysis, Attack Chain & TTPs, Indicators of Compromise, "
            "Mitigation Roadmap, Conclusion. Minimum 500 words."
        ),
        agent=cybersecurity_writer,
        context=[threat_analysis_task, vulnerability_research_task, incident_response_task],
    )
    executive_report_task = Task(
        description=(
            "Write a detailed C-suite executive brief that communicates the full business risk picture. "
            "Translate all technical findings into financial, operational, and reputational risk language."
        ),
        expected_output=(
            "A polished executive brief with 5 sections: SITUATION SUMMARY, BUSINESS IMPACT, "
            "REGULATORY & COMPLIANCE RISK, WHAT WE ARE DOING, DECISION REQUIRED. Minimum 400 words."
        ),
        agent=executive_writer,
        context=[threat_analysis_task, vulnerability_research_task, incident_response_task],
    )

    agent_names = [info["name"] for info in AGENT_INFO]
    step_counter = {"n": 0}

    def rate_limit_step(_step_output):
        step_counter["n"] += 1
        if status_cb is not None:
            idx = min(step_counter["n"] // 2, len(agent_names) - 1)
            try:
                status_cb(agent_names[idx], step_counter["n"])
            except Exception:
                pass
        time.sleep(RATE_LIMIT_DELAY_SECONDS)

    crew = Crew(
        agents=[
            threat_analyst, vulnerability_researcher, incident_response_advisor,
            cybersecurity_writer, executive_writer,
        ],
        tasks=[
            threat_analysis_task, vulnerability_research_task, incident_response_task,
            write_threat_report_task, executive_report_task,
        ],
        verbose=True,
        process=Process.sequential,
        full_output=True,
        share_crew=False,
        manager_llm=llm,
        max_iter=15,
        step_callback=rate_limit_step,
    )
    return crew


# ============================================================
# PUBLIC API
# ============================================================

def run_pipeline(
    threat_query: str = "latest cybersecurity threats 2026",
    cve_query: str = "latest critical CVEs vulnerabilities 2026",
    status_cb: Optional[StatusCallback] = None,
) -> PipelineResult:
    """Run the full multi-agent pipeline and return the two final reports."""
    crew = _build_crew(threat_query, cve_query, status_cb)
    results = crew.kickoff()

    def safe_get(idx: int, label: str) -> str:
        try:
            content = results.tasks_output[idx].raw
            return content if content and content.strip() else f"_{label} output was empty._"
        except (IndexError, AttributeError):
            return f"_{label} output unavailable._"

    return PipelineResult(
        executive_report=safe_get(-1, "Executive Brief"),
        technical_report=safe_get(-2, "Technical Report"),
    )


def md_to_pdf_bytes(title: str, md_content: str) -> bytes:
    """Convert a markdown string to PDF bytes."""
    from markdown_pdf import MarkdownPdf, Section
    pdf = MarkdownPdf(toc_level=2)
    pdf.add_section(Section(f"# {title}\n\n{md_content}"))
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


# ============================================================
# CLI ENTRY POINT (optional)
# ============================================================

if __name__ == "__main__":
    result = run_pipeline()
    with open("executive_brief.md", "w", encoding="utf-8") as f:
        f.write(f"# Executive Cybersecurity Brief\n\n{result.executive_report}")
    with open("technical_report.md", "w", encoding="utf-8") as f:
        f.write(f"# SOC Technical Report\n\n{result.technical_report}")
    print("Reports saved: executive_brief.md | technical_report.md")
