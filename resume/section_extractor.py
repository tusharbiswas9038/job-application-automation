# resume/section_extractor.py
import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LaTeXSection:
    """Represents a LaTeX section"""
    level: int  # 1=section, 2=subsection, 3=subsubsection
    title: str
    content: str
    start_pos: int
    end_pos: int
    line_number: int


class SectionExtractor:
    """
    Extract sections from LaTeX document using regex [web:81]
    Handles nested structures properly
    """
    
    # Section patterns (in order of priority)
    SECTION_PATTERNS = [
        (1, re.compile(r'\\section\*?\s*\{([^}]+)\}', re.IGNORECASE)),
        (2, re.compile(r'\\subsection\*?\s*\{([^}]+)\}', re.IGNORECASE)),
        (3, re.compile(r'\\subsubsection\*?\s*\{([^}]+)\}', re.IGNORECASE)),
    ]
    
    # Environment patterns (handles optional args like [leftmargin=*])
    ITEMIZE_PATTERN = re.compile(
        r'\\begin\{itemize\}(?:\[([^\]]*)\])?(.*?)\\end\{itemize\}',
        re.DOTALL | re.IGNORECASE
    )
    
    ENUMERATE_PATTERN = re.compile(
        r'\\begin\{enumerate\}(?:\[([^\]]*)\])?(.*?)\\end\{enumerate\}',
        re.DOTALL | re.IGNORECASE
    )
    
    # Item pattern
    ITEM_PATTERN = re.compile(r'\\item\s+(.+?)(?=\\item|\\end\{(?:itemize|enumerate)\}|$)', re.DOTALL)
    
    def __init__(self):
        pass
    
    def extract_sections(self, latex_content: str) -> List[LaTeXSection]:
        """
        Extract all sections from LaTeX document [web:81]
        
        Returns:
            List of LaTeXSection objects in document order
        """
        sections = []
        
        # Find all section markers
        section_markers = []
        
        for level, pattern in self.SECTION_PATTERNS:
            for match in pattern.finditer(latex_content):
                section_markers.append({
                    'level': level,
                    'title': match.group(1).strip(),
                    'start_pos': match.start(),
                    'end_pos': match.end(),
                    'line_number': latex_content[:match.start()].count('\n') + 1
                })
        
        # Sort by position
        section_markers.sort(key=lambda x: x['start_pos'])
        
        # Extract content between sections
        for i, marker in enumerate(section_markers):
            # Find end position (next section of same or higher level, or end of doc)
            end_pos = len(latex_content)
            
            for next_marker in section_markers[i + 1:]:
                if next_marker['level'] <= marker['level']:
                    end_pos = next_marker['start_pos']
                    break
            
            content = latex_content[marker['end_pos']:end_pos].strip()
            
            section = LaTeXSection(
                level=marker['level'],
                title=marker['title'],
                content=content,
                start_pos=marker['start_pos'],
                end_pos=end_pos,
                line_number=marker['line_number']
            )
            
            sections.append(section)
        
        logger.info(f"Extracted {len(sections)} sections")
        return sections
    
    def find_section_by_name(
        self,
        sections: List[LaTeXSection],
        name_pattern: str,
        case_sensitive: bool = False
    ) -> Optional[LaTeXSection]:
        """Find section matching name pattern"""
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(name_pattern, flags)
        
        for section in sections:
            if pattern.search(section.title):
                return section
        
        return None
    
    def extract_itemize_blocks(self, content: str) -> List[Dict]:
        """
        Extract itemize/enumerate blocks with optional args [web:69]
        
        Returns:
            List of dicts with 'type', 'options', 'items', 'raw_content'
        """
        blocks = []
        
        # Extract itemize environments
        for match in self.ITEMIZE_PATTERN.finditer(content):
            options = match.group(1) if match.group(1) else None
            block_content = match.group(2)
            items = self._extract_items(block_content)
            
            blocks.append({
                'type': 'itemize',
                'options': options,
                'items': items,
                'raw_content': match.group(0),
                'start_pos': match.start(),
                'end_pos': match.end()
            })
        
        # Extract enumerate environments
        for match in self.ENUMERATE_PATTERN.finditer(content):
            options = match.group(1) if match.group(1) else None
            block_content = match.group(2)
            items = self._extract_items(block_content)
            
            blocks.append({
                'type': 'enumerate',
                'options': options,
                'items': items,
                'raw_content': match.group(0),
                'start_pos': match.start(),
                'end_pos': match.end()
            })
        
        # Sort by position
        blocks.sort(key=lambda x: x['start_pos'])
        
        return blocks
    
    def _extract_items(self, content: str) -> List[str]:
        """Extract \\item entries from itemize/enumerate content"""
        items = []
        
        for match in self.ITEM_PATTERN.finditer(content):
            item_text = match.group(1).strip()
            if item_text:
                items.append(item_text)
        
        return items
    
    def extract_subsections(self, section_content: str) -> List[Tuple[str, str]]:
        """
        Extract subsections from a section's content
        
        Returns:
            List of (subsection_title, subsection_content) tuples
        """
        subsections = []
        
        # Find all subsection markers in this content
        pattern = self.SECTION_PATTERNS[1][1]  # subsection pattern
        matches = list(pattern.finditer(section_content))
        
        for i, match in enumerate(matches):
            title = match.group(1).strip()
            start = match.end()
            
            # Find end (next subsection or end of content)
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(section_content)
            
            content = section_content[start:end].strip()
            subsections.append((title, content))
        
        return subsections

