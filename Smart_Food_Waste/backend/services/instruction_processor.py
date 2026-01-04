"""
Professional Instruction Processor
Transforms raw recipe instructions into well-organized, formal, professional chef-style instructions
"""

import re
from typing import List, Dict, Optional
import textwrap


class InstructionProcessor:
    """
    Processes raw recipe instructions and transforms them into:
    1. Cleaned, properly formatted text
    2. Formal English language
    3. Professional chef-style guidance
    """
    
    def __init__(self):
        # Common cooking verbs that start instructions
        self.cooking_verbs = {
            'add', 'mix', 'combine', 'blend', 'beat', 'whisk', 'stir', 'fold', 'cut', 'chop',
            'dice', 'slice', 'peel', 'mince', 'grate', 'squeeze', 'drain', 'boil', 'simmer',
            'fry', 'sauté', 'roast', 'bake', 'broil', 'grill', 'steam', 'poach', 'braise',
            'cook', 'heat', 'warm', 'cool', 'chill', 'freeze', 'thaw', 'marinate', 'season',
            'salt', 'pepper', 'top', 'garnish', 'serve', 'plate', 'arrange', 'spread',
            'pour', 'coat', 'dip', 'dot', 'sprinkle', 'layer', 'stack', 'roll', 'fold',
            'knead', 'shape', 'form', 'press', 'pound', 'break', 'crack', 'separate',
            'sift', 'strain', 'filter', 'reduce', 'thicken', 'thin', 'mount', 'emulsify'
        }
        
        # Professional cooking techniques and their formal descriptions
        self.technique_upgrades = {
            'just': 'until',
            'keep': 'maintain',
            'til': 'until',
            'till': 'until',
            'let': 'allow to',
            'put': 'place',
            'put in': 'incorporate',
            'get': 'achieve',
            'makes': 'yields',
            'make sure': 'ensure',
            'don\'t': 'do not',
            'doesn\'t': 'does not',
            'it\'s': 'it is',
            'you\'ll': 'you will',
            'won\'t': 'will not',
            'can\'t': 'cannot',
            'aren\'t': 'are not',
            'isn\'t': 'is not',
            'wasn\'t': 'was not',
            'weren\'t': 'were not',
            'haven\'t': 'have not',
            'hasn\'t': 'has not',
        }
        
        # Temperature indicators
        self.temperature_patterns = {
            'oven': r'(\d+)\s*(?:°?F|°?C|degrees?)',
            'heat': r'(low|medium|high|medium-low|medium-high)',
            'time': r'(\d+)\s*(?:minutes?|mins?|seconds?|secs?|hours?|hrs?)'
        }
        
        # Noise patterns to remove
        self.noise_patterns = [
            r'\[.*?\]',  # [brackets]
            r'\(.*?optional.*?\)',  # (optional stuff)
            r'note:.*?(?=\d+\.|$)',  # notes
            r'tip:.*?(?=\d+\.|$)',  # tips (we'll handle separately)
            r'photo credit.*',
            r'©.*',
        ]
    
    def process_instructions(self, raw_instructions: List[str]) -> Dict:
        """
        Process raw instructions and transform into professional format
        
        Args:
            raw_instructions: List of raw instruction strings from web scraping
        
        Returns:
            Dictionary with:
            - organized_steps: List of cleaned, organized steps
            - professional_steps: List of professional chef-style steps
            - tips: List of extracted chef tips
            - warnings: List of important warnings
            - timeline: Timeline summary
        """
        if not raw_instructions:
            return {
                'organized_steps': [],
                'professional_steps': [],
                'tips': [],
                'warnings': [],
                'timeline': {}
            }
        
        # Step 1: Clean and organize raw data
        organized = self._organize_raw_instructions(raw_instructions)
        
        # Step 2: Transform to professional style
        professional = self._transform_to_professional(organized)
        
        # Step 3: Extract tips and warnings
        tips, warnings = self._extract_guidance(organized + professional)
        
        # Step 4: Build timeline summary
        timeline = self._extract_timeline(professional)
        
        return {
            'organized_steps': organized,
            'professional_steps': professional,
            'tips': tips,
            'warnings': warnings,
            'timeline': timeline
        }
    
    def _organize_raw_instructions(self, raw_instructions: List[str]) -> List[str]:
        """
        Clean and organize raw instructions into coherent steps
        """
        organized = []
        
        for instruction in raw_instructions:
            if not instruction or len(instruction.strip()) < 5:
                continue
            
            # Clean the instruction
            text = instruction.strip()
            
            # Remove common noise
            for pattern in self.noise_patterns:
                text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
            
            text = text.strip()
            
            # Skip if too short after cleaning
            if len(text) < 5:
                continue
            
            # Handle multi-sentence instructions
            sentences = self._split_into_coherent_sentences(text)
            organized.extend(sentences)
        
        # Deduplicate and clean
        organized = list(dict.fromkeys(organized))  # Remove duplicates while preserving order
        
        return organized
    
    def _split_into_coherent_sentences(self, text: str) -> List[str]:
        """
        Split text into coherent instruction sentences
        Handles cases where multiple instructions are in one line
        """
        # Split by common separators but keep structure
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])|;\s+|,\s+(?=[A-Z])', text)
        
        sentences = []
        for part in parts:
            part = part.strip()
            if part and len(part) > 5:
                # Ensure it ends with punctuation
                if not part.endswith(('.', '!', '?')):
                    part += '.'
                sentences.append(part)
        
        return sentences
    
    def _transform_to_professional(self, organized_steps: List[str]) -> List[str]:
        """
        Transform organized steps into professional chef-style instructions
        """
        professional = []
        
        for step in organized_steps:
            # Skip empty steps
            if not step or len(step.strip()) < 5:
                continue
            
            transformed = self._upgrade_single_step(step)
            professional.append(transformed)
        
        return professional
    
    def _upgrade_single_step(self, step: str) -> str:
        """
        Upgrade a single step to professional chef language
        """
        # Preserve original punctuation
        ends_with_period = step.rstrip().endswith(('!', '?', '.'))
        step_text = step.rstrip('!?.').strip()
        
        # Replace casual language with formal
        for casual, formal in self.technique_upgrades.items():
            pattern = r'\b' + re.escape(casual) + r'\b'
            step_text = re.sub(pattern, formal, step_text, flags=re.IGNORECASE)
        
        # Remove redundant instructions (starting with step numbers or bullets)
        step_text = re.sub(r'^\d+[\.\)]\s*', '', step_text)
        step_text = re.sub(r'^[-•]\s*', '', step_text)
        
        # Capitalize properly
        step_text = step_text[0].upper() + step_text[1:] if step_text else ''
        
        # Ensure it ends with period
        if not step_text.endswith(('!', '?', '.')):
            step_text += '.'
        
        return step_text
    
    def _extract_guidance(self, all_steps: List[str]) -> tuple:
        """
        Extract chef tips and warnings from instructions
        """
        tips = []
        warnings = []
        
        tip_keywords = ['tip:', 'chef\'s tip', 'pro tip', 'note:', 'hint:', 'suggestion:']
        warning_keywords = ['caution:', 'warning:', 'be careful', 'don\'t', 'avoid', 'make sure', 'ensure']
        
        for step in all_steps:
            step_lower = step.lower()
            
            # Check for tips
            for keyword in tip_keywords:
                if keyword in step_lower:
                    advice = step.replace(keyword, '', flags=re.IGNORECASE).strip()
                    if advice and len(advice) > 10:
                        tips.append(advice)
                    break
            
            # Check for warnings
            if any(word in step_lower for word in ['caution', 'warning', 'careful', 'ensure', 'must']):
                if len(step) > 10:
                    warnings.append(step)
        
        return tips[:10], warnings[:10]  # Limit to 10 each
    
    def _extract_timeline(self, professional_steps: List[str]) -> Dict:
        """
        Extract and organize time-related information from steps
        """
        timeline = {
            'prep_time': None,
            'cook_time': None,
            'total_time': None,
            'key_timings': []
        }
        
        for step in professional_steps:
            # Look for time mentions
            time_match = re.search(r'(\d+)\s*(?:minutes?|mins?|seconds?|secs?|hours?|hrs?)', step, re.IGNORECASE)
            if time_match:
                timeline['key_timings'].append({
                    'duration': time_match.group(1),
                    'context': step[:100]
                })
            
            # Look for temperature
            temp_match = re.search(r'(\d+)\s*(?:°?[CF]|degrees?)', step, re.IGNORECASE)
            if temp_match and 'oven' not in timeline:
                timeline['oven_temp'] = temp_match.group(0)
        
        return timeline
    
    def format_for_display(self, processed_data: Dict, max_steps: int = 30) -> str:
        """
        Format processed instructions for professional display
        """
        output = []
        
        # Main instructions
        if processed_data.get('professional_steps'):
            output.append("═" * 80)
            output.append("PREPARATION & COOKING INSTRUCTIONS")
            output.append("═" * 80)
            
            for i, step in enumerate(processed_data['professional_steps'][:max_steps], 1):
                output.append(f"\n{i}. {step}")
        
        # Chef tips
        if processed_data.get('tips'):
            output.append("\n" + "═" * 80)
            output.append("CHEF'S TIPS")
            output.append("═" * 80)
            for tip in processed_data['tips']:
                output.append(f"• {tip}")
        
        # Important warnings
        if processed_data.get('warnings'):
            output.append("\n" + "═" * 80)
            output.append("⚠ IMPORTANT NOTES")
            output.append("═" * 80)
            for warning in processed_data['warnings']:
                output.append(f"⚠ {warning}")
        
        # Timeline summary
        if processed_data.get('timeline') and processed_data['timeline'].get('key_timings'):
            output.append("\n" + "═" * 80)
            output.append("TIMING SUMMARY")
            output.append("═" * 80)
            for timing in processed_data['timeline']['key_timings'][:5]:
                output.append(f"• {timing['duration']} minutes: {timing['context'][:60]}...")
        
        return "\n".join(output)
    
    def get_summary(self, processed_data: Dict) -> Dict:
        """
        Get a concise summary of processed instructions
        """
        return {
            'total_steps': len(processed_data.get('professional_steps', [])),
            'has_tips': len(processed_data.get('tips', [])) > 0,
            'has_warnings': len(processed_data.get('warnings', [])) > 0,
            'estimated_key_timings': len(processed_data.get('timeline', {}).get('key_timings', [])),
            'first_three_steps': processed_data.get('professional_steps', [])[:3]
        }


# Standalone function for quick processing
def enhance_instructions(raw_instructions: List[str]) -> Dict:
    """
    Quick function to enhance raw instructions
    
    Usage:
        from instruction_processor import enhance_instructions
        result = enhance_instructions(raw_steps)
        print(result['professional_steps'])
    """
    processor = InstructionProcessor()
    return processor.process_instructions(raw_instructions)
