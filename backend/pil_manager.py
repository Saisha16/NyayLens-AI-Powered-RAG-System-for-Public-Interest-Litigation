"""
PIL Storage and Management Module
Handles storing, retrieving, and updating PIL drafts before PDF generation
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class PILDraft:
    """Represents a PIL draft with metadata"""
    id: str
    article_index: int
    news_title: str
    created_at: str
    updated_at: str
    severity_score: float
    priority_level: str
    entities: list
    legal_sources: list
    
    # Main PIL sections (editable)
    facts_of_case: str
    fundamental_rights: list
    directive_principles: list
    case_precedents: list
    prayer_relief: str
    
    # Metadata
    topics: list = None
    source_url: str = None
    
    def to_dict(self):
        return asdict(self)


class PILManager:
    """Manages PIL draft lifecycle"""
    
    STORAGE_DIR = "data/pil_drafts"
    CURRENT_PIL_FILE = "data/current_pil.json"
    
    @staticmethod
    def initialize():
        """Create storage directory if needed"""
        os.makedirs(PILManager.STORAGE_DIR, exist_ok=True)
    
    @staticmethod
    def create_draft(pil_text: str, article_index: int, metadata: Dict[str, Any]) -> PILDraft:
        """
        Create a new PIL draft from generated content
        
        Args:
            pil_text: Full PIL text from generator
            article_index: Index of source article
            metadata: Dict with news_title, severity_score, entities, legal_sources, topics
        
        Returns:
            PILDraft object
        """
        # Parse PIL sections from text
        sections = PILManager._parse_pil_sections(pil_text)
        print(f"DEBUG: Parsed sections - facts: {len(sections.get('facts', ''))}, rights: {len(sections.get('fundamental_rights', []))}, prayer: {len(sections.get('prayer', ''))}")
        
        # Create unique ID based on article index and timestamp
        draft_id = hashlib.md5(
            f"{article_index}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        draft = PILDraft(
            id=draft_id,
            article_index=article_index,
            news_title=metadata.get("news_title", ""),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            severity_score=metadata.get("severity_score", 0.0),
            priority_level=metadata.get("priority_level", "MEDIUM"),
            entities=metadata.get("entities_detected", []),
            legal_sources=metadata.get("legal_sources_used", []),
            facts_of_case=sections.get("facts", ""),
            fundamental_rights=sections.get("fundamental_rights", []),
            directive_principles=sections.get("directive_principles", []),
            case_precedents=sections.get("case_precedents", []),
            prayer_relief=sections.get("prayer", ""),
            topics=metadata.get("topics", []),
            source_url=metadata.get("source", "")
        )

        # Normalize and save to file
        draft, changed = PILManager._split_case_precedents_from_directives(draft)
        if changed:
            PILManager.save_draft(draft)
        else:
            PILManager.save_draft(draft)
        
        return draft
    
    @staticmethod
    def save_draft(draft: PILDraft) -> bool:
        """Save draft to disk"""
        try:
            PILManager.initialize()
            
            # Normalize draft before persisting
            draft, _ = PILManager._split_case_precedents_from_directives(draft)

            # Update timestamp
            draft.updated_at = datetime.now().isoformat()
            
            # Save to individual file
            draft_file = os.path.join(PILManager.STORAGE_DIR, f"{draft.id}.json")
            with open(draft_file, "w", encoding="utf-8") as f:
                json.dump(draft.to_dict(), f, indent=2, ensure_ascii=False)
            
            # Also save as current PIL for quick access
            with open(PILManager.CURRENT_PIL_FILE, "w", encoding="utf-8") as f:
                json.dump(draft.to_dict(), f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error saving draft: {e}")
            return False
    
    @staticmethod
    def get_current_draft() -> Optional[PILDraft]:
        """Get the most recently generated PIL draft"""
        try:
            if not os.path.exists(PILManager.CURRENT_PIL_FILE):
                return None
            
            with open(PILManager.CURRENT_PIL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            draft = PILDraft(**data)
            draft, changed = PILManager._split_case_precedents_from_directives(draft)
            # Persist normalization so downstream APIs (view/download) get updated fields
            if changed:
                PILManager.save_draft(draft)
            return draft
        except Exception as e:
            print(f"Error loading current draft: {e}")
            return None
    
    @staticmethod
    def get_draft(draft_id: str) -> Optional[PILDraft]:
        """Get a specific draft by ID"""
        try:
            draft_file = os.path.join(PILManager.STORAGE_DIR, f"{draft_id}.json")
            if not os.path.exists(draft_file):
                return None
            
            with open(draft_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            draft = PILDraft(**data)
            draft, changed = PILManager._split_case_precedents_from_directives(draft)
            if changed:
                PILManager.save_draft(draft)
            return draft
        except Exception as e:
            print(f"Error loading draft {draft_id}: {e}")
            return None

    @staticmethod
    def _split_case_precedents_from_directives(draft: PILDraft) -> tuple[PILDraft, bool]:
        """If case precedents are embedded inside directive principles, split them out.

        Returns (draft, changed)
        """
        try:
            if not draft:
                return draft, False
            
            principles = draft.directive_principles or []
            marker_idx = -1
            
            # Find marker in directive principles
            for idx, item in enumerate(principles):
                text = (item or "").lower()
                if "applicable statutory provisions" in text or "relevant case precedents" in text:
                    marker_idx = idx
                    break
            
            # Extract case precedents after marker
            if marker_idx != -1:
                extracted_precedents = [p for p in principles[marker_idx + 1:] if p and p.strip()]
                # Always replace if we found marker, even if case_precedents not empty
                # This ensures we always keep the extracted ones
                if extracted_precedents or not draft.case_precedents:
                    draft.case_precedents = extracted_precedents
                    draft.directive_principles = principles[:marker_idx]
                    return draft, True
            
            return draft, False
        except Exception as e:
            print(f"Error splitting case precedents: {e}")
            return draft, False
    
    @staticmethod
    def update_draft(draft_id: str, updates: Dict[str, Any]) -> Optional[PILDraft]:
        """
        Update specific fields of a draft
        
        Args:
            draft_id: ID of draft to update
            updates: Dict of fields to update (facts_of_case, fundamental_rights, etc.)
        
        Returns:
            Updated PILDraft or None if failed
        """
        draft = PILManager.get_draft(draft_id)
        if not draft:
            return None
        
        # Update allowed fields
        allowed_fields = [
            'facts_of_case',
            'fundamental_rights',
            'directive_principles',
            'case_precedents',
            'prayer_relief'
        ]
        
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(draft, field, value)
        
        PILManager.save_draft(draft)
        return draft
    
    @staticmethod
    def reconstruct_pil_text(draft: PILDraft) -> str:
        """Reconstruct full PIL text from draft (PDF-friendly, clean separators)."""

        # Elegant separator for professional appearance
        sep = "═" * 80
        subsep = "─" * 80

        lines = [
            sep,
            "IN THE HON'BLE SUPREME COURT OF INDIA",
            "(ORIGINAL CIVIL JURISDICTION)",
            sep,
            "",
            "PUBLIC INTEREST LITIGATION UNDER ARTICLE 32",
            "OF THE CONSTITUTION OF INDIA",
            "",
            f"Date of Filing: {datetime.fromisoformat(draft.updated_at).strftime('%B %d, %Y')}",
            "",
            subsep,
            "",
            "PETITIONER:",
            "",
            "    A Public-Spirited Citizen/Organization acting in Public Interest",
            "    (Name and address to be furnished)",
            "",
            "                                    ...Petitioner",
            "",
            "                                  VERSUS",
            "",
            "RESPONDENTS:",
            "",
            "    1. Union of India",
            "       Through the Secretary, Ministry of [Relevant Ministry]",
            "       Government of India, New Delhi",
            "",
            "    2. State of [State Name]",
            "       Through the Chief Secretary",
            "       State Government Secretariat",
            "",
            "    3. [Other Concerned Authorities as applicable]",
            "",
            "                                    ...Respondents",
            "",
            sep,
            "",
            "SUBJECT MATTER OF PUBLIC INTEREST LITIGATION",
            "",
            f"Issue: {draft.news_title}",
            "",
            f"Severity Assessment: {draft.priority_level} (Score: {draft.severity_score:.2f})",
            f"Category: {', '.join(draft.topics) if draft.topics else 'General Public Interest'}",
            "",
            sep,
            "",
            "FACTS OF THE CASE",
            "",
            draft.facts_of_case.strip() if draft.facts_of_case else "[Facts to be supplied]",
            "",
            ("Parties/Entities Involved: " + ", ".join(draft.entities)) if draft.entities else "",
            "",
            sep,
            "",
            "GROUNDS FOR FILING THIS PETITION",
            "",
            "A. VIOLATION OF FUNDAMENTAL RIGHTS:",
            "",
        ]

        if draft.fundamental_rights:
            for i, right in enumerate(draft.fundamental_rights, 1):
                lines.append(f"   {i}. {right}")
                lines.append("")
        else:
            lines.append("   1. Article 21 - Right to Life and Personal Liberty")
            lines.append("      (The right to live with human dignity, encompassing all aspects")
            lines.append("       necessary for a meaningful existence)")
            lines.append("")

        lines.extend([
            "B. VIOLATION OF DIRECTIVE PRINCIPLES OF STATE POLICY:",
            "",
        ])
        if draft.directive_principles:
            for i, principle in enumerate(draft.directive_principles, 1):
                lines.append(f"   {i}. {principle}")
                lines.append("")
        else:
            lines.append("   1. The State has failed to fulfill its constitutional obligations")
            lines.append("      under Part IV of the Constitution.")
            lines.append("")

        lines.extend([
            "C. RELEVANT CASE PRECEDENTS:",
            "",
        ])
        if draft.case_precedents:
            for i, case in enumerate(draft.case_precedents, 1):
                lines.append(f"   {i}. {case}")
                lines.append("")
        else:
            lines.append("   [Case precedents to be supplied - relevant Supreme Court")
            lines.append("    and High Court judgments establishing similar violations]")
            lines.append("")

        lines.extend([
            sep,
            "",
            "PRAYER FOR RELIEF",
            "",
            "It is most respectfully prayed that this Hon'ble Court may be pleased to:",
            "",
        ])
        
        if draft.prayer_relief.strip():
            # If prayer exists, use it
            prayer_lines = draft.prayer_relief.strip().split('\n')
            for line in prayer_lines:
                lines.append(line)
        else:
            # Default prayer structure
            lines.extend([
                "a) Issue appropriate writs, orders, or directions in the nature of mandamus",
                "   or any other writ deemed fit;",
                "",
                "b) Direct the Respondents to take immediate and effective action to remedy",
                "   the violations highlighted in this petition;",
                "",
                "c) Pass such other and further orders as this Hon'ble Court may deem fit",
                "   in the facts and circumstances of the case and in the interest of justice;",
                "",
                "d) Award costs of this petition.",
            ])
        
        lines.extend([
            "",
            sep,
            "",
            "VERIFICATION",
            "",
            "I, the Petitioner above named, do hereby verify that the contents of the above",
            "petition are true to the best of my knowledge and belief and nothing material",
            "has been concealed therefrom.",
            "",
            "Verified at _________ on this _____ day of _________ 2026.",
            "",
            "",
            "                                                    PETITIONER",
            "",
            sep,
            "",
            f"Document Generated: {datetime.fromisoformat(draft.updated_at).strftime('%B %d, %Y at %I:%M %p')}",
            f"Draft Reference ID: {draft.id}",
            "",
            sep,
        ])

        return "\n".join(lines)
    
    @staticmethod
    def _parse_pil_sections(pil_text: str) -> Dict[str, Any]:
        """
        Parse PIL text to extract sections (supports BOTH markdown ## format AND old: format)
        Returns dict with facts, fundamental_rights, directive_principles, case_precedents, prayer
        """
        sections = {
            "facts": "",
            "fundamental_rights": [],
            "directive_principles": [],
            "case_precedents": [],
            "prayer": ""
        }
        
        try:
            # MARKDOWN FORMAT PARSING (## headings - REAL RAG output)
            if "## Facts of the Case" in pil_text or "## Fundamental Rights Violated" in pil_text:
                print("✅ Parsing markdown-format PIL (## headings)")
                
                # Extract Facts of the Case
                if "## Facts of the Case" in pil_text:
                    start = pil_text.find("## Facts of the Case") + len("## Facts of the Case")
                    # Find next ## heading
                    next_section_pos = pil_text.find("##", start + 2)
                    end = next_section_pos if next_section_pos != -1 else len(pil_text)
                    sections["facts"] = pil_text[start:end].strip()
                
                # Extract Fundamental Rights Violated
                if "## Fundamental Rights Violated" in pil_text:
                    start = pil_text.find("## Fundamental Rights Violated") + len("## Fundamental Rights Violated")
                    next_section_pos = pil_text.find("##", start + 2)
                    end = next_section_pos if next_section_pos != -1 else len(pil_text)
                    rights_text = pil_text[start:end].strip()
                    sections["fundamental_rights"] = [
                        line.strip() for line in rights_text.split('\n')
                        if line.strip() and line.strip().startswith('-')
                    ]
                    # Remove leading dash
                    sections["fundamental_rights"] = [
                        r.lstrip('- ').strip() for r in sections["fundamental_rights"]
                    ]
                
                # Extract Directive Principles
                if "## Directive Principles" in pil_text:
                    start = pil_text.find("## Directive Principles") + len("## Directive Principles")
                    next_section_pos = pil_text.find("##", start + 2)
                    end = next_section_pos if next_section_pos != -1 else len(pil_text)
                    principles_text = pil_text[start:end].strip()
                    sections["directive_principles"] = [
                        line.strip() for line in principles_text.split('\n')
                        if line.strip() and line.strip().startswith('-')
                    ]
                    # Remove leading dash
                    sections["directive_principles"] = [
                        p.lstrip('- ').strip() for p in sections["directive_principles"]
                    ]
                
                # Extract Case Precedents
                if "## Case Precedents" in pil_text:
                    start = pil_text.find("## Case Precedents") + len("## Case Precedents")
                    next_section_pos = pil_text.find("##", start + 2)
                    end = next_section_pos if next_section_pos != -1 else len(pil_text)
                    cases_text = pil_text[start:end].strip()
                    sections["case_precedents"] = [
                        line.strip() for line in cases_text.split('\n')
                        if line.strip() and line.strip().startswith('-')
                    ]
                    # Remove leading dash
                    sections["case_precedents"] = [
                        c.lstrip('- ').strip() for c in sections["case_precedents"]
                    ]
                
                # Extract Prayer for Relief
                if "## Prayer for Relief" in pil_text:
                    start = pil_text.find("## Prayer for Relief") + len("## Prayer for Relief")
                    sections["prayer"] = pil_text[start:].strip()
                    # Remove numbered list bullets if present
                    prayer_lines = []
                    for line in sections["prayer"].split('\n'):
                        if line.strip():
                            # Remove "1.", "2.", etc.
                            cleaned = line.strip()
                            if cleaned and cleaned[0].isdigit() and cleaned[1] in '.):':
                                cleaned = cleaned[2:].strip()
                            prayer_lines.append(cleaned)
                    sections["prayer"] = '\n'.join(prayer_lines)
            
            # OLD FORMAT PARSING (: format - fallback for compatibility)
            else:
                print("⚠️ Parsing old-format PIL (with colons)")
                
                if "Facts of the Case:" in pil_text:
                    start = pil_text.find("Facts of the Case:") + len("Facts of the Case:")
                    end = pil_text.find("Legal Grounds:") if "Legal Grounds:" in pil_text else len(pil_text)
                    sections["facts"] = pil_text[start:end].strip()
                
                if "FUNDAMENTAL RIGHTS VIOLATED:" in pil_text:
                    start = pil_text.find("FUNDAMENTAL RIGHTS VIOLATED:") + len("FUNDAMENTAL RIGHTS VIOLATED:")
                    end_markers = ["DIRECTIVE PRINCIPLES", "RELEVANT CASE PRECEDENTS", "Prayer", "OTHER CONSTITUTIONAL"]
                    end = len(pil_text)
                    for marker in end_markers:
                        pos = pil_text.find(marker, start)
                        if pos != -1 and pos < end:
                            end = pos
                    
                    rights_text = pil_text[start:end]
                    sections["fundamental_rights"] = [
                        line.strip() for line in rights_text.split('\n')
                        if line.strip() and len(line.strip()) > 10
                    ]
                
                if "DIRECTIVE PRINCIPLES" in pil_text:
                    start = pil_text.find("DIRECTIVE PRINCIPLES") + len("DIRECTIVE PRINCIPLES")
                    end_markers = ["RELEVANT CASE PRECEDENTS", "Prayer", "OTHER CONSTITUTIONAL"]
                    end = len(pil_text)
                    for marker in end_markers:
                        pos = pil_text.find(marker, start)
                        if pos != -1 and pos < end:
                            end = pos
                    
                    principles_text = pil_text[start:end]
                    sections["directive_principles"] = [
                        line.strip() for line in principles_text.split('\n')
                        if line.strip() and len(line.strip()) > 10
                    ]
                
                if "RELEVANT CASE PRECEDENTS" in pil_text or "APPLICABLE STATUTORY PROVISIONS" in pil_text:
                    marker = "RELEVANT CASE PRECEDENTS" if "RELEVANT CASE PRECEDENTS" in pil_text else "APPLICABLE STATUTORY PROVISIONS"
                    start = pil_text.find(marker) + len(marker)
                    end_markers = ["Prayer", "Filed in public"]
                    end = len(pil_text)
                    for m in end_markers:
                        pos = pil_text.find(m, start)
                        if pos != -1 and pos < end:
                            end = pos
                    
                    cases_text = pil_text[start:end]
                    sections["case_precedents"] = [
                        line.strip() for line in cases_text.split('\n')
                        if line.strip() and len(line.strip()) > 10
                    ]
                
                if "Prayer" in pil_text:
                    start = pil_text.find("Prayer") + len("Prayer")
                    end = pil_text.find("Filed in public") if "Filed in public" in pil_text else len(pil_text)
                    sections["prayer"] = pil_text[start:end].strip()
        
        except Exception as e:
            print(f"❌ Error parsing PIL sections: {e}")
        
        print(f"📊 Parsed: facts={len(sections['facts'])} chars, rights={len(sections['fundamental_rights'])}, principles={len(sections['directive_principles'])}, cases={len(sections['case_precedents'])}, prayer={len(sections['prayer'])} chars")
        return sections


# Initialize on module load
PILManager.initialize()
