import streamlit as st
import json
from datetime import datetime
import re
from typing import Dict, List, Tuple, Optional
import time
import os
import glob
import base64
from io import BytesIO

# Add required imports
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    st.error("Please install groq: pip install groq")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# PDF generation imports
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    import markdown
    from bs4 import BeautifulSoup
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    st.warning("PDF export not available. Install: pip install reportlab markdown beautifulsoup4")

# Page configuration
st.set_page_config(
    page_title="Ruckus Datasheet Generator",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if "templates" not in st.session_state:
    st.session_state.templates = {}
if "generated_datasheets" not in st.session_state:
    st.session_state.generated_datasheets = []
if "current_step" not in st.session_state:
    st.session_state.current_step = 1
if "selected_template_id" not in st.session_state:
    st.session_state.selected_template_id = None
if "new_specs" not in st.session_state:
    st.session_state.new_specs = {}
if "new_features" not in st.session_state:
    st.session_state.new_features = []
if "trained_templates" not in st.session_state:
    st.session_state.trained_templates = {}
if "template_analysis" not in st.session_state:
    st.session_state.template_analysis = {}

# Product type configurations
PRODUCT_TYPES = {
    "wireless_ap": {
        "name": "Wireless Access Point",
        "keywords": ["access point", "wireless", "wifi", "802.11", "antenna", "ssid", "wlan", "mimo", "radio"],
        "spec_fields": [
            ("model_number", "Model Number", "text"),
            ("wireless_standards", "Wireless Standards", "text"),
            ("frequency_bands", "Frequency Bands", "text"),
            ("max_data_rate", "Maximum Data Rate", "text"),
            ("antenna_config", "Antenna Configuration", "text"),
            ("mimo_streams", "MIMO Streams", "text"),
            ("max_clients", "Maximum Concurrent Clients", "number"),
            ("ethernet_ports", "Ethernet Ports", "text"),
            ("poe_requirements", "PoE Requirements", "text"),
            ("power_consumption", "Power Consumption", "text"),
            ("dimensions", "Dimensions (H x W x D)", "text"),
            ("weight", "Weight", "text"),
            ("operating_temp", "Operating Temperature", "text"),
            ("certifications", "Certifications", "textarea")
        ]
    },
    "switch": {
        "name": "Network Switch",
        "keywords": ["switch", "ethernet", "port", "vlan", "layer", "poe", "managed", "gigabit", "switching"],
        "spec_fields": [
            ("model_number", "Model Number", "text"),
            ("port_configuration", "Port Configuration", "text"),
            ("switching_capacity", "Switching Capacity", "text"),
            ("forwarding_rate", "Forwarding Rate", "text"),
            ("mac_table_size", "MAC Address Table Size", "text"),
            ("vlan_support", "VLAN Support", "text"),
            ("poe_budget", "Total PoE Budget", "text"),
            ("poe_standards", "PoE Standards Supported", "text"),
            ("management_features", "Management Features", "textarea"),
            ("layer3_features", "Layer 3 Features", "textarea"),
            ("redundancy", "Redundancy Features", "text"),
            ("dimensions", "Dimensions (H x W x D)", "text"),
            ("rack_units", "Rack Units", "text"),
            ("power_consumption", "Power Consumption", "text"),
            ("certifications", "Certifications", "textarea")
        ]
    },
    "controller": {
        "name": "Wireless Controller",
        "keywords": ["controller", "management", "smartzone", "unleashed", "centralized", "vsz", "cluster"],
        "spec_fields": [
            ("model_number", "Model Number", "text"),
            ("max_aps", "Maximum APs Supported", "number"),
            ("max_clients", "Maximum Clients", "number"),
            ("throughput", "System Throughput", "text"),
            ("interfaces", "Network Interfaces", "text"),
            ("redundancy", "Redundancy Options", "text"),
            ("clustering", "Clustering Support", "text"),
            ("guest_features", "Guest Access Features", "textarea"),
            ("security_features", "Security Features", "textarea"),
            ("management_api", "Management APIs", "text"),
            ("dimensions", "Dimensions", "text"),
            ("power_requirements", "Power Requirements", "text"),
            ("certifications", "Certifications", "textarea")
        ]
    }
}

def load_preloaded_datasheets():
    """Load pre-existing datasheets from the RDS folder into the template library"""
    if st.session_state.templates:
        return 0  # Already loaded
    
    upload_count = 0
    
    # Check if RDS folder exists
    rds_folder = "RDS"
    if not os.path.exists(rds_folder):
        st.warning(f"RDS folder not found at: {rds_folder}. Creating sample templates instead.")
        create_sample_templates()
        return len(st.session_state.templates)
    
    # Get all text files from RDS folder
    txt_files = glob.glob(os.path.join(rds_folder, "*.txt"))
    
    if not txt_files:
        st.warning(f"No .txt files found in RDS folder: {rds_folder}. Creating sample templates instead.")
        create_sample_templates()
        return len(st.session_state.templates)
    
    # Sort files alphabetically for consistent loading order
    txt_files.sort()
    
    for file_path in txt_files:
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            
            # Skip empty files
            if not content.strip():
                continue
            
            # Get filename without extension for template name
            filename = os.path.basename(file_path)
            template_name = os.path.splitext(filename)[0]
            
            # Clean up template name
            template_name = template_name.replace('data-sheet-', '').replace('ds-', '')
            template_name = template_name.replace('ruckus-', 'RUCKUS ').replace('-', ' ')
            template_name = ' '.join(word.capitalize() for word in template_name.split())
            
            # Detect product type
            product_type = detect_product_type(content)
            
            # Extract sections
            sections = extract_key_sections(content)
            
            # Create template ID
            template_id = f"rds_{upload_count}_{datetime.now().strftime('%Y%m%d')}"
            
            st.session_state.templates[template_id] = {
                "name": template_name,
                "original_filename": filename,
                "product_type": product_type,
                "content": content,
                "sections": sections,
                "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "quality_score": calculate_template_quality(sections)
            }
            upload_count += 1
            
        except Exception as e:
            st.error(f"Error loading {file_path}: {str(e)}")
            continue
    
    return upload_count

def create_sample_templates():
    """Create sample templates if no RDS folder is found"""
    sample_templates = {
        "sample_ap_1": {
            "name": "RUCKUS R550 Access Point",
            "original_filename": "sample_r550.txt",
            "product_type": "wireless_ap",
            "content": """RUCKUS R550 Wi-Fi 6 Access Point

Overview
The RUCKUS R550 is a high-performance Wi-Fi 6 access point designed for high-density environments. It delivers exceptional performance with advanced beamforming technology and OFDMA support.

Key Features
• Wi-Fi 6 (802.11ax) support with up to 1.2 Gbps aggregate data rate
• Advanced BeamFlex+ adaptive antenna technology
• OFDMA and MU-MIMO support for improved efficiency
• Enterprise-grade security with WPA3 support
• Cloud or on-premises management options

Technical Specifications
Wireless Standards: 802.11ax/ac/n/g/a
Frequency Bands: 2.4 GHz and 5 GHz dual-concurrent
Maximum Data Rate: 1.2 Gbps (574 + 688 Mbps)
Antenna Configuration: 2x2:2 internal BeamFlex+ adaptive antenna arrays
Ethernet Ports: 1x Gigabit Ethernet port with 802.3at PoE+ support
Power Consumption: 12.95W maximum
Dimensions: 21.59 x 21.59 x 4.85 cm
Weight: 0.65 kg

Ordering Information
Model: R550-9012-1301-WR
Contact your Ruckus Networks representative for pricing.""",
            "sections": {
                "overview": "The RUCKUS R550 is a high-performance Wi-Fi 6 access point designed for high-density environments. It delivers exceptional performance with advanced beamforming technology and OFDMA support.",
                "features": [
                    "Wi-Fi 6 (802.11ax) support with up to 1.2 Gbps aggregate data rate",
                    "Advanced BeamFlex+ adaptive antenna technology",
                    "OFDMA and MU-MIMO support for improved efficiency",
                    "Enterprise-grade security with WPA3 support",
                    "Cloud or on-premises management options"
                ],
                "specifications": {
                    "Wireless Standards": "802.11ax/ac/n/g/a",
                    "Frequency Bands": "2.4 GHz and 5 GHz dual-concurrent",
                    "Maximum Data Rate": "1.2 Gbps (574 + 688 Mbps)",
                    "Antenna Configuration": "2x2:2 internal BeamFlex+ adaptive antenna arrays",
                    "Ethernet Ports": "1x Gigabit Ethernet port with 802.3at PoE+ support",
                    "Power Consumption": "12.95W maximum",
                    "Dimensions": "21.59 x 21.59 x 4.85 cm",
                    "Weight": "0.65 kg"
                },
                "ordering_info": "Model: R550-9012-1301-WR\nContact your Ruckus Networks representative for pricing."
            },
            "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "quality_score": 0.9
        }
    }
    
    for template_id, template_data in sample_templates.items():
        st.session_state.templates[template_id] = template_data

def calculate_template_quality(sections: Dict) -> float:
    """Calculate a quality score for a template based on completeness"""
    score = 0.0
    
    # Overview quality (0-0.3)
    if sections.get('overview'):
        overview_len = len(sections['overview'])
        if overview_len > 200:
            score += 0.3
        elif overview_len > 100:
            score += 0.2
        elif overview_len > 50:
            score += 0.1
    
    # Features quality (0-0.3)
    features = sections.get('features', [])
    if len(features) >= 5:
        score += 0.3
    elif len(features) >= 3:
        score += 0.2
    elif len(features) >= 1:
        score += 0.1
    
    # Specifications quality (0-0.3)
    specs = sections.get('specifications', {})
    if len(specs) >= 8:
        score += 0.3
    elif len(specs) >= 5:
        score += 0.2
    elif len(specs) >= 2:
        score += 0.1
    
    # Ordering info quality (0-0.1)
    if sections.get('ordering_info'):
        score += 0.1
    
    return round(score, 2)

def analyze_templates_with_ai(api_key: str, provider: str = "groq_free") -> Dict:
    """Use AI to analyze all templates and create improved template patterns"""
    if not st.session_state.templates:
        return {}
    
    try:
        # Group templates by product type
        templates_by_type = {}
        for template in st.session_state.templates.values():
            ptype = template['product_type']
            if ptype not in templates_by_type:
                templates_by_type[ptype] = []
            templates_by_type[ptype].append(template)
        
        analysis_results = {}
        
        for product_type, templates in templates_by_type.items():
            if len(templates) < 1:
                continue
                
            # Prepare analysis prompt
            templates_content = []
            for i, template in enumerate(templates[:5]):  # Limit to 5 templates to avoid token limits
                templates_content.append(f"TEMPLATE {i+1}: {template['name']}\n{template['content'][:1000]}...\n")
            
            prompt = f"""Analyze these {PRODUCT_TYPES[product_type]['name']} datasheets and extract the best practices for creating new ones.

TEMPLATES TO ANALYZE:
{chr(10).join(templates_content)}

Please provide a comprehensive analysis with:
1. COMMON_STRUCTURE: The typical sections and their order
2. WRITING_STYLE: Key characteristics of the writing style
3. TECHNICAL_PATTERNS: Common technical specification patterns
4. FEATURE_PATTERNS: How features are typically presented
5. BEST_PRACTICES: What makes the highest quality datasheets
6. TEMPLATE_FORMULA: A formula for creating new datasheets of this type

Provide your analysis in a structured JSON format."""

            if provider == "groq_free" and GROQ_AVAILABLE:
                client = Groq(api_key=api_key)
                response = client.chat.completions.create(
                    model="llama-3.1-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are an expert technical writer and document analyst. Analyze datasheet patterns and provide structured insights."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=2000
                )
                analysis_text = response.choices[0].message.content
            else:
                # Fallback analysis if AI not available
                analysis_text = f"""{{
                    "COMMON_STRUCTURE": ["Product Name", "Overview", "Key Features", "Technical Specifications", "Ordering Information"],
                    "WRITING_STYLE": "Professional, technical, clear and concise",
                    "TECHNICAL_PATTERNS": "Specifications in table format with clear categories",
                    "FEATURE_PATTERNS": "Bullet points highlighting key benefits and capabilities",
                    "BEST_PRACTICES": "Complete technical details, clear value proposition, professional formatting",
                    "TEMPLATE_FORMULA": "Start with compelling overview, list key features with benefits, provide comprehensive specs table, end with ordering info"
                }}"""
            
            try:
                # Try to parse as JSON, fallback to text if needed
                if analysis_text.strip().startswith('{'):
                    analysis_results[product_type] = json.loads(analysis_text)
                else:
                    analysis_results[product_type] = {"analysis": analysis_text}
            except:
                analysis_results[product_type] = {"analysis": analysis_text}
        
        return analysis_results
        
    except Exception as e:
        st.error(f"Error analyzing templates: {str(e)}")
        return {}

def detect_product_type(content: str) -> str:
    """Detect product type from datasheet content with improved accuracy"""
    content_lower = content.lower()
    scores = {}
    
    for prod_type, config in PRODUCT_TYPES.items():
        score = 0
        for keyword in config["keywords"]:
            # Give more weight to keywords that appear multiple times
            score += content_lower.count(keyword) * (2 if keyword in config["name"].lower() else 1)
        scores[prod_type] = score
    
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    return "wireless_ap"  # Default

def extract_key_sections(content: str) -> Dict:
    """Extract key sections from datasheet content with improved parsing"""
    sections = {
        "overview": "",
        "features": [],
        "specifications": {},
        "ordering_info": ""
    }
    
    lines = content.split('\n')
    current_section = None
    
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        
        # Check if this line is a section header
        is_section_header = False
        
        if any(kw in line_lower for kw in ['overview', 'introduction', 'description']) and len(line_lower) < 50:
            current_section = 'overview'
            is_section_header = True
        elif any(kw in line_lower for kw in ['features', 'benefits', 'highlights', 'key features']) and len(line_lower) < 50:
            current_section = 'features'
            is_section_header = True
        elif any(kw in line_lower for kw in ['specifications', 'technical specs', 'specs', 'technical specifications']) and len(line_lower) < 50:
            current_section = 'specifications'
            is_section_header = True
        elif any(kw in line_lower for kw in ['ordering', 'model', 'part number', 'ordering information']) and len(line_lower) < 50:
            current_section = 'ordering_info'
            is_section_header = True
        
        # Skip section headers and empty lines
        if is_section_header or not line.strip():
            continue
            
        # Extract content based on section
        if current_section == 'features':
            # Look for bullet points or numbered lists
            if re.match(r'^[\s]*[\•\-\*\▪\d\.]+\s+', line):
                feature = re.sub(r'^[\s]*[\•\-\*\▪\d\.]+\s+', '', line).strip()
                if feature:
                    sections['features'].append(feature)
            elif line.strip() and len(line.strip()) > 10:  # Also capture non-bulleted features
                sections['features'].append(line.strip())
        elif current_section == 'overview':
            if line.strip():
                sections['overview'] += line.strip() + " "
        elif current_section == 'specifications':
            # Try to extract key-value pairs
            if ':' in line or '\t' in line:
                # Handle both colon and tab separators
                separator = ':' if ':' in line else '\t'
                parts = line.split(separator, 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value:
                        sections['specifications'][key] = value
        elif current_section == 'ordering_info':
            if line.strip():
                sections['ordering_info'] += line.strip() + "\n"
    
    # Clean up
    sections['overview'] = ' '.join(sections['overview'].split())  # Normalize whitespace
    sections['ordering_info'] = sections['ordering_info'].strip()
    
    return sections

def generate_datasheet_with_groq(template: Dict, specs: Dict, features: List[str], api_key: str, model: str = "llama-3.1-70b-versatile") -> str:
    """Generate new datasheet using Groq API with enhanced template analysis"""
    if not GROQ_AVAILABLE:
        st.error("Groq library not installed. Please run: pip install groq")
        return None
        
    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        st.error(f"Invalid Groq API key: {str(e)}")
        return None
    
    # Get template analysis if available
    product_type = template['product_type']
    template_analysis = st.session_state.template_analysis.get(product_type, {})
    
    # Build enhanced prompt with template analysis
    analysis_context = ""
    if template_analysis:
        analysis_context = f"""
TEMPLATE ANALYSIS FOR {PRODUCT_TYPES[product_type]['name']}:
Writing Style: {template_analysis.get('WRITING_STYLE', 'Professional and technical')}
Common Structure: {template_analysis.get('COMMON_STRUCTURE', [])}
Best Practices: {template_analysis.get('BEST_PRACTICES', 'Complete technical details with clear value proposition')}
Template Formula: {template_analysis.get('TEMPLATE_FORMULA', 'Standard datasheet format')}
"""
    
    prompt = f"""You are a technical writer for Ruckus Networks. Create a professional datasheet for a new product based on the template and specifications provided.

TEMPLATE INFORMATION:
Product Type: {PRODUCT_TYPES[template['product_type']]['name']}
Template Overview: {template['sections']['overview'][:500]}...
Template Quality Score: {template.get('quality_score', 'N/A')}

{analysis_context}

TEMPLATE FEATURES (for style reference):
{json.dumps(template['sections']['features'][:5], indent=2)}

NEW PRODUCT SPECIFICATIONS:
{json.dumps(specs, indent=2)}

NEW/ENHANCED FEATURES:
{json.dumps(features, indent=2)}

INSTRUCTIONS:
1. Create a complete, professional datasheet in markdown format
2. Follow Ruckus branding and style guidelines (professional, technical, clear)
3. Use the analyzed template patterns and best practices above
4. Include these sections in order:
   - Product name and compelling tagline
   - Overview (2-3 compelling paragraphs focusing on business benefits)
   - Key Features and Benefits (bullet points with clear value propositions)
   - Technical Specifications (well-organized table format)
   - Ordering Information (professional format)
5. Ensure technical accuracy and clarity
6. Make the content compelling and customer-focused
7. Include all provided specifications in the technical specifications table
8. Use consistent formatting and professional language throughout

Generate the complete datasheet now:"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert technical documentation writer specializing in networking equipment datasheets. You write in a professional, clear, and technically accurate style that follows industry best practices."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=4000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating datasheet with Groq: {str(e)}")
        return None

def generate_datasheet_with_openai(template: Dict, specs: Dict, features: List[str], api_key: str, model: str = "gpt-3.5-turbo") -> str:
    """Generate new datasheet using OpenAI API with enhanced template analysis"""
    if not OPENAI_AVAILABLE:
        st.error("OpenAI library not installed. Please run: pip install openai")
        return None
        
    try:
        client = OpenAI(api_key=api_key)
    except Exception as e:
        st.error(f"Invalid OpenAI API key: {str(e)}")
        return None
    
    # Get template analysis if available
    product_type = template['product_type']
    template_analysis = st.session_state.template_analysis.get(product_type, {})
    
    # Build enhanced prompt with template analysis
    analysis_context = ""
    if template_analysis:
        analysis_context = f"""
TEMPLATE ANALYSIS FOR {PRODUCT_TYPES[product_type]['name']}:
Writing Style: {template_analysis.get('WRITING_STYLE', 'Professional and technical')}
Common Structure: {template_analysis.get('COMMON_STRUCTURE', [])}
Best Practices: {template_analysis.get('BEST_PRACTICES', 'Complete technical details with clear value proposition')}
Template Formula: {template_analysis.get('TEMPLATE_FORMULA', 'Standard datasheet format')}
"""
    
    prompt = f"""You are a technical writer for Ruckus Networks. Create a professional datasheet for a new product based on the template and specifications provided.

TEMPLATE INFORMATION:
Product Type: {PRODUCT_TYPES[template['product_type']]['name']}
Template Overview: {template['sections']['overview'][:500]}...

{analysis_context}

TEMPLATE FEATURES (for style reference):
{json.dumps(template['sections']['features'][:5], indent=2)}

NEW PRODUCT SPECIFICATIONS:
{json.dumps(specs, indent=2)}

NEW/ENHANCED FEATURES:
{json.dumps(features, indent=2)}

INSTRUCTIONS:
1. Create a complete, professional datasheet in markdown format
2. Follow Ruckus branding and style guidelines (professional, technical, clear)
3. Include these sections in order:
   - Product name and tagline
   - Overview (2-3 paragraphs)
   - Key Features and Benefits (bullet points)
   - Technical Specifications (formatted as a table)
   - Ordering Information
4. Use the template's writing style and structure but with the new specifications
5. Ensure technical accuracy and clarity
6. Make the overview compelling and focused on business benefits
7. Include all provided specifications in the technical specifications table

Generate the complete datasheet now:"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a technical documentation expert specializing in networking equipment datasheets. You write in a professional, clear, and technically accurate style."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=3000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating datasheet with OpenAI: {str(e)}")
        return None

def markdown_to_pdf(markdown_content: str, filename: str) -> BytesIO:
    """Convert markdown content to PDF"""
    if not PDF_AVAILABLE:
        return None
    
    try:
        # Convert markdown to HTML
        html = markdown.markdown(markdown_content, extensions=['tables'])
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.darkblue
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=12,
            alignment=TA_JUSTIFY
        )
        
        # Build story
        story = []
        
        # Process HTML elements
        for element in soup.find_all(['h1', 'h2', 'h3', 'p', 'ul', 'ol', 'table']):
            if element.name == 'h1':
                story.append(Paragraph(element.get_text(), title_style))
            elif element.name in ['h2', 'h3']:
                story.append(Paragraph(element.get_text(), heading_style))
            elif element.name == 'p':
                story.append(Paragraph(element.get_text(), body_style))
            elif element.name in ['ul', 'ol']:
                for li in element.find_all('li'):
                    story.append(Paragraph(f"• {li.get_text()}", body_style))
            elif element.name == 'table':
                # Convert table to ReportLab table
                rows = []
                for tr in element.find_all('tr'):
                    row = []
                    for td in tr.find_all(['td', 'th']):
                        row.append(td.get_text())
                    if row:
                        rows.append(row)
                
                if rows:
                    table = Table(rows)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 12))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        st.error(f"Error creating PDF: {str(e)}")
        return None

