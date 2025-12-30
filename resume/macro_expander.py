# resume/macro_expander.py
import re
import logging
from typing import Dict, Tuple, Optional
from pylatexenc.latexwalker import LatexWalker, get_default_latex_context_db
from pylatexenc.latex2text import LatexNodes2Text

logger = logging.getLogger(__name__)


class LaTeXMacroExpander:
    """
    Extract and expand LaTeX macros using pylatexenc [web:76][web:77]
    Handles \\newcommand definitions properly
    """
    
    # Regex patterns for macro definitions
    NEWCOMMAND_PATTERN = re.compile(
        r'\\newcommand\s*\{\s*\\([a-zA-Z0-9_]+)\s*\}\s*(?:\[(\d+)\])?\s*\{((?:[^{}]|(?:\{[^{}]*\}))*)\}',
        re.DOTALL
    )
    
    RENEWCOMMAND_PATTERN = re.compile(
        r'\\renewcommand\s*\{\s*\\([a-zA-Z0-9_]+)\s*\}\s*(?:\[(\d+)\])?\s*\{((?:[^{}]|(?:\{[^{}]*\}))*)\}',
        re.DOTALL
    )
    
    def __init__(self):
        self.latex_context = get_default_latex_context_db()
        self.latex2text = LatexNodes2Text()
        self.custom_macros: Dict[str, Tuple[Optional[int], str]] = {}
    
    def extract_macro_definitions(self, latex_content: str) -> Dict[str, str]:
        """
        Extract all \\newcommand and \\renewcommand definitions [web:72]
        
        Returns:
            Dict mapping macro names to their expanded text
        """
        macros = {}
        
        # Find all newcommand definitions
        for match in self.NEWCOMMAND_PATTERN.finditer(latex_content):
            macro_name = match.group(1)
            num_args = int(match.group(2)) if match.group(2) else 0
            macro_body = match.group(3)
            
            # Store raw definition
            self.custom_macros[macro_name] = (num_args, macro_body)
            
            # Convert to plain text (expand nested LaTeX)
            expanded = self._expand_macro_body(macro_body)
            macros[macro_name] = expanded
            
            logger.debug(f"Found macro: \\{macro_name} -> {expanded[:50]}...")
        
        # Handle renewcommand (overwrites)
        for match in self.RENEWCOMMAND_PATTERN.finditer(latex_content):
            macro_name = match.group(1)
            num_args = int(match.group(2)) if match.group(2) else 0
            macro_body = match.group(3)
            
            self.custom_macros[macro_name] = (num_args, macro_body)
            expanded = self._expand_macro_body(macro_body)
            macros[macro_name] = expanded
        
        logger.info(f"Extracted {len(macros)} macro definitions")
        return macros
    
    def _expand_macro_body(self, macro_body: str) -> str:
        """
        Expand LaTeX macro body to plain text using pylatexenc [web:77]
        
        Args:
            macro_body: LaTeX code in macro body
        
        Returns:
            Plain text representation
        """
        try:
            # Use LatexWalker to parse and expand [web:77]
            walker = LatexWalker(
                macro_body,
                latex_context=self.latex_context
            )
            
            # Parse the content
            nodelist, _, _ = walker.get_latex_nodes()
            
            # Convert to text
            text = self.latex2text.nodelist_to_text(nodelist)
            
            return text.strip()
        
        except Exception as e:
            logger.warning(f"Failed to expand macro body: {e}")
            # Fallback: return raw text with LaTeX commands stripped
            return self._strip_latex_commands(macro_body)
    
    def _strip_latex_commands(self, text: str) -> str:
        """Fallback: simple LaTeX command stripping"""
        # Remove common formatting commands
        text = re.sub(r'\\textbf\{([^}]+)\}', r'\1', text)
        text = re.sub(r'\\textit\{([^}]+)\}', r'\1', text)
        text = re.sub(r'\\emph\{([^}]+)\}', r'\1', text)
        text = re.sub(r'\\texttt\{([^}]+)\}', r'\1', text)
        
        # Remove all other commands (keep their arguments)
        text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
        text = re.sub(r'\\[a-zA-Z]+', '', text)
        
        return text.strip()
    
    def expand_text(self, text: str) -> str:
        """
        Expand all custom macro calls in text
        
        Args:
            text: Text potentially containing macro calls like \\myMacro
        
        Returns:
            Text with macros expanded
        """
        expanded = text
        
        for macro_name, (num_args, macro_body) in self.custom_macros.items():
            # Handle zero-argument macros
            if num_args == 0:
                pattern = r'\\' + re.escape(macro_name) + r'(?:\{\})?'
                expanded_text = self._expand_macro_body(macro_body)
                expanded = re.sub(pattern, expanded_text, expanded)
        
        return expanded
    
    def remove_macro_definitions(self, latex_content: str) -> str:
        """Remove all macro definitions from content"""
        content = self.NEWCOMMAND_PATTERN.sub('', latex_content)
        content = self.RENEWCOMMAND_PATTERN.sub('', content)
        return content


def extract_macro_calls(text: str, macro_names: set) -> Dict[str, list]:
    """
    Find all calls to specific macros in text
    
    Args:
        text: LaTeX text
        macro_names: Set of macro names to search for
    
    Returns:
        Dict mapping macro names to list of positions where they're called
    """
    calls = {name: [] for name in macro_names}
    
    for name in macro_names:
        pattern = r'\\' + re.escape(name) + r'(?:\{\})?'
        for match in re.finditer(pattern, text):
            calls[name].append(match.start())
    
    return calls

