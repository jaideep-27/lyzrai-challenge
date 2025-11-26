"""
Diff Parser - Parse and extract meaningful information from git diffs
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ChangedLine:
    """Represents a single changed line in a diff"""
    line_number: int
    content: str
    change_type: str  # 'addition', 'deletion', 'context'
    original_line_number: Optional[int] = None


@dataclass
class DiffHunk:
    """Represents a hunk in a diff (a contiguous block of changes)"""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    lines: List[ChangedLine] = field(default_factory=list)


@dataclass
class FileDiff:
    """Represents all changes to a single file"""
    file_path: str
    old_path: Optional[str] = None
    new_path: Optional[str] = None
    is_new_file: bool = False
    is_deleted_file: bool = False
    is_renamed: bool = False
    language: Optional[str] = None
    hunks: List[DiffHunk] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    
    def get_all_changed_lines(self) -> List[ChangedLine]:
        """Get all changed lines across all hunks"""
        all_lines = []
        for hunk in self.hunks:
            all_lines.extend(hunk.lines)
        return all_lines
    
    def get_additions(self) -> List[ChangedLine]:
        """Get only added lines"""
        return [line for line in self.get_all_changed_lines() if line.change_type == 'addition']
    
    def get_deletions(self) -> List[ChangedLine]:
        """Get only deleted lines"""
        return [line for line in self.get_all_changed_lines() if line.change_type == 'deletion']


class DiffParser:
    """Parser for unified diff format"""
    
    # File extension to language mapping
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.jsx': 'javascript',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.c': 'c',
        '.cpp': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.r': 'r',
        '.sql': 'sql',
        '.sh': 'bash',
        '.bash': 'bash',
        '.zsh': 'zsh',
        '.yml': 'yaml',
        '.yaml': 'yaml',
        '.json': 'json',
        '.xml': 'xml',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        '.md': 'markdown',
        '.rst': 'restructuredtext',
        '.vue': 'vue',
        '.svelte': 'svelte',
    }
    
    def __init__(self):
        # Regex patterns for parsing
        self.file_header_pattern = re.compile(r'^diff --git a/(.+) b/(.+)$')
        self.old_file_pattern = re.compile(r'^--- (?:a/)?(.+)$')
        self.new_file_pattern = re.compile(r'^\+\+\+ (?:b/)?(.+)$')
        self.hunk_header_pattern = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$')
        self.new_file_mode_pattern = re.compile(r'^new file mode \d+$')
        self.deleted_file_mode_pattern = re.compile(r'^deleted file mode \d+$')
        self.rename_from_pattern = re.compile(r'^rename from (.+)$')
        self.rename_to_pattern = re.compile(r'^rename to (.+)$')
    
    def detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension"""
        if not file_path:
            return None
        
        for ext, lang in self.LANGUAGE_MAP.items():
            if file_path.lower().endswith(ext):
                return lang
        return None
    
    def parse(self, diff_text: str) -> List[FileDiff]:
        """Parse a unified diff string into structured data"""
        if not diff_text or not diff_text.strip():
            return []
        
        lines = diff_text.split('\n')
        file_diffs = []
        current_file: Optional[FileDiff] = None
        current_hunk: Optional[DiffHunk] = None
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check for file header
            file_match = self.file_header_pattern.match(line)
            if file_match:
                # Save previous file diff
                if current_file and current_hunk:
                    current_file.hunks.append(current_hunk)
                if current_file:
                    file_diffs.append(current_file)
                
                # Start new file diff
                old_path, new_path = file_match.groups()
                current_file = FileDiff(
                    file_path=new_path,
                    old_path=old_path,
                    new_path=new_path,
                    language=self.detect_language(new_path)
                )
                current_hunk = None
                i += 1
                continue
            
            # Check for new/deleted file markers
            if current_file:
                if self.new_file_mode_pattern.match(line):
                    current_file.is_new_file = True
                    i += 1
                    continue
                
                if self.deleted_file_mode_pattern.match(line):
                    current_file.is_deleted_file = True
                    i += 1
                    continue
                
                rename_from = self.rename_from_pattern.match(line)
                if rename_from:
                    current_file.old_path = rename_from.group(1)
                    current_file.is_renamed = True
                    i += 1
                    continue
                
                rename_to = self.rename_to_pattern.match(line)
                if rename_to:
                    current_file.new_path = rename_to.group(1)
                    current_file.file_path = rename_to.group(1)
                    i += 1
                    continue
            
            # Check for hunk header
            hunk_match = self.hunk_header_pattern.match(line)
            if hunk_match and current_file:
                # Save previous hunk
                if current_hunk:
                    current_file.hunks.append(current_hunk)
                
                old_start = int(hunk_match.group(1))
                old_count = int(hunk_match.group(2)) if hunk_match.group(2) else 1
                new_start = int(hunk_match.group(3))
                new_count = int(hunk_match.group(4)) if hunk_match.group(4) else 1
                header_context = hunk_match.group(5).strip()
                
                current_hunk = DiffHunk(
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    header=header_context
                )
                i += 1
                continue
            
            # Parse diff content lines
            if current_hunk is not None and current_file:
                if line.startswith('+') and not line.startswith('+++'):
                    # Addition
                    new_line_num = current_hunk.new_start + len([
                        l for l in current_hunk.lines 
                        if l.change_type in ('addition', 'context')
                    ])
                    changed_line = ChangedLine(
                        line_number=new_line_num,
                        content=line[1:],  # Remove the '+' prefix
                        change_type='addition'
                    )
                    current_hunk.lines.append(changed_line)
                    current_file.additions += 1
                    
                elif line.startswith('-') and not line.startswith('---'):
                    # Deletion
                    old_line_num = current_hunk.old_start + len([
                        l for l in current_hunk.lines 
                        if l.change_type in ('deletion', 'context')
                    ])
                    changed_line = ChangedLine(
                        line_number=old_line_num,
                        content=line[1:],  # Remove the '-' prefix
                        change_type='deletion',
                        original_line_number=old_line_num
                    )
                    current_hunk.lines.append(changed_line)
                    current_file.deletions += 1
                    
                elif line.startswith(' ') or (line == '' and i < len(lines) - 1):
                    # Context line
                    new_line_num = current_hunk.new_start + len([
                        l for l in current_hunk.lines 
                        if l.change_type in ('addition', 'context')
                    ])
                    old_line_num = current_hunk.old_start + len([
                        l for l in current_hunk.lines 
                        if l.change_type in ('deletion', 'context')
                    ])
                    changed_line = ChangedLine(
                        line_number=new_line_num,
                        content=line[1:] if line.startswith(' ') else line,
                        change_type='context',
                        original_line_number=old_line_num
                    )
                    current_hunk.lines.append(changed_line)
            
            i += 1
        
        # Don't forget the last file/hunk
        if current_file and current_hunk:
            current_file.hunks.append(current_hunk)
        if current_file:
            file_diffs.append(current_file)
        
        return file_diffs
    
    def parse_github_diff(self, diff_text: str) -> List[FileDiff]:
        """Parse GitHub-formatted diff (same as unified diff)"""
        return self.parse(diff_text)
    
    def get_context_around_change(self, file_diff: FileDiff, line_number: int, context_lines: int = 3) -> Dict[str, Any]:
        """Get context around a specific line change"""
        all_lines = file_diff.get_all_changed_lines()
        
        # Find the line
        target_idx = None
        for idx, line in enumerate(all_lines):
            if line.line_number == line_number:
                target_idx = idx
                break
        
        if target_idx is None:
            return {"before": [], "target": None, "after": []}
        
        before_start = max(0, target_idx - context_lines)
        after_end = min(len(all_lines), target_idx + context_lines + 1)
        
        return {
            "before": all_lines[before_start:target_idx],
            "target": all_lines[target_idx],
            "after": all_lines[target_idx + 1:after_end]
        }
    
    def extract_code_blocks(self, file_diff: FileDiff) -> List[Dict[str, Any]]:
        """Extract logical code blocks from changes (functions, classes, etc.)"""
        code_blocks = []
        
        for hunk in file_diff.hunks:
            block = {
                "file_path": file_diff.file_path,
                "language": file_diff.language,
                "start_line": hunk.new_start,
                "end_line": hunk.new_start + hunk.new_count,
                "header": hunk.header,
                "additions": [],
                "deletions": [],
                "context": []
            }
            
            for line in hunk.lines:
                if line.change_type == 'addition':
                    block["additions"].append(line)
                elif line.change_type == 'deletion':
                    block["deletions"].append(line)
                else:
                    block["context"].append(line)
            
            code_blocks.append(block)
        
        return code_blocks
    
    def to_dict(self, file_diffs: List[FileDiff]) -> List[Dict[str, Any]]:
        """Convert parsed diffs to dictionary format"""
        result = []
        for file_diff in file_diffs:
            file_dict = {
                "file_path": file_diff.file_path,
                "old_path": file_diff.old_path,
                "new_path": file_diff.new_path,
                "is_new_file": file_diff.is_new_file,
                "is_deleted_file": file_diff.is_deleted_file,
                "is_renamed": file_diff.is_renamed,
                "language": file_diff.language,
                "additions": file_diff.additions,
                "deletions": file_diff.deletions,
                "hunks": []
            }
            
            for hunk in file_diff.hunks:
                hunk_dict = {
                    "old_start": hunk.old_start,
                    "old_count": hunk.old_count,
                    "new_start": hunk.new_start,
                    "new_count": hunk.new_count,
                    "header": hunk.header,
                    "lines": [
                        {
                            "line_number": line.line_number,
                            "content": line.content,
                            "change_type": line.change_type,
                            "original_line_number": line.original_line_number
                        }
                        for line in hunk.lines
                    ]
                }
                file_dict["hunks"].append(hunk_dict)
            
            result.append(file_dict)
        
        return result
    
    def get_summary(self, file_diffs: List[FileDiff]) -> Dict[str, Any]:
        """Get summary statistics of the diff"""
        total_additions = sum(f.additions for f in file_diffs)
        total_deletions = sum(f.deletions for f in file_diffs)
        
        languages = {}
        for f in file_diffs:
            if f.language:
                languages[f.language] = languages.get(f.language, 0) + 1
        
        return {
            "total_files": len(file_diffs),
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "new_files": len([f for f in file_diffs if f.is_new_file]),
            "deleted_files": len([f for f in file_diffs if f.is_deleted_file]),
            "renamed_files": len([f for f in file_diffs if f.is_renamed]),
            "languages": languages,
            "files": [f.file_path for f in file_diffs]
        }


# Singleton instance
diff_parser = DiffParser()
