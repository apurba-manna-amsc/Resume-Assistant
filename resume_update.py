# Required imports
import json
import re
import copy
import time
import requests
from typing import Dict, Any, List
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ResumeUpdater:
    def __init__(self):
        """Initialize the ResumeUpdater with Groq API credentials"""
        self.groq_api_key = os.getenv("GROQ_API_KEY")  # Set this in your .env file
        
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.groq_api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        # Choose your preferred model
        self.llm_model = "llama3-70b-8192"  # Options: llama-3.1-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768
        
        print(f"🔑 API Key loaded: {'✅' if self.groq_api_key else '❌'}")
        print(f"🤖 Using model: {self.llm_model}")

    def update_resume_with_groq(self, resume_json: Dict[str, Any], user_request: str) -> List[str]:
        """
        Parse natural language update requests and generate executable resume update commands
        
        Args:
            resume_json (Dict[str, Any]): Current resume data structure
            user_request (str): Natural language description of desired updates
        
        Returns:
            List[str]: List of executable Python commands to update the resume
        """
        
        # Convert resume_json to formatted string for context
        resume_context = json.dumps(resume_json, indent=2)
        
        prompt = f"""
You are an expert resume update parser. Your task is to analyze a natural language update request and generate precise Python commands to modify a resume JSON structure.

**CURRENT RESUME STRUCTURE:**
\\```json
{resume_context}
\\```

**UPDATE REQUEST:**
{user_request}

TASK INSTRUCTIONS:

1. Return a Python list of strings, where each string is a valid Python command to update the resume JSON using the exact structure provided above.
2. You MUST generate realistic rewritten content for summaries, descriptions, and text fields. Do NOT use placeholders like "new summary" or "updated text". Your rewrites should be formal, clear, and suitable for a professional resume.
3. Only modify fields explicitly mentioned in the user request.
4. Use proper Python syntax with single quotes. For example:
   - resume['overview']['professional_summary'] = 'Rewritten summary here.'
   - resume['skills'].append('NewSkill')
   - resume['projects'][1]['description'][0] = 'Revised project bullet point.'
5. Use correct array indexing (e.g., for skills, projects, experience, etc.). Don't guess indexes; follow the structure given.
6. DO NOT create or modify non-existent fields. Only use keys and arrays visible in the JSON structure.
7. DO NOT include explanations or extra text — return only the list of update commands.
8. If the user request is ambiguous or not applicable, return an empty list: [].

EXAMPLES:

Request: "Add React and FastAPI to my skills"  
→ Output:  
["resume['skills'].append('React')", "resume['skills'].append('FastAPI')"]

Request: "Update my professional summary to emphasize AI and ML projects"  
→ Output:  
["resume['overview']['professional_summary'] = 'AI/ML enthusiast with a strong track record in building intelligent systems, deploying scalable models, and driving innovation through data.'"]

Request: "Revise the second project description to highlight my work on recommender systems"  
→ Output:  
["resume['projects'][1]['description'][0] = 'Designed and deployed a recommender system using matrix factorization, increasing user engagement by 30%.'"]

Request: "Remove the third skill"  
→ Output:  
["resume['skills'].pop(2)"]

FINAL OUTPUT FORMAT:

Return ONLY a valid Python list of update commands, no extra text. For example:

["resume['overview']['current_role'] = 'Machine Learning Intern'", "resume['skills'].append('LangChain')"]

⚠️ STRICT LIST ONLY. NO MARKDOWN. NO TEXT OUTSIDE LIST.
"""

        payload = {
            "model": self.llm_model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are an expert at parsing natural language into precise Python commands for JSON manipulation. Always return valid Python list format only."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 1000
        }
        
        max_retries = 1
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print(f"🔄 Parsing update request (attempt {retry_count + 1}/{max_retries})...")
                
                response = requests.post(self.groq_api_url, headers=self.headers, json=payload)
                response.raise_for_status()
                
                commands_str = response.json()["choices"][0]["message"]["content"].strip()
                print(f"📝 Raw commands response: {commands_str}")
                
                # Try to extract Python list from the response
                commands_str = self._extract_python_list_from_response(commands_str)
                print(f"📝 Cleaned commands: {commands_str}")
                
                # Parse the Python list safely
                if commands_str.startswith('[') and commands_str.endswith(']'):
                    try:
                        # Use ast.literal_eval instead of eval for safety
                        import ast
                        commands = ast.literal_eval(commands_str)
                    except (ValueError, SyntaxError) as parse_error:
                        print(f"🔍 AST parse error: {parse_error}")
                        # Fallback to eval if ast fails
                        try:
                            commands = eval(commands_str)
                        except Exception as eval_error:
                            print(f"🔍 Eval parse error: {eval_error}")
                            commands = []
                else:
                    commands = []
                
                # Validate commands format
                if isinstance(commands, list) and all(isinstance(cmd, str) for cmd in commands):
                    print(f"✅ Successfully parsed {len(commands)} update commands!")
                    return commands
                else:
                    raise ValueError("Invalid commands format returned")
                    
            except (SyntaxError, ValueError, requests.exceptions.RequestException) as e:
                print(f"❌ Error parsing update request: {e}")
                
                # Debug: Print response details if it's an HTTP error
                if hasattr(e, 'response') and e.response is not None:
                    print(f"🔍 Response Status Code: {e.response.status_code}")
                    print(f"🔍 Response Content: {e.response.text}")
                
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"❌ Failed to parse update request after {max_retries} retries.")
                    return []  # Return empty list to keep original resume unchanged
                else:
                    print(f"⚠️ Retry {retry_count}/{max_retries}. Error: {str(e)[:100]}...")
                    time.sleep(2)
        
        return []  # Fallback to empty list

    def _extract_python_list_from_response(self, response_text: str) -> str:
        """
        Extract Python list from Groq response, handling various response formats
        
        Args:
            response_text (str): Raw response from Groq API
        
        Returns:
            str: Cleaned Python list string
        """
        print(f"🔍 Original response: {repr(response_text)}")
        
        # Remove markdown code blocks
        response_text = re.sub(r'```python\n?', '', response_text)
        response_text = re.sub(r'```\n?', '', response_text)
        
        # Try to find a complete list with proper bracket matching
        response_text = response_text.strip()
        
        # If the response starts with [ and we can find the matching ], extract that
        if response_text.startswith('['):
            bracket_count = 0
            end_pos = 0
            
            for i, char in enumerate(response_text):
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_pos = i + 1
                        break
            
            if end_pos > 0:
                extracted = response_text[:end_pos]
                print(f"🔍 Bracket-matched extraction: {repr(extracted)}")
                return extracted
        
        # Fallback: use regex to find list pattern (more permissive)
        list_pattern = r'\[.*?\]'
        matches = re.findall(list_pattern, response_text, re.DOTALL)
        
        if matches:
            # Return the longest match (likely the most complete)
            longest_match = max(matches, key=len)
            print(f"🔍 Regex extraction: {repr(longest_match)}")
            return longest_match.strip()
        
        # If no list found, return empty list
        print("🔍 No valid list found, returning empty list")
        return "[]"

    def execute_resume_updates(self, resume_json: Dict[str, Any], commands: List[str]) -> Dict[str, Any]:
        """
        Execute the update commands on the resume JSON (modifies original)
        
        Args:
            resume_json (Dict[str, Any]): Current resume data (will be modified in place)
            commands (List[str]): List of Python commands to execute
        
        Returns:
            Dict[str, Any]: The same resume data (modified in place)
        """
        # Use the original resume directly (no copy)
        resume = resume_json
        
        executed_commands = 0
        
        for command in commands:
            try:
                # Execute the command in local scope with resume available
                exec(command, {"resume": resume})
                executed_commands += 1
                print(f"✅ Executed: {command}")
            except Exception as e:
                print(f"❌ Failed to execute command '{command}': {e}")
                continue
        
        print(f"🎯 Successfully executed {executed_commands}/{len(commands)} commands")
        return resume