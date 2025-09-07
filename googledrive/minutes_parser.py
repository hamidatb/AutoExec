import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .drive_auth import get_credentials
from .sheets_manager import ClubSheetsManager

class MinutesParser:
    """
    Parses meeting minutes from Google Docs to extract action items.
    Specifically looks for the Action Items table with the required columns.
    """
    
    def __init__(self):
        """Initialize the minutes parser with credentials."""
        creds = get_credentials()
        self.docs_service = build("docs", "v1", credentials=creds)
        self.sheets_manager = ClubSheetsManager()
        
    def parse_minutes_doc(self, doc_url: str) -> List[Dict[str, Any]]:
        """
        Parses a Google Doc to extract action items from the Action Items table.
        Converts the document to markdown first for better parsing of tables and checkboxes.
        
        Args:
            doc_url: URL of the Google Doc containing meeting minutes
            
        Returns:
            List of action item dictionaries
        """
        try:
            # Extract document ID from URL
            doc_id = self._extract_doc_id(doc_url)
            if not doc_id:
                return []
            
            # Convert document to markdown using doctomarkdown
            markdown_content = self._convert_doc_to_markdown(doc_id)
            if not markdown_content:
                return []
            
            # Parse the markdown content to find action items
            action_items = self._parse_markdown_action_items(markdown_content)
            
            return action_items
            
        except Exception as error:
            print(f"Error parsing minutes document: {error}")
            return []
    
    def _extract_doc_id(self, doc_url: str) -> Optional[str]:
        """
        Extracts the document ID from a Google Docs URL.
        
        Args:
            doc_url: Google Docs URL
            
        Returns:
            Document ID or None if not found
        """
        # Pattern for Google Docs URLs
        patterns = [
            r'/document/d/([a-zA-Z0-9-_]+)',
            r'/document/d/([a-zA-Z0-9-_]+)/edit',
            r'/document/d/([a-zA-Z0-9-_]+)/view'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, doc_url)
            if match:
                return match.group(1)
        
        return None
    
    def _convert_doc_to_markdown(self, doc_id: str) -> Optional[str]:
        """
        Converts a Google Doc to markdown format using doctomarkdown.
        
        Args:
            doc_id: Google Doc document ID
            
        Returns:
            Markdown content as string or None if conversion fails
        """
        try:
            from doctomarkdown import convert
            
            # Convert the Google Doc to markdown
            markdown_content = convert(f"https://docs.google.com/document/d/{doc_id}/edit")
            return markdown_content
            
        except Exception as e:
            print(f"Error converting document to markdown: {e}")
            return None
    
    def _parse_markdown_action_items(self, markdown_content: str) -> List[Dict[str, Any]]:
        """
        Parses markdown content to extract action items from the Action Items table.
        
        Args:
            markdown_content: The markdown content of the document
            
        Returns:
            List of action item dictionaries
        """
        action_items = []
        
        try:
            # Split content into lines
            lines = markdown_content.split('\n')
            
            # Find the Action Items table
            in_action_items_table = False
            table_headers = []
            
            for i, line in enumerate(lines):
                # Look for the Action Items table header
                if 'Action Items To Be Done By Next Meeting' in line or 'Action Items' in line:
                    # Check if this is a table row (contains |)
                    if '|' in line:
                        in_action_items_table = True
                        # Extract headers from the next line
                        if i + 1 < len(lines) and '|' in lines[i + 1]:
                            header_line = lines[i + 1]
                            table_headers = [h.strip() for h in header_line.split('|') if h.strip()]
                        continue
                
                # If we're in the action items table, parse the rows
                if in_action_items_table and '|' in line:
                    # Skip separator lines (containing only |, -, and spaces)
                    if re.match(r'^[\s\|\-]+$', line):
                        continue
                    
                    # Parse the table row
                    cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                    
                    if len(cells) >= 3:  # Should have Role, Team Member, Action Items columns
                        role = cells[0] if len(cells) > 0 else ""
                        team_member = cells[1] if len(cells) > 1 else ""
                        action_items_text = cells[2] if len(cells) > 2 else ""
                        
                        # Parse individual action items from the action items text
                        individual_items = self._parse_action_items_from_text(action_items_text)
                        
                        for item in individual_items:
                            action_items.append({
                                'role': role,
                                'person': team_member,
                                'task': item['task'],
                                'deadline': item.get('deadline'),
                                'completed': item['completed']
                            })
                
                # Stop parsing if we hit another major section
                elif in_action_items_table and line.strip().startswith('#'):
                    break
            
            return action_items
            
        except Exception as e:
            print(f"Error parsing markdown action items: {e}")
            return []
    
    def _parse_action_items_from_text(self, action_items_text: str) -> List[Dict[str, Any]]:
        """
        Parses individual action items from a text block containing checkboxes and tasks.
        
        Args:
            action_items_text: Text containing action items with checkboxes
            
        Returns:
            List of action item dictionaries
        """
        items = []
        
        try:
            # Split by lines and process each line
            lines = action_items_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check for checkbox patterns: [x] or [ ]
                checkbox_match = re.match(r'^-\s*\[([x\s])\]\s*(.*)', line)
                if checkbox_match:
                    is_completed = checkbox_match.group(1) == 'x'
                    task_text = checkbox_match.group(2).strip()
                    
                    # Remove strikethrough text (~~text~~)
                    task_text = re.sub(r'~~([^~]+)~~', r'\1', task_text)
                    
                    # Look for deadline in the task text
                    deadline = self._extract_deadline_from_task(task_text)
                    
                    items.append({
                        'task': task_text,
                        'completed': is_completed,
                        'deadline': deadline
                    })
                else:
                    # Handle lines without checkboxes (might be continuation or regular text)
                    if line.startswith('-') and not line.startswith('- [') and not line.startswith('- ~~'):
                        # Regular bullet point without checkbox
                        task_text = line[1:].strip()
                        deadline = self._extract_deadline_from_task(task_text)
                        
                        items.append({
                            'task': task_text,
                            'completed': False,
                            'deadline': deadline
                        })
            
            return items
            
        except Exception as e:
            print(f"Error parsing action items from text: {e}")
            return []
    
    def _extract_deadline_from_task(self, task_text: str) -> Optional[str]:
        """
        Extracts deadline information from task text.
        
        Args:
            task_text: The task description text
            
        Returns:
            Deadline string if found, None otherwise
        """
        try:
            # Look for common deadline patterns
            deadline_patterns = [
                r'deadline[:\s]+([^,\n]+)',
                r'due[:\s]+([^,\n]+)',
                r'by[:\s]+([^,\n]+)',
                r'([A-Za-z]+day,?\s+[A-Za-z]+\s+\d{1,2})',  # e.g., "Tuesday, Sept 2"
                r'([A-Za-z]+\s+\d{1,2})',  # e.g., "Sept 2"
            ]
            
            for pattern in deadline_patterns:
                match = re.search(pattern, task_text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
            
            return None
            
        except Exception as e:
            print(f"Error extracting deadline: {e}")
            return None
    
    def _extract_action_items_table(self, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extracts action items from the Action Items table in the document.
        
        Args:
            doc: Google Docs document object
            
        Returns:
            List of action item dictionaries
        """
        action_items = []
        
        # Look for table with action items
        for element in doc.get('body', {}).get('content', []):
            if 'table' in element:
                table = element['table']
                if self._is_action_items_table(table):
                    action_items = self._parse_action_items_table(table)
                    break
        
        return action_items
    
    def _is_action_items_table(self, table: Dict[str, Any]) -> bool:
        """
        Checks if a table is the Action Items table by looking at headers.
        
        Args:
            table: Table element from Google Docs
            
        Returns:
            True if it's the Action Items table
        """
        try:
            # Get the first row (headers)
            if not table.get('tableRows') or len(table['tableRows']) == 0:
                return False
            
            first_row = table['tableRows'][0]
            if not first_row.get('tableCells') or len(first_row['tableCells']) < 4:
                return False
            
            # Check if headers match expected columns
            headers = []
            for cell in first_row['tableCells']:
                if 'content' in cell:
                    header_text = self._extract_text_from_content(cell['content'])
                    headers.append(header_text.lower().strip())
            
            # Expected headers (case-insensitive)
            expected_headers = [
                'role', 'team member', 'action items to be done by next meeting', 'deadline'
            ]
            
            # Check if at least 3 out of 4 expected headers are present
            matches = sum(1 for expected in expected_headers if any(expected in header for header in headers))
            return matches >= 3
            
        except Exception as e:
            print(f"Error checking if table is action items table: {e}")
            return False
    
    def _parse_action_items_table(self, table: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parses the Action Items table to extract individual action items.
        
        Args:
            table: Action Items table element
            
        Returns:
            List of action item dictionaries
        """
        action_items = []
        
        try:
            rows = table.get('tableRows', [])
            if len(rows) < 2:  # Need at least headers + 1 data row
                return []
            
            # Get headers from first row
            headers = []
            for cell in rows[0]['tableCells']:
                if 'content' in cell:
                    header_text = self._extract_text_from_content(cell['content'])
                    headers.append(header_text.strip())
            
            # Parse data rows
            for row in rows[1:]:
                if len(row.get('tableCells', [])) >= len(headers):
                    action_item = self._parse_action_item_row(row, headers)
                    if action_item:
                        action_items.append(action_item)
            
            # Split multiple tasks in the same row
            expanded_items = []
            for item in action_items:
                if item.get('action_items'):
                    # Split multiple action items
                    action_texts = [text.strip() for text in item['action_items'].split('\n') if text.strip()]
                    for action_text in action_texts:
                        expanded_item = item.copy()
                        expanded_item['action_items'] = action_text
                        expanded_items.append(expanded_item)
                else:
                    expanded_items.append(item)
            
            return expanded_items
            
        except Exception as e:
            print(f"Error parsing action items table: {e}")
            return []
    
    def _parse_action_item_row(self, row: Dict[str, Any], headers: List[str]) -> Optional[Dict[str, Any]]:
        """
        Parses a single row from the Action Items table.
        
        Args:
            row: Table row element
            headers: List of column headers
            
        Returns:
            Action item dictionary or None if invalid
        """
        try:
            cells = row.get('tableCells', [])
            if len(cells) < len(headers):
                return None
            
            # Extract text from each cell
            row_data = {}
            for i, cell in enumerate(cells):
                if i < len(headers):
                    cell_text = self._extract_text_from_content(cell.get('content', []))
                    row_data[headers[i]] = cell_text.strip()
            
            # Create action item dictionary
            action_item = {
                'role': row_data.get('Role', ''),
                'team_member': row_data.get('Team Member', ''),
                'action_items': row_data.get('Action Items To Be Done By Next Meeting', ''),
                'deadline': row_data.get('Deadline', ''),
                'parsed_deadline': self._parse_deadline(row_data.get('Deadline', ''))
            }
            
            # Only return if we have essential information
            if action_item['team_member'] and action_item['action_items']:
                return action_item
            
            return None
            
        except Exception as e:
            print(f"Error parsing action item row: {e}")
            return None
    
    def _extract_text_from_content(self, content: List[Dict[str, Any]]) -> str:
        """
        Extracts text from Google Docs content array.
        
        Args:
            content: Content array from Google Docs
            
        Returns:
            Extracted text string
        """
        text = ""
        
        try:
            for element in content:
                if 'paragraph' in element:
                    paragraph = element['paragraph']
                    for para_element in paragraph.get('elements', []):
                        if 'textRun' in para_element:
                            text += para_element['textRun'].get('content', '')
                elif 'table' in element:
                    # Handle nested tables if any
                    text += "[Table Content]"
            
            return text
            
        except Exception as e:
            print(f"Error extracting text from content: {e}")
            return ""
    
    def _parse_deadline(self, deadline_text: str) -> Optional[str]:
        """
        Parses deadline text into ISO 8601 format.
        
        Args:
            deadline_text: Deadline text from the document
            
        Returns:
            ISO 8601 formatted deadline string or None if unparseable
        """
        if not deadline_text:
            return None
        
        try:
            # Common deadline formats
            deadline_text = deadline_text.lower().strip()
            
            # Handle relative dates
            if 'next meeting' in deadline_text:
                return 'next_meeting'
            elif 'this week' in deadline_text:
                return 'this_week'
            elif 'next week' in deadline_text:
                return 'next_week'
            elif 'end of month' in deadline_text:
                return 'end_of_month'
            
            # Handle specific dates
            # Try various date formats
            date_formats = [
                '%Y-%m-%d',           # 2025-09-15
                '%B %d, %Y',          # September 15, 2025
                '%B %d',              # September 15 (assume current year)
                '%b %d, %Y',          # Sep 15, 2025
                '%b %d',              # Sep 15 (assume current year)
                '%m/%d/%Y',           # 09/15/2025
                '%m/%d/%y',           # 09/15/25
                '%d/%m/%Y',           # 15/09/2025
                '%d/%m/%y',           # 15/09/25
            ]
            
            for fmt in date_formats:
                try:
                    if fmt in ['%B %d', '%b %d']:
                        # Add current year
                        parsed_date = datetime.strptime(deadline_text, fmt)
                        current_year = datetime.now().year
                        parsed_date = parsed_date.replace(year=current_year)
                    else:
                        parsed_date = datetime.strptime(deadline_text, fmt)
                    
                    # Convert to ISO format
                    return parsed_date.isoformat()
                    
                except ValueError:
                    continue
            
            # If we can't parse it, return the original text
            return deadline_text
            
        except Exception as e:
            print(f"Error parsing deadline '{deadline_text}': {e}")
            return deadline_text
    
    def create_tasks_from_minutes(self, doc_url: str, tasks_spreadsheet_id: str, 
                                 people_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Creates tasks in Google Sheets from parsed meeting minutes.
        
        Args:
            doc_url: URL of the minutes document
            tasks_spreadsheet_id: ID of the tasks spreadsheet
            people_mapping: Dictionary mapping names to Discord IDs
            
        Returns:
            List of created task dictionaries
        """
        try:
            # Parse the minutes document
            action_items = self.parse_minutes_doc(doc_url)
            
            if not action_items:
                print("No action items found in the minutes document.")
                return []
            
            created_tasks = []
            
            for item in action_items:
                # Map team member name to Discord ID
                discord_id = people_mapping.get(item['team_member'], '')
                
                # Create task data
                task_data = {
                    'title': item['action_items'],
                    'owner_discord_id': discord_id,
                    'owner_name': item['team_member'],
                    'due_at': item['parsed_deadline'],
                    'status': 'open',
                    'priority': 'medium',
                    'source_doc': doc_url,
                    'channel_id': '',  # Will be set based on configuration
                    'notes': f"Role: {item['role']}"
                }
                
                # Add task to spreadsheet
                if self.sheets_manager.add_task(tasks_spreadsheet_id, task_data):
                    created_tasks.append(task_data)
                    print(f"Created task: {item['action_items']} for {item['team_member']}")
                else:
                    print(f"Failed to create task: {item['action_items']}")
            
            return created_tasks
            
        except Exception as e:
            print(f"Error creating tasks from minutes: {e}")
            return []