def export_library() -> str:
    """Export the entire library as JSON"""
    export_data = {
        "version": "2.0",
        "export_date": datetime.now().isoformat(),
        "templates": st.session_state.templates,
        "generated_datasheets": st.session_state.generated_datasheets,
        "template_analysis": st.session_state.template_analysis
    }
    return json.dumps(export_data, indent=2)

def import_library(file_content: str) -> bool:
    """Import library from JSON"""
    try:
        data = json.loads(file_content)
        st.session_state.templates = data.get("templates", {})
        st.session_state.generated_datasheets = data.get("generated_datasheets", [])
        st.session_state.template_analysis = data.get("template_analysis", {})
        return True
    except Exception as e:
        st.error(f"Error importing library: {str(e)}")
        return False

# Main UI
st.title("📊 Ruckus Datasheet Generator")
st.markdown("Generate professional datasheets for new Ruckus products using AI with enhanced template analysis")

# Top navigation bar
col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
with col2:
    if st.button("🧠 AI Training", type="secondary" if st.session_state.current_step != 5 else "primary"):
        st.session_state.current_step = 5
        st.rerun()
with col3:
    if st.button("📋 Library", type="secondary" if st.session_state.current_step != 4 else "primary"):
        st.session_state.current_step = 4
        st.rerun()
