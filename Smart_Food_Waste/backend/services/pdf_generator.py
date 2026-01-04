"""
PDF generation service for grocery lists
"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Try to register fonts that support Hindi/Unicode
try:
    # Use system fonts that support Unicode (Hindi)
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    # ReportLab's built-in fonts support basic Unicode
    # For better Hindi support, you may need to install and register a Hindi font
    pass
except:
    pass


class PDFGenerator:
    """Service for generating PDF grocery lists and recipe PDFs"""
    
    def __init__(self):
        # Get the directory where this file is located
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_output_dir = os.path.join(current_dir, 'static', 'pdfs')
        
        # Create subdirectories for recipes and ingredients
        self.recipes_dir = os.path.join(self.base_output_dir, 'recipes')
        self.ingredients_dir = os.path.join(self.base_output_dir, 'ingredients')
        
        # Create directories with error handling
        try:
            os.makedirs(self.recipes_dir, exist_ok=True)
            os.makedirs(self.ingredients_dir, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create PDF directories: {e}")
            # Fallback to base directory
            self.recipes_dir = self.base_output_dir
            self.ingredients_dir = self.base_output_dir
            os.makedirs(self.base_output_dir, exist_ok=True)
    
    def generate_pdf(self, grocery_list):
        """
        Generate PDF from grocery list
        
        Args:
            grocery_list: GroceryList document
        
        Returns:
            URL/path to generated PDF
        """
        filename = f"grocery_list_{grocery_list.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.base_output_dir, filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        story = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=12
        )
        
        # Title
        story.append(Paragraph("Grocery List", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Dish and household info
        info_data = [
            ['Dish:', grocery_list.dish_name],
            ['Household Size:', grocery_list.household_size],
            ['Date:', datetime.now().strftime('%Y-%m-%d %H:%M')]
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Group items by category
        items_by_category = {}
        for item in grocery_list.items:
            category = item.category or 'other'
            if category not in items_by_category:
                items_by_category[category] = []
            items_by_category[category].append(item)
        
        # Create table data
        table_data = [['Category', 'Ingredient', 'Quantity', 'Unit']]
        
        category_order = ['produce', 'meat', 'poultry', 'seafood', 'dairy',
                         'grains', 'spices', 'condiments', 'beverages',
                         'frozen', 'canned', 'bakery', 'snacks', 'other']
        
        for category in category_order:
            if category in items_by_category:
                for item in items_by_category[category]:
                    quantity = item.quantity or '1'
                    unit = item.unit or ''
                    # Ensure ingredient name is properly encoded for PDF (handles Hindi)
                    ingredient_name = str(item.ingredient_name) if item.ingredient_name else ''
                    # Clean any encoding issues
                    try:
                        ingredient_name = ingredient_name.encode('utf-8', errors='ignore').decode('utf-8')
                    except:
                        pass
                    
                    table_data.append([
                        category.title(),
                        ingredient_name,
                        str(quantity),
                        str(unit) if unit else ''
                    ])
        
        # Create table
        table = Table(table_data, colWidths=[1.5*inch, 3*inch, 1.5*inch, 1*inch])
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
        ]))
        
        story.append(Paragraph("Ingredients", heading_style))
        story.append(table)
        
        # Notes section
        if grocery_list.notes:
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph("Notes", heading_style))
            story.append(Paragraph(grocery_list.notes, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        # Return relative path
        return f"/static/pdfs/{filename}"
    
    def generate_recipe_steps_pdf(self, recipe):
        """
        Generate PDF for recipe steps/instructions
        
        Args:
            recipe: Recipe document
        
        Returns:
            URL/path to generated PDF
        """
        try:
            filename = f"recipe_steps_{recipe.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = os.path.join(self.recipes_dir, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            story = []
            
            # Define styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=30,
                alignment=TA_CENTER
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#34495e'),
                spaceAfter=12
            )
            
            step_style = ParagraphStyle(
                'StepStyle',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=12,
                leftIndent=20
            )
            
            # Title
            recipe_title = recipe.title or recipe.dish_name
            story.append(Paragraph(recipe_title, title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Recipe info
            info_data = [
                ['Servings:', str(recipe.servings)],
                ['Source:', recipe.source_url or 'N/A']
            ]
            
            if recipe.prep_time:
                info_data.append(['Prep Time:', f"{recipe.prep_time} minutes"])
            if recipe.cook_time:
                info_data.append(['Cook Time:', f"{recipe.cook_time} minutes"])
            
            info_table = Table(info_data, colWidths=[2*inch, 4*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Summary if available
            if recipe.summary:
                story.append(Paragraph("Summary", heading_style))
                story.append(Paragraph(recipe.summary, styles['Normal']))
                story.append(Spacer(1, 0.3*inch))
            
            # Instructions/Steps
            story.append(Paragraph("Instructions", heading_style))
            
            if recipe.instructions and len(recipe.instructions) > 0:
                for i, step in enumerate(recipe.instructions, 1):
                    step_text = f"<b>Step {i}:</b> {step}"
                    story.append(Paragraph(step_text, step_style))
            else:
                story.append(Paragraph("No instructions available.", styles['Normal']))
            
            # Nutrition Information (after instructions)
            if recipe.nutrition:
                story.append(Spacer(1, 0.3*inch))
                story.append(Paragraph("Nutrition Information", heading_style))
                
                nutrition = recipe.nutrition
                nutrition_data = []
                
                # Main nutrients
                if nutrition.get('calories'):
                    nutrition_data.append(['Calories', f"{int(nutrition.get('calories', 0))} kcal"])
                if nutrition.get('protein'):
                    nutrition_data.append(['Protein', f"{nutrition.get('protein', 0):.1f} g"])
                if nutrition.get('fat'):
                    nutrition_data.append(['Fat', f"{nutrition.get('fat', 0):.1f} g"])
                if nutrition.get('carbs'):
                    nutrition_data.append(['Carbohydrates', f"{nutrition.get('carbs', 0):.1f} g"])
                if nutrition.get('fiber'):
                    nutrition_data.append(['Fiber', f"{nutrition.get('fiber', 0):.1f} g"])
                if nutrition.get('sugar'):
                    nutrition_data.append(['Sugar', f"{nutrition.get('sugar', 0):.1f} g"])
                if nutrition.get('sodium'):
                    nutrition_data.append(['Sodium', f"{int(nutrition.get('sodium', 0))} mg"])
                
                if nutrition_data:
                    nutrition_table = Table(nutrition_data, colWidths=[3*inch, 3*inch])
                    nutrition_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 11),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
                    ]))
                    story.append(nutrition_table)
            
            # Build PDF
            doc.build(story)
            
            # Return relative path
            return f"/static/pdfs/recipes/{filename}"
        except Exception as e:
            print(f"Error generating recipe steps PDF: {e}")
            raise
    
    def generate_ingredients_pdf(self, recipe):
        """
        Generate PDF for recipe ingredients
        
        Args:
            recipe: Recipe document
        
        Returns:
            URL/path to generated PDF
        """
        try:
            filename = f"ingredients_{recipe.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = os.path.join(self.ingredients_dir, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            story = []
            
            # Define styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=30,
                alignment=TA_CENTER
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#34495e'),
                spaceAfter=12
            )
            
            # Title
            recipe_title = recipe.title or recipe.dish_name
            story.append(Paragraph(f"{recipe_title} - Ingredients", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Recipe info
            info_data = [
                ['Servings:', str(recipe.servings)],
                ['Source:', recipe.source_url or 'N/A']
            ]
            
            info_table = Table(info_data, colWidths=[2*inch, 4*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Ingredients table
            if recipe.ingredients and len(recipe.ingredients) > 0:
                # Group by category
                items_by_category = {}
                for ing in recipe.ingredients:
                    category = ing.category or 'other'
                    if category not in items_by_category:
                        items_by_category[category] = []
                    items_by_category[category].append(ing)
                
                # Create table data
                table_data = [['Ingredient', 'Quantity', 'Unit', 'Category']]
                
                category_order = ['produce', 'meat', 'poultry', 'seafood', 'dairy',
                                 'grains', 'spices', 'condiments', 'beverages',
                                 'frozen', 'canned', 'bakery', 'snacks', 'other']
                
                for category in category_order:
                    if category in items_by_category:
                        for item in items_by_category[category]:
                            quantity = item.quantity or '1'
                            unit = item.unit or ''
                            # Ensure ingredient name is properly encoded for PDF (handles Hindi)
                            ingredient_name = str(item.name) if item.name else ''
                            try:
                                ingredient_name = ingredient_name.encode('utf-8', errors='ignore').decode('utf-8')
                            except:
                                pass
                            
                            table_data.append([
                                ingredient_name,
                                str(quantity),
                                str(unit) if unit else '',
                                category.title()
                            ])
                
                # Add uncategorized items
                if 'other' not in items_by_category:
                    for ing in recipe.ingredients:
                        if not ing.category:
                            ingredient_name = str(ing.name) if ing.name else ''
                            try:
                                ingredient_name = ingredient_name.encode('utf-8', errors='ignore').decode('utf-8')
                            except:
                                pass
                            
                            table_data.append([
                                ingredient_name,
                                str(ing.quantity) if ing.quantity else '1',
                                str(ing.unit) if ing.unit else '',
                                'Other'
                            ])
                
                # Create table
                table = Table(table_data, colWidths=[3*inch, 1.5*inch, 1.5*inch, 1*inch])
                table.setStyle(TableStyle([
                    # Header row
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    # Data rows
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
                ]))
                
                story.append(Paragraph("Ingredients", heading_style))
                story.append(table)
            else:
                story.append(Paragraph("Ingredients", heading_style))
                story.append(Paragraph("No ingredients available.", styles['Normal']))
            
            # Build PDF
            doc.build(story)
            
            # Return relative path
            return f"/static/pdfs/ingredients/{filename}"
        except Exception as e:
            print(f"Error generating ingredients PDF: {e}")
            raise

