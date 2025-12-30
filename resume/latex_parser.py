# resume/latex_parser.py
import re
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from pylatexenc.latex2text import LatexNodes2Text
import yaml

from resume.config import get_config, ResumeConfig
from resume.models import (
    ParsedResume, ResumeMetadata, PersonalInfo, BulletPoint,
    ExperienceEntry, EducationEntry, SkillsSection
)
from resume.macro_expander import LaTeXMacroExpander
from resume.section_extractor import SectionExtractor

logger = logging.getLogger(__name__)


class LaTeXResumeParser:
    """
    Robust LaTeX resume parser using regex + pylatexenc

    Features:
    - Uses regex for structural parsing (sections, itemize)
    - Uses pylatexenc for macro expansion and text conversion
    - Handles enumitem optional args properly
    - Supports custom resume template commands (resumeSubheading, resumeItem)
    - No TexSoup dependency
    """

    # Personal info patterns
    PERSONAL_PATTERNS = {
        'name': [
            re.compile(r'\\name\s*\{([^}]+)\}', re.IGNORECASE),
            re.compile(r'\\author\s*\{([^}]+)\}', re.IGNORECASE),
        ],
        'email': [
            re.compile(r'\\email\s*\{([^}]+)\}', re.IGNORECASE),
            re.compile(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'),
        ],
        'phone': [
            re.compile(r'\\phone\s*\{([^}]+)\}', re.IGNORECASE),
            re.compile(r'\\mobile\s*\{([^}]+)\}', re.IGNORECASE),
            re.compile(r'\+?\d{1,3}[\s-]?\d{3,4}[\s-]?\d{4,}'),
        ],
        'location': [
            re.compile(r'\\location\s*\{([^}]+)\}', re.IGNORECASE),
            re.compile(r'\\address\s*\{([^}]+)\}', re.IGNORECASE),
        ],
        'linkedin': [
            re.compile(r'\\linkedin\s*\{([^}]+)\}', re.IGNORECASE),
            re.compile(r'linkedin\.com/in/([a-zA-Z0-9-]+)'),
        ],
        'github': [
            re.compile(r'\\github\s*\{([^}]+)\}', re.IGNORECASE),
            re.compile(r'github\.com/([a-zA-Z0-9-]+)'),
        ],
    }

    # Name extraction from bfseries/center (for custom templates)
    NAME_FROM_BFSERIES = re.compile(
        r'\\(?:Huge|LARGE|Large|large)?\s*\\bfseries\s+([A-Z][a-zA-Z\s]+?)(?:\\\\|\})',
        re.IGNORECASE
    )

    # Experience entry pattern (Title -- Company or Title | Company)
    EXPERIENCE_TITLE_PATTERN = re.compile(
        r'^(.+?)\s*(?:--|—|\||@)\s*(.+?)$',
        re.MULTILINE
    )

    # Custom resume template patterns
    RESUME_ITEM_START = re.compile(r'\\resumeItem\s*\{')
    RESUME_SUBHEADING_START = re.compile(r'\\resumeSubheading\s*\{')

    # Date range patterns
    DATE_PATTERN = re.compile(
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}',
        re.IGNORECASE
    )

    @staticmethod
    def _extract_balanced_braces(text: str, start_pos: int) -> Tuple[str, int]:
        """
        Extract content within balanced braces starting at position

        Args:
            text: Full text
            start_pos: Position of opening brace

        Returns:
            Tuple of (content, end_position)
        """
        if start_pos >= len(text) or text[start_pos] != '{':
            return "", start_pos

        brace_count = 0
        i = start_pos

        while i < len(text):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Found closing brace
                    return text[start_pos + 1:i], i
            i += 1

        # Unbalanced braces - return what we have
        return text[start_pos + 1:], len(text)

    def __init__(self, config: Optional[ResumeConfig] = None):
        self.config = config or get_config()
        self.macro_expander = LaTeXMacroExpander()
        self.section_extractor = SectionExtractor()
        self.latex2text = LatexNodes2Text()

    def parse_file(self, filepath: str) -> ParsedResume:
        """
        Parse LaTeX resume file

        Args:
            filepath: Path to .tex file

        Returns:
            ParsedResume object
        """
        import traceback

        try:
            filepath = Path(filepath)

            if not filepath.exists():
                raise FileNotFoundError(f"Resume file not found: {filepath}")

            logger.info(f"Parsing resume: {filepath}")

            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract YAML frontmatter
            metadata = self._extract_frontmatter(content)
            content = self._remove_frontmatter(content)

            # Extract and store macro definitions
            custom_macros = self.macro_expander.extract_macro_definitions(content)

            # Remove macro definitions from content (cleaner parsing)
            content_without_defs = self.macro_expander.remove_macro_definitions(content)

            # Extract sections
            sections = self.section_extractor.extract_sections(content_without_defs)

            # Initialize parsed resume
            resume = ParsedResume(
                metadata=metadata,
                source_file=str(filepath),
                personal=PersonalInfo(),
                custom_commands=custom_macros
            )

            # Extract personal info
            resume.personal = self._extract_personal_info(content)

            # Extract section content
            resume.summary = self._extract_summary(sections, content_without_defs)
            resume.experience = self._extract_experience(sections)
            resume.education = self._extract_education(sections)
            resume.skills = self._extract_skills(sections)
            resume.certifications = self._extract_list_section(sections, 'certifications?')
            resume.awards = self._extract_list_section(sections, 'awards?|honors?')
            resume.projects = self._extract_projects(sections)

            # Collect all bullets
            resume.all_bullets = self._collect_all_bullets(resume)

            logger.info(f"Parsed resume: {len(resume.all_bullets)} bullets, "
                       f"{len(resume.experience)} experiences, "
                       f"{len(resume.education)} education")

            return resume

        except Exception as e:
            logger.error(f"Parse error: {e}")
            traceback.print_exc()
            raise

    def _extract_frontmatter(self, content: str) -> ResumeMetadata:
        """Extract YAML frontmatter from document"""
        if not content.startswith('---'):
            return ResumeMetadata()

        try:
            parts = content.split('---', 2)
            if len(parts) < 3:
                return ResumeMetadata()

            yaml_content = parts[1].strip()
            data = yaml.safe_load(yaml_content)

            if not data:
                return ResumeMetadata()

            return ResumeMetadata(
                name=data.get('name'),
                target_role=data.get('target_role'),
                version=data.get('version', '1.0.0'),
                tags=data.get('tags', []),
                custom_fields=data
            )

        except Exception as e:
            logger.warning(f"Failed to parse frontmatter: {e}")
            return ResumeMetadata()

    def _remove_frontmatter(self, content: str) -> str:
        """Remove YAML frontmatter"""
        if not content.startswith('---'):
            return content

        parts = content.split('---', 2)
        if len(parts) >= 3:
            return parts[2].strip()

        return content
        
        

    def _extract_personal_info(self, content: str) -> PersonalInfo:
        """Extract personal information using patterns"""
        personal = PersonalInfo()
        
        # Try standard patterns first
        for field, patterns in self.PERSONAL_PATTERNS.items():
            for pattern in patterns:
                match = pattern.search(content)
                if match:
                    # Check if pattern has capturing groups
                    if pattern.groups > 0:
                        value = match.group(1).strip()
                    else:
                        # Pattern matches but has no groups - use full match
                        value = match.group(0).strip()
                    
                    # Clean LaTeX formatting
                    value = self.latex2text.latex_to_text(value)
                    
                    # Additional cleanup for URLs
                    if field in ['linkedin', 'github']:
                        # Extract just the username part if full URL
                        if '/' in value:
                            value = value.split('/')[-1]
                    
                    setattr(personal, field, value)
                    logger.debug(f"Found {field}: {value}")
                    break  # Use first match
        
        # If name not found, try bfseries pattern (custom templates)
        if not personal.name:
            match = self.NAME_FROM_BFSERIES.search(content)
            if match:
                personal.name = match.group(1).strip()
                logger.debug(f"Found name from bfseries: {personal.name}")
        
        return personal



    def _extract_summary(self, sections: List, content: str) -> Optional[str]:
        """Extract professional summary/objective"""
        section = self.section_extractor.find_section_by_name(
            sections,
            r'summary|objective|profile'
        )

        if section:
            # Get first paragraph (before any lists)
            text = section.content.split('\\begin{itemize}')[0]
            text = text.split('\\begin{enumerate}')[0]

            # Convert to plain text
            text = self.latex2text.latex_to_text(text).strip()

            if len(text) > 50:
                return text

        return None

    def _extract_experience(self, sections: List) -> List[ExperienceEntry]:
        """Extract work experience section"""
        # Find experience section
        exp_section = self.section_extractor.find_section_by_name(
            sections,
            r'experience|work\s*history|employment'
        )

        if not exp_section:
            logger.warning("No experience section found")
            return []

        # Try custom resume template format first (resumeSubheading)
        experiences = self._parse_resume_subheading_experience(exp_section.content)

        if experiences:
            logger.info(f"Extracted {len(experiences)} experience entries (custom template)")
            return experiences

        # Fallback to standard subsection format
        experiences = []
        subsections = self.section_extractor.extract_subsections(exp_section.content)

        for subsection_title, subsection_content in subsections:
            try:
                entry = self._parse_experience_entry(
                    subsection_title,
                    subsection_content
                )
                if entry:
                    experiences.append(entry)
            except Exception as e:
                logger.error(f"Failed to parse experience: {e}")
                continue

        logger.info(f"Extracted {len(experiences)} experience entries (standard format)")
        return experiences

    def _parse_resume_subheading_experience(self, content: str) -> List[ExperienceEntry]:
        """Parse experience using \\resumeSubheading custom command"""
        experiences = []

        # Find all resumeSubheading calls manually (handles nested braces)
        for match in self.RESUME_SUBHEADING_START.finditer(content):
            try:
                # Extract 4 arguments with balanced braces
                pos = match.end() - 1  # Position of first opening brace

                # Arg 1: Title
                title_text, pos = self._extract_balanced_braces(content, pos)
                title = self.latex2text.latex_to_text(title_text.strip())

                # Skip whitespace and opening brace
                pos += 1
                while pos < len(content) and content[pos] in ' \t\n':
                    pos += 1

                # Arg 2: Date
                date_text, pos = self._extract_balanced_braces(content, pos)
                date_range = date_text.strip()

                # Skip whitespace
                pos += 1
                while pos < len(content) and content[pos] in ' \t\n':
                    pos += 1

                # Arg 3: Company
                company_text, pos = self._extract_balanced_braces(content, pos)
                company = self.latex2text.latex_to_text(company_text.strip())

                # Skip whitespace
                pos += 1
                while pos < len(content) and content[pos] in ' \t\n':
                    pos += 1

                # Arg 4: Location
                location_text, pos = self._extract_balanced_braces(content, pos)
                location = self.latex2text.latex_to_text(location_text.strip())

                # Parse date range
                dates = [d.strip() for d in date_range.split('--')]
                start_date = dates[0] if len(dates) > 0 else None
                end_date = dates[1] if len(dates) > 1 else start_date

                # Find bullets after this resumeSubheading
                rest_content = content[pos:]

                # Find next resumeSubheading or end
                next_match = self.RESUME_SUBHEADING_START.search(rest_content)
                if next_match:
                    bullet_section = rest_content[:next_match.start()]
                else:
                    bullet_section = rest_content

                # Extract resumeItem bullets manually
                bullets = []
                for item_match in self.RESUME_ITEM_START.finditer(bullet_section):
                    try:
                        item_pos = item_match.end() - 1
                        bullet_text, _ = self._extract_balanced_braces(bullet_section, item_pos)

                        # Expand macros
                        expanded = self.macro_expander.expand_text(bullet_text.strip())
                        plain_text = self.latex2text.latex_to_text(expanded).strip()

                        # Check if this uses a custom command
                        cmd_name = self._find_macro_in_text(
                            bullet_text,
                            set(self.macro_expander.custom_macros.keys())
                        )

                        bullet = BulletPoint(
                            id=f"{company.replace(' ', '_').replace('&', 'and').lower()}_{len(bullets)}",
                            text=plain_text,
                            section='experience',
                            subsection=company,
                            is_modifiable=True,
                            command_name=cmd_name,
                            original_text=bullet_text if cmd_name else None
                        )
                        bullets.append(bullet)
                    except Exception as e:
                        logger.warning(f"Failed to parse bullet: {e}")
                        continue

                if bullets:  # Only add if we found bullets
                    entry = ExperienceEntry(
                        title=title,
                        company=company,
                        location=location,
                        start_date=start_date,
                        end_date=end_date,
                        bullets=bullets
                    )
                    experiences.append(entry)
                    logger.debug(f"Parsed experience: {company} with {len(bullets)} bullets")

            except Exception as e:
                logger.error(f"Failed to parse resumeSubheading: {e}")
                continue

        return experiences

    def _parse_experience_entry(
        self,
        title_line: str,
        content: str
    ) -> Optional[ExperienceEntry]:
        """Parse individual experience entry (standard format)"""
        # Parse title line (Title -- Company or Title | Company)
        title_match = self.EXPERIENCE_TITLE_PATTERN.search(title_line)

        if title_match:
            title = self.latex2text.latex_to_text(title_match.group(1).strip())
            company = self.latex2text.latex_to_text(title_match.group(2).strip())
        else:
            # Fallback: use whole line as title
            title = self.latex2text.latex_to_text(title_line.strip())
            company = "Unknown"

        # Extract dates if present
        dates = self.DATE_PATTERN.findall(content)
        start_date = dates[0] if len(dates) > 0 else None
        end_date = dates[1] if len(dates) > 1 else start_date

        # Extract location if present
        location_match = re.search(r'\\textit\{([^}]+)\}.*?\\hfill', content)
        location = location_match.group(1) if location_match else None

        # Extract bullets from itemize blocks
        bullets = []
        itemize_blocks = self.section_extractor.extract_itemize_blocks(content)

        for block in itemize_blocks:
            for i, item_text in enumerate(block['items']):
                # Expand macros in bullet text
                expanded_text = self.macro_expander.expand_text(item_text)

                # Convert to plain text
                plain_text = self.latex2text.latex_to_text(expanded_text).strip()

                # Check if this bullet uses a custom command
                cmd_name = self._find_macro_in_text(
                    item_text,
                    set(self.macro_expander.custom_macros.keys())
                )

                bullet = BulletPoint(
                    id=f"{company.replace(' ', '_').lower()}_{i}",
                    text=plain_text,
                    section='experience',
                    subsection=company,
                    is_modifiable=True,
                    command_name=cmd_name,
                    original_text=item_text if cmd_name else None
                )
                bullets.append(bullet)

        return ExperienceEntry(
            title=title,
            company=company,
            location=location,
            start_date=start_date,
            end_date=end_date,
            bullets=bullets
        )

    def _extract_education(self, sections: List) -> List[EducationEntry]:
        """Extract education section"""
        edu_section = self.section_extractor.find_section_by_name(
            sections,
            r'education'
        )

        if not edu_section:
            logger.warning("No education section found")
            return []

        # Try custom resume template format first (resumeSubheading)
        education = self._parse_resume_subheading_education(edu_section.content)

        if education:
            logger.info(f"Extracted {len(education)} education entries (custom template)")
            return education

        # Fallback to standard subsection format
        education = []
        subsections = self.section_extractor.extract_subsections(edu_section.content)

        for subsection_title, subsection_content in subsections:
            # Parse "Degree -- Institution" format
            title_match = self.EXPERIENCE_TITLE_PATTERN.search(subsection_title)

            if title_match:
                degree = self.latex2text.latex_to_text(title_match.group(1).strip())
                institution = self.latex2text.latex_to_text(title_match.group(2).strip())
            else:
                degree = self.latex2text.latex_to_text(subsection_title.strip())
                institution = ""

            # Extract graduation date
            dates = self.DATE_PATTERN.findall(subsection_content)
            grad_date = dates[0] if dates else None

            entry = EducationEntry(
                degree=degree,
                institution=institution,
                graduation_date=grad_date
            )
            education.append(entry)

        logger.info(f"Extracted {len(education)} education entries (standard format)")
        return education

    def _parse_resume_subheading_education(self, content: str) -> List[EducationEntry]:
        """Parse education using \\resumeSubheading custom command"""
        education = []

        # Find all resumeSubheading calls manually
        for match in self.RESUME_SUBHEADING_START.finditer(content):
            try:
                # Extract 4 arguments
                pos = match.end() - 1

                # Arg 1: Institution
                institution_text, pos = self._extract_balanced_braces(content, pos)
                institution = self.latex2text.latex_to_text(institution_text.strip())

                pos += 1
                while pos < len(content) and content[pos] in ' \t\n':
                    pos += 1

                # Arg 2: Location
                location_text, pos = self._extract_balanced_braces(content, pos)
                location = self.latex2text.latex_to_text(location_text.strip())

                pos += 1
                while pos < len(content) and content[pos] in ' \t\n':
                    pos += 1

                # Arg 3: Degree
                degree_text, pos = self._extract_balanced_braces(content, pos)
                degree = self.latex2text.latex_to_text(degree_text.strip())

                pos += 1
                while pos < len(content) and content[pos] in ' \t\n':
                    pos += 1

                # Arg 4: Date
                date_text, pos = self._extract_balanced_braces(content, pos)
                date_range = date_text.strip()

                entry = EducationEntry(
                    degree=degree,
                    institution=institution,
                    location=location,
                    graduation_date=date_range
                )
                education.append(entry)
                logger.debug(f"Parsed education: {institution} - {degree}")

            except Exception as e:
                logger.error(f"Failed to parse education entry: {e}")
                continue

        return education

    def _extract_skills(self, sections: List) -> SkillsSection:
        """Extract skills section"""
        skills = SkillsSection()

        skills_section = self.section_extractor.find_section_by_name(
            sections,
            r'(?:technical\s*)?skills|technologies'
        )

        if not skills_section:
            logger.warning("No skills section found")
            return skills

        # Convert to plain text
        text = self.latex2text.latex_to_text(skills_section.content)

        # Parse skill categories (look for bold labels followed by colon)
        category_pattern = re.compile(r'([A-Za-z\s]+):\s*([^\n]+)', re.IGNORECASE)

        for match in category_pattern.finditer(text):
            category_name = match.group(1).strip().lower()
            items_str = match.group(2).strip()

            # Split by comma
            items = [s.strip() for s in items_str.split(',') if s.strip()]

            # Map to skill fields
            if any(keyword in category_name for keyword in ['technical', 'programming', 'language', 'kafka', 'ecosystem']):
                skills.technical.extend(items)
            elif any(keyword in category_name for keyword in ['tool', 'devops', 'platform', 'monitoring']):
                skills.tools.extend(items)
            elif 'language' in category_name and 'programming' not in category_name:
                skills.languages.extend(items)
            elif any(keyword in category_name for keyword in ['scripting', 'script']):
                skills.technical.extend(items)
            else:
                # Generic - add to tools
                skills.tools.extend(items)

        # Deduplicate
        skills.technical = list(dict.fromkeys(skills.technical))
        skills.tools = list(dict.fromkeys(skills.tools))
        skills.languages = list(dict.fromkeys(skills.languages))

        logger.debug(f"Extracted skills: {len(skills.technical)} technical, {len(skills.tools)} tools")
        return skills

    def _extract_projects(self, sections: List) -> List[Dict]:
        """Extract projects section"""
        projects = []

        proj_section = self.section_extractor.find_section_by_name(
            sections,
            r'projects?'
        )

        if not proj_section:
            return projects

        # Extract subsections
        subsections = self.section_extractor.extract_subsections(proj_section.content)

        for subsection_title, subsection_content in subsections:
            project_name = self.latex2text.latex_to_text(subsection_title.strip())
            description = self.latex2text.latex_to_text(subsection_content.strip())

            projects.append({
                'name': project_name,
                'description': description
            })

        return projects

    def _extract_list_section(self, sections: List, section_pattern: str) -> List[str]:
        """Extract simple list section (certifications, awards)"""
        items = []

        section = self.section_extractor.find_section_by_name(
            sections,
            section_pattern
        )

        if not section:
            return items

        # Extract itemize blocks
        itemize_blocks = self.section_extractor.extract_itemize_blocks(section.content)

        for block in itemize_blocks:
            for item_text in block['items']:
                # Expand macros
                expanded = self.macro_expander.expand_text(item_text)

                # Convert to plain text
                plain_text = self.latex2text.latex_to_text(expanded).strip()

                if plain_text:
                    items.append(plain_text)

        # Fallback: if no itemize found, try footnotesize blocks
        if not items:
            # Look for \item in footnotesize environment
            footnote_pattern = re.compile(r'\\item\s+(.+?)(?=\\item|\\end|$)', re.DOTALL)
            for match in footnote_pattern.finditer(section.content):
                item_text = match.group(1).strip()
                plain_text = self.latex2text.latex_to_text(item_text).strip()
                if plain_text:
                    items.append(plain_text)

        return items

    def _collect_all_bullets(self, resume: ParsedResume) -> List[BulletPoint]:
        """Collect all bullet points from all sections"""
        bullets = []

        # Experience bullets
        for exp in resume.experience:
            bullets.extend(exp.bullets)

        # Project bullets (if structured)
        for project in resume.projects:
            if 'bullets' in project:
                bullets.extend(project['bullets'])

        return bullets

    def _find_macro_in_text(self, text: str, macro_names: set) -> Optional[str]:
        """Check if text contains a custom macro call"""
        for macro_name in macro_names:
            pattern = r'\\' + re.escape(macro_name) + r'(?:\{\})?'
            if re.search(pattern, text):
                return macro_name

        return None