with col4:
    if st.button("🏠 Home", type="secondary" if st.session_state.current_step not in [1, 2, 3] else "primary"):
        st.session_state.current_step = 1
        st.rerun()

# Sidebar
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # AI Provider selection
    ai_provider = st.selectbox(
        "AI Provider",
        ["groq_free", "openai_paid"],
        format_func=lambda x: {
            "groq_free": "🆓 Groq (Free - Recommended)",
            "openai_paid": "💳 OpenAI (Paid)"
        }.get(x, x),
        help="Groq offers free high-quality AI generation. OpenAI is a paid alternative."
    )
    
    # Show different inputs based on provider
    api_key = None
    model_choice = None
    
    if ai_provider == "groq_free":
        if GROQ_AVAILABLE:
            api_key = st.text_input("Groq API Key (Free)", type="password", 
                                   help="Get free API key from console.groq.com")
            if api_key:
                st.success("✅ Free Groq API configured")
                # Model selection for Groq
                model_choice = st.selectbox(
                    "Groq Model",
                    ["llama-3.1-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
                    index=0,
                    help="70b model is highest quality, 8b is fastest, Mixtral is good balance"
                )
            else:
                st.info("📝 Sign up at console.groq.com for free API access")
                st.markdown("[Get Free Groq API Key →](https://console.groq.com)")
        else:
            st.error("❌ Groq library not installed")
            st.code("pip install groq")
            
    elif ai_provider == "openai_paid":
        if OPENAI_AVAILABLE:
            api_key = st.text_input("OpenAI API Key", type="password")
            if api_key:
                st.success("✅ OpenAI API configured")
                # Model selection for OpenAI
                model_choice = st.selectbox(
                    "OpenAI Model",
                    ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
                    index=0,
                    help="GPT-3.5 is faster and cheaper, GPT-4 is more capable"
                )
            else:
                st.warning("💳 Enter OpenAI API key (paid service)")
        else:
            st.error("❌ OpenAI library not installed")
            st.code("pip install openai")
    
    st.divider()
    
    # Show template analysis status
    if st.session_state.template_analysis:
        st.success("🧠 AI Template Analysis: Active")
        analyzed_types = list(st.session_state.template_analysis.keys())
        for ptype in analyzed_types:
            type_name = PRODUCT_TYPES.get(ptype, {}).get('name', ptype)
            st.write(f"✓ {type_name}")
    else:
        st.info("🧠 AI Template Analysis: Not trained")
        st.write("Visit AI Training tab to analyze templates")
    
    st.divider()
    
    # Show API usage info
    if ai_provider == "groq_free":
        st.info("""
        **🆓 Groq Free Tier:**
        • 14,400 requests/day
        • 200K tokens/day
        • Very fast inference
        • High quality results
        """)
    else:
        st.info("""
        **💳 OpenAI Pricing:**
        • GPT-3.5: ~$0.03/datasheet
        • GPT-4: ~$0.15/datasheet
        • Charged per token used
        """)
    
    st.divider()
    
    # Quick stats
    st.subheader("📊 Library Statistics")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Templates", len(st.session_state.templates))
    with col2:
        st.metric("Generated", len(st.session_state.generated_datasheets))
    
    # Template breakdown by type
    if st.session_state.templates:
        st.subheader("📁 Templates by Type")
        type_counts = {}
        quality_scores = {}
        for template in st.session_state.templates.values():
            ptype = template['product_type']
            type_counts[ptype] = type_counts.get(ptype, 0) + 1
            if ptype not in quality_scores:
                quality_scores[ptype] = []
            quality_scores[ptype].append(template.get('quality_score', 0))
        
        # Sort by type name for consistent display
        for ptype in sorted(type_counts.keys()):
            count = type_counts[ptype]
            avg_quality = round(sum(quality_scores[ptype]) / len(quality_scores[ptype]), 2) if quality_scores[ptype] else 0
            st.write(f"• {PRODUCT_TYPES.get(ptype, {}).get('name', ptype)}: {count} (Q: {avg_quality})")
    
    st.divider()
    
    # Import/Export
    st.subheader("📦 Import/Export")
    
    if st.button("Export Library", use_container_width=True):
        library_json = export_library()
        st.download_button(
            label="Download Library JSON",
            data=library_json,
            file_name=f"ruckus_library_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    uploaded_library = st.file_uploader("Import Library", type=['json'])
    if uploaded_library:
        content = uploaded_library.read().decode('utf-8')
        if import_library(content):
            st.success("Library imported successfully!")
            time.sleep(1)
            st.rerun()

# Main content based on current step
if st.session_state.current_step not in [4, 5]:
    # Step indicator
    steps = ["Select Template", "Enter Specifications", "Generate Datasheet"]
    cols = st.columns(len(steps))
    for idx, (col, step) in enumerate(zip(cols, steps)):
        with col:
            if idx + 1 <= st.session_state.current_step:
                st.info(f"**Step {idx + 1}: {step}**")
            else:
                st.text(f"Step {idx + 1}: {step}")
    
    st.divider()

# Step 1: Select Template
if st.session_state.current_step == 1:
    st.header("Step 1: Select Template Datasheet")
    
    # Load pre-existing datasheets into library if not already loaded
    if not st.session_state.templates:
        st.info("📁 Loading pre-existing datasheets from your library...")
        # Auto-load datasheets from the pre-loaded content
        with st.spinner("Loading pre-existing datasheets..."):
            loaded_count = load_preloaded_datasheets()
            if loaded_count > 0:
                st.success(f"✅ Loaded {loaded_count} pre-existing datasheet templates")
                time.sleep(1)
                st.rerun()
            else:
                st.info("📋 No pre-existing datasheets found. Sample templates have been created.")
    else:
        st.write("Select a template from your library to use for generating a new datasheet.")
        
        # Show AI training recommendation
        if not st.session_state.template_analysis and len(st.session_state.templates) > 0:
            st.warning("🧠 **Recommendation**: Visit the AI Training tab to analyze your templates for better results!")
        
        # Filter and sort options
        col1, col2 = st.columns(2)
        with col1:
            # Filter by product type
            product_types_in_library = list(set(t['product_type'] for t in st.session_state.templates.values()))
            product_types_in_library.insert(0, "All")
            
            selected_filter = st.selectbox(
                "Filter by Product Type",
                product_types_in_library,
                format_func=lambda x: "All Product Types" if x == "All" else PRODUCT_TYPES.get(x, {}).get('name', x)
            )
        
        with col2:
            sort_option = st.selectbox(
                "Sort by",
                ["name", "quality", "date"],
                format_func=lambda x: {"name": "Name", "quality": "Quality Score", "date": "Upload Date"}[x]
            )
        
        # Display templates
        templates_to_show = {
            tid: tdata for tid, tdata in st.session_state.templates.items()
            if selected_filter == "All" or tdata['product_type'] == selected_filter
        }
        
        if templates_to_show:
            st.write(f"**{len(templates_to_show)} template(s) available**")
            
            # Sort templates
            if sort_option == "quality":
                sorted_templates = sorted(templates_to_show.items(), key=lambda x: x[1].get('quality_score', 0), reverse=True)
            elif sort_option == "date":
                sorted_templates = sorted(templates_to_show.items(), key=lambda x: x[1]['upload_date'], reverse=True)
            else:  # name
                sorted_templates = sorted(templates_to_show.items(), key=lambda x: x[1]['name'])
            
            for tid, tdata in sorted_templates:
                # Quality indicator
                quality_score = tdata.get('quality_score', 0)
                if quality_score >= 0.8:
                    quality_emoji = "🏆"
                elif quality_score >= 0.6:
                    quality_emoji = "⭐"
                elif quality_score >= 0.4:
                    quality_emoji = "👍"
                else:
                    quality_emoji = "📄"
                
                with st.expander(f"{quality_emoji} {tdata['name']} (Quality: {quality_score})", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Product Type:** {PRODUCT_TYPES[tdata['product_type']]['name']}")
                        st.write(f"**Uploaded:** {tdata['upload_date']}")
                        st.write(f"**Quality Score:** {quality_score}/1.0")
                        
                        if tdata['sections'].get('overview'):
                            st.write("**Overview Preview:**")
                            preview = tdata['sections']['overview'][:200] + "..." if len(tdata['sections']['overview']) > 200 else tdata['sections']['overview']
                            st.info(preview)
                        
                        if tdata['sections'].get('features'):
                            st.write(f"**Sample Features:** {len(tdata['sections']['features'])} found")
                            for feature in tdata['sections']['features'][:3]:
                                st.write(f"• {feature[:100]}...")
                    
                    with col2:
                        if st.button("Use This Template", key=f"select_{tid}", type="primary"):
                            st.session_state.selected_template_id = tid
                            st.session_state.current_step = 2
                            st.rerun()
                        
                        if st.button("Delete", key=f"delete_{tid}"):
                            del st.session_state.templates[tid]
                            st.rerun()

# Step 2: Enter Specifications
elif st.session_state.current_step == 2:
    st.header("Step 2: Enter New Product Specifications")
    
    if st.session_state.selected_template_id and st.session_state.selected_template_id in st.session_state.templates:
        template = st.session_state.templates[st.session_state.selected_template_id]
        
        # Show template info with quality score
        quality_score = template.get('quality_score', 0)
        quality_indicator = "🏆 High Quality" if quality_score >= 0.8 else "⭐ Good Quality" if quality_score >= 0.6 else "👍 Fair Quality"
        
        st.info(f"Using template: **{template['name']}** ({PRODUCT_TYPES[template['product_type']]['name']}) - {quality_indicator}")
        
        # Get spec fields for this product type
        spec_fields = PRODUCT_TYPES[template['product_type']]['spec_fields']
        
        # Create form for specifications
        with st.form("specifications_form"):
            st.subheader("Product Specifications")
            st.write("Fill in the specifications for your new product. At least one field is required.")
            
            # Two column layout for specs
            col1, col2 = st.columns(2)
            specs = {}
            
            for idx, (field_id, label, field_type) in enumerate(spec_fields):
                col = col1 if idx % 2 == 0 else col2
                
                with col:
                    if field_type == "text":
                        specs[field_id] = st.text_input(label, key=f"spec_{field_id}")
                    elif field_type == "number":
                        specs[field_id] = st.text_input(label, key=f"spec_{field_id}")
                    elif field_type == "textarea":
                        specs[field_id] = st.text_area(label, height=100, key=f"spec_{field_id}")
            
            st.divider()
            
            # New features section
            st.subheader("New/Enhanced Features")
            features_text = st.text_area(
                "List new or enhanced features (one per line)",
                height=150,
                help="Enter each feature on a new line. Be specific and highlight the benefits.",
                placeholder="Example:\nAdvanced beamforming technology for improved coverage\nAI-powered RF optimization\nEnhanced security with WPA3 support"
            )
            
            # Marketing message
            st.subheader("Product Positioning (Optional)")
            marketing_message = st.text_area(
                "Key marketing message or unique selling proposition",
                height=80,
                help="What makes this product special? Who is it for?",
                placeholder="Example: Designed for high-density environments like stadiums and conference centers..."
            )
            
            # Buttons
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.form_submit_button("← Back"):
                    st.session_state.current_step = 1
                    st.rerun()
            
            with col3:
                if st.form_submit_button("Generate Datasheet →", type="primary"):
                    # Validate input
                    filled_specs = {k: v for k, v in specs.items() if v}
                    features_list = [f.strip() for f in features_text.split('\n') if f.strip()]
                    
                    if not filled_specs and not features_list:
                        st.error("Please provide at least one specification or feature before generating.")
                    else:
                        st.session_state.new_specs = filled_specs
                        st.session_state.new_features = features_list
                        if marketing_message:
                            st.session_state.new_specs['marketing_message'] = marketing_message
                        st.session_state.current_step = 3
                        st.rerun()
    else:
        st.error("No template selected. Please go back and select a template.")
        if st.button("← Back to Template Selection"):
            st.session_state.current_step = 1
            st.rerun()

# Step 3: Generate Datasheet
elif st.session_state.current_step == 3:
    st.header("Step 3: Generate New Datasheet")
    
    if st.session_state.selected_template_id and st.session_state.selected_template_id in st.session_state.templates:
        template = st.session_state.templates[st.session_state.selected_template_id]
        
        # Summary
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Template Information")
            st.write(f"**Base Template:** {template['name']}")
            st.write(f"**Product Type:** {PRODUCT_TYPES[template['product_type']]['name']}")
            st.write(f"**Quality Score:** {template.get('quality_score', 'N/A')}")
        
        with col2:
            st.subheader("New Specifications")
            st.write(f"**Specifications Provided:** {len([k for k, v in st.session_state.new_specs.items() if k != 'marketing_message'])}")
            st.write(f"**New Features:** {len(st.session_state.new_features)}")
            
            # Show if AI analysis is available
            if st.session_state.template_analysis.get(template['product_type']):
                st.success("🧠 AI Template Analysis: Active")
            else:
                st.info("💡 AI Template Analysis: Not available")
        
        st.divider()
        
        # Generate button
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("← Back"):
                st.session_state.current_step = 2
                st.rerun()
        
        with col2:
            # Check if API key is available
            can_generate = api_key is not None
            button_text = "🚀 Generate Datasheet"
            
            if not can_generate:
                if ai_provider == "groq_free":
                    button_text = "❌ Get Groq API Key First"
                else:
                    button_text = "❌ Enter API Key First"
            
            if st.button(button_text, type="primary", disabled=not can_generate, use_container_width=True):
                if api_key:
                    with st.spinner(f"Generating datasheet using {ai_provider.replace('_', ' ').title()}... This may take a moment."):
                        # Generate using the selected provider
                        if ai_provider == "groq_free":
                            generated_content = generate_datasheet_with_groq(
                                template,
                                st.session_state.new_specs,
                                st.session_state.new_features,
                                api_key,
                                model_choice
                            )
                        else:  # openai_paid
                            generated_content = generate_datasheet_with_openai(
                                template,
                                st.session_state.new_specs,
                                st.session_state.new_features,
                                api_key,
                                model_choice
                            )
                        
                        if generated_content:
                            # Save generated datasheet
                            datasheet = {
                                "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                                "product_name": st.session_state.new_specs.get('model_number', 'New Product'),
                                "template_used": template['name'],
                                "product_type": template['product_type'],
                                "content": generated_content,
                                "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "specs": st.session_state.new_specs,
                                "features": st.session_state.new_features,
                                "model_used": f"{ai_provider}: {model_choice}",
                                "ai_provider": ai_provider,
                                "template_quality": template.get('quality_score', 0),
                                "ai_analysis_used": bool(st.session_state.template_analysis.get(template['product_type']))
                            }
                            st.session_state.generated_datasheets.append(datasheet)
                            st.success(f"✅ Datasheet generated successfully using {ai_provider.replace('_', ' ').title()}!")
                            
                            # Display the generated datasheet
                            st.divider()
                            st.subheader("Generated Datasheet")
                            
                            # Action buttons
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.download_button(
                                    label="📥 Download Markdown",
                                    data=generated_content,
                                    file_name=f"{datasheet['product_name']}_datasheet.md",
                                    mime="text/markdown",
                                    use_container_width=True
                                )
                            with col2:
                                # Convert to HTML for preview
                                html_content = f"""<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1, h2, h3 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    {generated_content.replace('`', '')}
</body>
</html>"""
                                st.download_button(
                                    label="📥 Download HTML",
                                    data=html_content,
                                    file_name=f"{datasheet['product_name']}_datasheet.html",
                                    mime="text/html",
                                    use_container_width=True
                                )
                            with col3:
                                # PDF download
                                if PDF_AVAILABLE:
                                    pdf_buffer = markdown_to_pdf(generated_content, f"{datasheet['product_name']}_datasheet.pdf")
                                    if pdf_buffer:
                                        st.download_button(
                                            label="📥 Download PDF",
                                            data=pdf_buffer.getvalue(),
                                            file_name=f"{datasheet['product_name']}_datasheet.pdf",
                                            mime="application/pdf",
                                            use_container_width=True
                                        )
                                    else:
                                        st.button("❌ PDF Error", disabled=True, use_container_width=True)
                                else:
                                    st.button("❌ PDF Not Available", disabled=True, use_container_width=True, 
                                             help="Install reportlab, markdown, and beautifulsoup4 for PDF export")
                            with col4:
                                if st.button("Generate Another", use_container_width=True):
                                    st.session_state.current_step = 1
                                    st.session_state.new_specs = {}
                                    st.session_state.new_features = []
                                    st.rerun()
                            
                            # Preview
                            st.divider()
                            with st.container():
                                st.markdown("### Preview")
                                st.markdown(generated_content)
                else:
                    st.error(f"Please configure your {ai_provider.replace('_', ' ').title()} API key in the sidebar.")
    else:
        st.error("Template not found. Please start over.")
        if st.button("← Start Over"):
            st.session_state.current_step = 1
            st.rerun()

# Step 4: Generated datasheets library view
elif st.session_state.current_step == 4:
    st.header("📋 Generated Datasheets Library")
    
    if not st.session_state.generated_datasheets:
        st.info("No datasheets generated yet. Click 'Home' to start generating.")
    else:
        # Search and filter
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search_term = st.text_input("Search datasheets", placeholder="Search by product name...")
        with col2:
            filter_type = st.selectbox(
                "Filter by type",
                ["All"] + list(PRODUCT_TYPES.keys()),
                format_func=lambda x: "All Types" if x == "All" else PRODUCT_TYPES.get(x, {}).get('name', x)
            )
        with col3:
            sort_by = st.selectbox(
                "Sort by",
                ["date", "name", "quality"],
                format_func=lambda x: {"date": "Date", "name": "Name", "quality": "Template Quality"}[x]
            )
        
        # Filter datasheets
        filtered_datasheets = []
        for ds in st.session_state.generated_datasheets:
            if search_term and search_term.lower() not in ds['product_name'].lower():
                continue
            if filter_type != "All" and ds['product_type'] != filter_type:
                continue
            filtered_datasheets.append(ds)
        
        # Sort datasheets
        if sort_by == "name":
            filtered_datasheets.sort(key=lambda x: x['product_name'])
        elif sort_by == "quality":
            filtered_datasheets.sort(key=lambda x: x.get('template_quality', 0), reverse=True)
        else:  # date
            filtered_datasheets.sort(key=lambda x: x['generation_date'], reverse=True)
        
        st.write(f"Showing {len(filtered_datasheets)} of {len(st.session_state.generated_datasheets)} datasheets")
        
        # Display filtered datasheets
        for ds in filtered_datasheets:
            # Quality and AI indicators
            template_quality = ds.get('template_quality', 0)
            ai_analysis = ds.get('ai_analysis_used', False)
            
            quality_emoji = "🏆" if template_quality >= 0.8 else "⭐" if template_quality >= 0.6 else "👍" if template_quality >= 0.4 else "📄"
            ai_emoji = "🧠" if ai_analysis else "💡"
            
            with st.expander(f"{quality_emoji}{ai_emoji} {ds['product_name']} - Generated {ds['generation_date']}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Template Used:** {ds['template_used']}")
                    st.write(f"**Product Type:** {PRODUCT_TYPES[ds['product_type']]['name']}")
                    st.write(f"**AI Model Used:** {ds.get('model_used', 'Unknown')}")
                    st.write(f"**Template Quality:** {template_quality}")
                    
                    # Show AI provider and analysis badges
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if ds.get('ai_provider') == 'groq_free':
                            st.success("🆓 Generated with Groq (Free)")
                        elif ds.get('ai_provider') == 'openai_paid':
                            st.info("💳 Generated with OpenAI (Paid)")
                    
                    with col_b:
                        if ai_analysis:
                            st.success("🧠 AI Analysis Used")
                        else:
                            st.info("💡 Basic Template Used")
                    
                    # Show specs summary
                    if ds['specs']:
                        st.write("**Key Specifications:**")
                        spec_cols = st.columns(2)
                        for idx, (key, value) in enumerate(list(ds['specs'].items())[:6]):
                            if key != 'marketing_message' and value:
                                col = spec_cols[idx % 2]
                                with col:
                                    st.write(f"• {key.replace('_', ' ').title()}: {value}")
                    
                    # Show features count
                    if ds['features']:
                        st.write(f"**Features:** {len(ds['features'])} defined")
                
                with col2:
                    # Download buttons
                    st.download_button(
                        label="📥 Markdown",
                        data=ds['content'],
                        file_name=f"{ds['product_name']}_datasheet.md",
                        mime="text/markdown",
                        key=f"download_md_{ds['id']}",
                        use_container_width=True
                    )
                    
                    # PDF download if available
                    if PDF_AVAILABLE:
                        pdf_buffer = markdown_to_pdf(ds['content'], f"{ds['product_name']}_datasheet.pdf")
                        if pdf_buffer:
                            st.download_button(
                                label="📥 PDF",
                                data=pdf_buffer.getvalue(),
                                file_name=f"{ds['product_name']}_datasheet.pdf",
                                mime="application/pdf",
                                key=f"download_pdf_{ds['id']}",
                                use_container_width=True
                            )
                    
                    # Delete button
                    if st.button("🗑️ Delete", key=f"delete_ds_{ds['id']}", use_container_width=True):
                        st.session_state.generated_datasheets = [
                            d for d in st.session_state.generated_datasheets 
                            if d['id'] != ds['id']
                        ]
                        st.rerun()
                
                # Preview toggle
                if st.checkbox("Show preview", key=f"preview_{ds['id']}"):
                    st.markdown("### Datasheet Preview")
                    with st.container():
                        st.markdown(ds['content'])

# Step 5: AI Training Tab
elif st.session_state.current_step == 5:
    st.header("🧠 AI Template Analysis & Training")
    st.markdown("Analyze your template library to create intelligent, cohesive templates for better datasheet generation.")
    
    if not st.session_state.templates:
        st.warning("❌ No templates found in your library. Please load some templates first.")
        if st.button("← Go to Home to Load Templates"):
            st.session_state.current_step = 1
            st.rerun()
    else:
        # Show current analysis status
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Current Library Status")
            
            # Group templates by type for analysis
            templates_by_type = {}
            for template in st.session_state.templates.values():
                ptype = template['product_type']
                if ptype not in templates_by_type:
                    templates_by_type[ptype] = []
                templates_by_type[ptype].append(template)
            
            for ptype, templates in templates_by_type.items():
                type_name = PRODUCT_TYPES[ptype]['name']
                count = len(templates)
                avg_quality = round(sum(t.get('quality_score', 0) for t in templates) / count, 2)
                analyzed = "✅" if ptype in st.session_state.template_analysis else "❌"
                
                st.write(f"**{type_name}**: {count} templates (Avg Quality: {avg_quality}) {analyzed}")
        
        with col2:
            st.subheader("🧠 AI Analysis Status")
            
            if st.session_state.template_analysis:
                st.success("✅ AI Analysis Complete")
                st.write(f"**Analyzed Types:** {len(st.session_state.template_analysis)}")
                st.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                
                # Show analysis summary
                for ptype, analysis in st.session_state.template_analysis.items():
                    type_name = PRODUCT_TYPES[ptype]['name']
                    st.write(f"• {type_name}: Enhanced template patterns available")
            else:
                st.info("❌ No AI analysis performed yet")
                st.write("Train the AI to analyze your templates for better results")
        
        st.divider()
        
        # Training controls
        st.subheader("🚀 Start AI Training")
        
        if not api_key:
            st.warning("⚠️ Please configure your API key in the sidebar to start training.")
        else:
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write("**Training will analyze your templates to:**")
                st.write("• Extract common structure patterns")
                st.write("• Identify writing style characteristics")
                st.write("• Learn technical specification formats")
                st.write("• Create intelligent generation formulas")
            
            with col2:
                if st.button("🧠 Start Training", type="primary", use_container_width=True):
                    if api_key:
                        with st.spinner("🧠 Analyzing templates with AI... This may take a few minutes."):
                            analysis_results = analyze_templates_with_ai(api_key, ai_provider)
                            
                            if analysis_results:
                                st.session_state.template_analysis = analysis_results
                                st.success(f"✅ AI training completed! Analyzed {len(analysis_results)} product types.")
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error("❌ Training failed. Please check your API key and try again.")
                    else:
                        st.error("Please configure your API key first.")
            
            with col3:
                if st.session_state.template_analysis:
                    if st.button("🗑️ Clear Training", use_container_width=True):
                        st.session_state.template_analysis = {}
                        st.success("Training data cleared.")
                        time.sleep(1)
                        st.rerun()
        
        # Show detailed analysis results if available
        if st.session_state.template_analysis:
            st.divider()
            st.subheader("📋 Detailed Analysis Results")
            
            for ptype, analysis in st.session_state.template_analysis.items():
                type_name = PRODUCT_TYPES[ptype]['name']
                
                with st.expander(f"📊 {type_name} Analysis Results", expanded=False):
                    if isinstance(analysis, dict):
                        for key, value in analysis.items():
                            st.write(f"**{key.replace('_', ' ').title()}:**")
                            if isinstance(value, list):
                                for item in value:
                                    st.write(f"• {item}")
                            else:
                                st.write(f"  {value}")
                            st.write("")
                    else:
                        st.write(analysis)
        
        # Template quality insights
        if st.session_state.templates:
            st.divider()
            st.subheader("📈 Template Quality Insights")
            
            # Calculate quality statistics
            all_scores = [t.get('quality_score', 0) for t in st.session_state.templates.values()]
            avg_quality = round(sum(all_scores) / len(all_scores), 2)
            high_quality = len([s for s in all_scores if s >= 0.8])
            medium_quality = len([s for s in all_scores if 0.6 <= s < 0.8])
            low_quality = len([s for s in all_scores if s < 0.6])
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Average Quality", f"{avg_quality}/1.0")
            with col2:
                st.metric("High Quality (≥0.8)", high_quality)
            with col3:
                st.metric("Medium Quality (0.6-0.8)", medium_quality)
            with col4:
                st.metric("Low Quality (<0.6)", low_quality)
            
            # Recommendations
            st.subheader("💡 Recommendations")
            
            if avg_quality < 0.5:
                st.warning("⚠️ **Low average template quality detected.** Consider adding more complete templates with detailed specifications and features.")
            elif avg_quality < 0.7:
                st.info("💡 **Template quality is fair.** Adding more detailed templates will improve AI generation quality.")
            else:
                st.success("✅ **Good template quality!** Your templates provide excellent training data for AI generation.")
            
            if low_quality > 0:
                st.write(f"📝 **{low_quality} templates** have low quality scores. Consider reviewing and enhancing them.")
            
            if not st.session_state.template_analysis:
                st.write("🧠 **Run AI training** to unlock advanced template analysis and improved generation quality.")

# Footer
st.divider()
footer_text = f"Ruckus Datasheet Generator v3.0 | Powered by "
if ai_provider == "groq_free":
    footer_text += "🆓 Groq (Free)"
else:
    footer_text += "💳 OpenAI"

if st.session_state.template_analysis:
    footer_text += " | 🧠 AI Enhanced"

if PDF_AVAILABLE:
    footer_text += " | 📄 PDF Ready"

st.markdown(
    f"""
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
        {footer_text}
    </div>
    """,
    unsafe_allow_html=True
)