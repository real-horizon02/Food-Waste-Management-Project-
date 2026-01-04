"""
NLP processing utilities for dish name and ingredient processing
"""
import re
import string
import os
import json


class NLPProcessor:
    """Natural Language Processing utilities with OpenAI integration"""
    
    def __init__(self):
        # Common dish name variations and synonyms
        self.dish_synonyms = {
            'pasta': ['spaghetti', 'noodles', 'macaroni'],
            'curry': ['kari', 'kadhi'],
            'rice': ['chawal', 'bhaat'],
            'bread': ['roti', 'naan', 'chapati']
        }
        
        # Initialize OpenAI client if API key is available
        self.openai_client = None
        self.use_openai = False
        self._try_init_openai()
    
    def _try_init_openai(self):
        """Lazy initialization of OpenAI client"""
        if self.use_openai:
            return  # Already initialized
        
        try:
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if openai_api_key and openai_api_key.startswith('sk-'):
                try:
                    from openai import OpenAI
                    self.openai_client = OpenAI(api_key=openai_api_key)
                    self.use_openai = True
                    print("[INFO] OpenAI integration enabled for NLP processing")
                except ImportError:
                    print("[WARN] OpenAI library not installed. Using fallback NLP processing.")
                except Exception as e:
                    print(f"[WARN] Could not initialize OpenAI: {e}")
        except Exception as e:
            pass
    
    def normalize_text(self, text):
        """
        Normalize text: lowercase, remove extra spaces, punctuation
        
        Args:
            text: Input text string
        
        Returns:
            Normalized text
        """
        if not text:
            return ''
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^\w\s]', '', text)
        
        return text.strip()
    
    def tokenize(self, text):
        """
        Tokenize text into words
        
        Args:
            text: Input text string
        
        Returns:
            List of tokens
        """
        if not text:
            return []
        
        # Normalize first
        normalized = self.normalize_text(text)
        
        # Split into words
        tokens = normalized.split()
        
        return tokens
    
    def extract_keywords(self, text, max_keywords=5):
        """
        Extract keywords from text
        
        Args:
            text: Input text string
            max_keywords: Maximum number of keywords to return
        
        Returns:
            List of keywords
        """
        tokens = self.tokenize(text)
        
        # Remove common stop words (simple version)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        keywords = [token for token in tokens if token not in stop_words]
        
        return keywords[:max_keywords]
    
    def find_synonyms(self, word):
        """
        Find synonyms for a word
        
        Args:
            word: Word to find synonyms for
        
        Returns:
            List of synonyms
        """
        word = word.lower()
        
        # Check direct mapping
        if word in self.dish_synonyms:
            return self.dish_synonyms[word]
        
        # Check if word is a synonym of another
        for main_word, synonyms in self.dish_synonyms.items():
            if word in synonyms:
                return [main_word] + [s for s in synonyms if s != word]
        
        return []
    
    def process_recipe_text(self, content):
        """
        Process raw recipe content (HTML/text) and extract structured data
        
        Args:
            content: Raw recipe content (HTML string or plain text)
        
        Returns:
            Dictionary with structured recipe data:
            {
                "title": str,
                "ingredients": list of dicts,
                "steps": list of strings,
                "summary": str
            }
        """
        import re
        from bs4 import BeautifulSoup
        
        # Try to parse as HTML first
        soup = None
        text_content = content
        try:
            soup = BeautifulSoup(content, 'html.parser')
            text_content = soup.get_text(separator='\n', strip=True)
        except:
            # If not HTML, use as plain text
            pass
        
        # Extract title
        title = ""
        if soup:
            # Try to find title in HTML
            title_tags = soup.find_all(['h1', 'h2', 'title'])
            for tag in title_tags:
                text = tag.get_text().strip()
                if text and 5 < len(text) < 200:
                    title = text
                    break
        
        # Fallback to first line of text
        if not title:
            lines = text_content.split('\n')
            for line in lines[:5]:
                line = line.strip()
                if line and 5 < len(line) < 200:
                    title = line
                    break
        
        if not title:
            title = "Recipe"
        
        # Extract ingredients - prefer HTML structure
        ingredients = []
        if soup:
            # Try structured HTML extraction first
            ingredient_selectors = [
                {'itemprop': 'recipeIngredient'},
                {'class': re.compile(r'recipe.*ingredient', re.I)},
                {'class': re.compile(r'ingredient', re.I)},
                {'id': re.compile(r'ingredient', re.I)}
            ]
            
            for selector in ingredient_selectors:
                elements = soup.find_all(attrs=selector)
                if elements:
                    for elem in elements:
                        text = elem.get_text().strip()
                        if text and len(text) > 2:
                            ing = self._parse_ingredient_line(text)
                            if ing:
                                ingredients.append(ing)
                    if ingredients:
                        break
            
            # If no structured list, try lists
            if not ingredients:
                lists = soup.find_all(['ul', 'ol'])
                for ul in lists[:5]:  # Check first 5 lists
                    items = ul.find_all('li')
                    for item in items[:30]:  # Limit to 30 items
                        text = item.get_text().strip()
                        if text and len(text) > 2 and len(text) < 200:
                            ing = self._parse_ingredient_line(text)
                            if ing:
                                ingredients.append(ing)
                    if ingredients:
                        break
        
        # Fallback to text-based extraction
        if not ingredients:
            ingredient_keywords = ['ingredient', 'ingredients', 'you will need', 'what you need']
            in_ingredients_section = False
            lines = text_content.split('\n')
            
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                
                # Check if we're entering ingredients section
                if any(keyword in line_lower for keyword in ingredient_keywords):
                    in_ingredients_section = True
                    continue
                
                # Check if we're leaving ingredients section
                if in_ingredients_section:
                    if any(keyword in line_lower for keyword in ['instruction', 'step', 'method', 'directions', 'how to']):
                        break
                    
                    line = line.strip()
                    if line and 2 < len(line) < 200:
                        ing = self._parse_ingredient_line(line)
                        if ing:
                            ingredients.append(ing)
        
        # Extract steps/instructions - prefer HTML structure
        steps = []
        if soup:
            # Try structured HTML extraction
            instruction_selectors = [
                {'itemprop': 'recipeInstructions'},
                {'class': re.compile(r'recipe.*instruction', re.I)},
                {'class': re.compile(r'instruction', re.I)},
                {'id': re.compile(r'instruction', re.I)}
            ]
            
            for selector in instruction_selectors:
                elements = soup.find_all(attrs=selector)
                if elements:
                    for elem in elements:
                        # Get ordered list items or paragraphs
                        step_items = elem.find_all(['li', 'p', 'div'])
                        for step_item in step_items:
                            text = step_item.get_text().strip()
                            if text and len(text) > 10:
                                steps.append(text)
                    if steps:
                        break
        
        # Fallback to text-based extraction
        if not steps:
            step_keywords = ['instruction', 'step', 'method', 'directions', 'how to', 'procedure']
            in_steps_section = False
            step_pattern = re.compile(r'^\d+[\.\)]\s*(.+)$', re.IGNORECASE)
            lines = text_content.split('\n')
            
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                
                # Check if we're entering steps section
                if any(keyword in line_lower for keyword in step_keywords):
                    in_steps_section = True
                    continue
                
                if in_steps_section or i > len(lines) * 0.3:
                    line = line.strip()
                    if line and len(line) > 10:
                        # Check if it's a numbered step
                        step_match = step_pattern.match(line)
                        if step_match:
                            steps.append(step_match.group(1).strip())
                        elif len(steps) > 0:
                            if len(line) > 20 and not line[0].islower():
                                steps.append(line)
        
        # If still no steps, split by paragraphs
        if not steps:
            paragraphs = [p.strip() for p in text_content.split('\n\n') if p.strip() and len(p.strip()) > 20]
            steps = paragraphs[:20]
        
        # Generate summary (first 200 chars of content)
        summary = text_content[:200].strip()
        if len(text_content) > 200:
            summary += "..."
        
        return {
            "title": title,
            "ingredients": ingredients,
            "steps": steps,
            "summary": summary
        }
    
    def _parse_ingredient_line(self, line):
        """Parse a single ingredient line into structured format"""
        import re
        if not line or len(line.strip()) < 2:
            return None
        
        line = line.strip()
        
        # Try OpenAI-based parsing first if available
        if self.use_openai and self.openai_client:
            try:
                parsed = self._parse_ingredient_with_openai(line)
                if parsed:
                    return parsed
            except Exception as e:
                print(f"[WARN] OpenAI parsing failed, falling back to regex: {e}")
        
        # Pattern: quantity unit ingredient or just ingredient
        # Examples: "2 cups flour", "1 tsp salt", "onions"
        ingredient_match = re.match(r'^(\d+[\s/]*\d*)?\s*([a-z]+)?\s*(.+)$', line, re.IGNORECASE)
        if ingredient_match:
            quantity = ingredient_match.group(1) or '1'
            unit = ingredient_match.group(2) or ''
            name = ingredient_match.group(3).strip()
            
            # Clean up name (remove trailing punctuation)
            name = re.sub(r'[.,;:]+$', '', name).strip()
            
            if name and len(name) > 1:
                return {
                    'name': name,
                    'quantity': quantity.strip(),
                    'unit': unit.strip(),
                    'category': None
                }
        
        # If no match, treat entire line as ingredient name
        name = re.sub(r'[.,;:]+$', '', line).strip()
        if name and len(name) > 1:
            return {
                'name': name,
                'quantity': '1',
                'unit': '',
                'category': None
            }
        
        return None
    
    def _parse_ingredient_with_openai(self, ingredient_line):
        """
        Use OpenAI to parse and normalize ingredient line
        
        Args:
            ingredient_line: Raw ingredient text (e.g., "2 cups all-purpose flour")
        
        Returns:
            Dict with parsed ingredient or None
        """
        # Try lazy initialization if not already initialized
        if not self.use_openai:
            self._try_init_openai()
        
        if not self.use_openai or not self.openai_client:
            return None
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a recipe parser. Extract ingredient information from text. Return JSON with fields: name, quantity, unit, category (e.g., 'dairy', 'spices', 'produce', 'grains', 'other'). Be concise."
                    },
                    {
                        "role": "user",
                        "content": f"Parse this ingredient: {ingredient_line}"
                    }
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            # Extract JSON from response
            response_text = response.choices[0].message.content.strip()
            
            # Try to parse as JSON
            if response_text.startswith('{'):
                parsed = json.loads(response_text)
                if 'name' in parsed and parsed['name']:
                    return {
                        'name': parsed.get('name', ''),
                        'quantity': str(parsed.get('quantity', '1')),
                        'unit': parsed.get('unit', ''),
                        'category': parsed.get('category', None)
                    }
        except Exception as e:
            # Silently fall back to regex parsing
            pass
        
        return None
    
    def normalize_recipe_with_ai(self, raw_recipe_dict):
        """
        Use OpenAI to enhance and normalize a recipe dictionary
        
        Args:
            raw_recipe_dict: Dictionary with title, ingredients, instructions, summary
        
        Returns:
            Enhanced recipe dictionary
        """
        # Try lazy initialization if not already initialized
        if not self.use_openai:
            self._try_init_openai()
        
        if not self.use_openai or not self.openai_client:
            return raw_recipe_dict
        
        try:
            # Create prompt for recipe enhancement
            prompt = f"""
            Analyze this recipe and provide:
            1. Indian cooking tips and techniques (if applicable)
            2. Alternative ingredient suggestions
            3. Nutrition estimates per serving
            4. Cooking time breakdown
            
            Recipe:
            Title: {raw_recipe_dict.get('title', 'Unknown')}
            Summary: {raw_recipe_dict.get('summary', '')[:200]}
            
            Return JSON with fields: cooking_tips, alternatives, estimated_nutrition (calories, protein, carbs, fat), prep_time, cook_time.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional chef and nutritionist. Provide practical cooking advice and realistic nutrition estimates. Return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.5,
                max_tokens=500
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Try to parse JSON
            if '{' in response_text:
                json_str = response_text[response_text.index('{'):response_text.rindex('}')+1]
                ai_enhancement = json.loads(json_str)
                
                # Merge with original recipe
                raw_recipe_dict['ai_enhancements'] = ai_enhancement
                return raw_recipe_dict
        except Exception as e:
            print(f"[WARN] Recipe enhancement failed: {e}")
        
        return raw_recipe_dict

