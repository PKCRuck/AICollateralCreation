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

# Document processing imports
try:
    import docx
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import PyPDF2
    import fitz  # PyMuPDF for better PDF processing
    PDF_READ_AVAILABLE = True
    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import PyPDF2
        PDF_READ_AVAILABLE = True
        PYMUPDF_AVAILABLE = False
    except ImportError:
        PDF_READ_AVAILABLE = False
        PYMUPDF_AVAILABLE = False

# Image processing imports
try:
    from PIL import Image
    import numpy as np
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Ruckus Datasheet Generator",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if "templates" not in st.session_state:
    st.session_state.templates = {}
if "prd_documents" not in st.session_state:
    st.session_state.prd_documents = {}
if "visual_templates" not in st.session_state:
    st.session_state.visual_templates = {}
if "generated_datasheets" not in st.session_state:
    st.session_state.generated_datasheets = []
if "current_step" not in st.session_state:
    st.session_state.current_step = 1
if "selected_template_id" not in st.session_state:
    st.session_state.selected_template_id = None
if "selected_prd_id" not in st.session_state:
    st.session_state.selected_prd_id = None
if "new_specs" not in st.session_state:
    st.session_state.new_specs = {}
if "new_features" not in st.session_state:
    st.session_state.new_features = []
if "trained_templates" not in st.session_state:
    st.session_state.trained_templates = {}
if "template_analysis" not in st.session_state:
    st.session_state.template_analysis = {}
if "extracted_specs" not in st.session_state:
    st.session_state.extracted_specs = {}
if "training_data" not in st.session_state:
    st.session_state.training_data = []
if "ai_feedback" not in st.session_state:
    st.session_state.ai_feedback = {}
if "pdf_format_analysis" not in st.session_state:
    st.session_state.pdf_format_analysis = {}
if "auto_training_completed" not in st.session_state:
    st.session_state.auto_training_completed = False
if "format_patterns" not in st.session_state:
    st.session_state.format_patterns = {}

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
        ],
        "prd_keywords": ["model", "wireless", "frequency", "data rate", "antenna", "mimo", "clients", "ethernet", "poe", "power", "dimensions", "weight", "temperature", "certification"]
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
        ],
        "prd_keywords": ["port", "switching", "forwarding", "mac", "vlan", "poe", "management", "layer 3", "redundancy", "dimensions", "rack", "power", "certification"]
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
        ],
        "prd_keywords": ["aps", "clients", "throughput", "interfaces", "redundancy", "clustering", "guest", "security", "api", "management", "dimensions", "power", "certification"]
    }
}

# Enhanced PDF Format Analysis Functions
def analyze_pdf_formatting(file_path: str) -> Dict:
    """Analyze PDF formatting patterns including layout, tables, sections"""
    if not PYMUPDF_AVAILABLE:
        return {"error": "PyMuPDF not available for format analysis"}
    
    try:
        doc = fitz.open(file_path)
        format_analysis = {
            "page_count": len(doc),
            "sections": [],
            "tables": [],
            "formatting_patterns": {},
            "text_styles": [],
            "layout_structure": {}
        }
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extract text with formatting information
            text_dict = page.get_text("dict")
            
            # Analyze text blocks and formatting
            blocks = []
            for block in text_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text:
                                blocks.append({
                                    "text": text,
                                    "font": span["font"],
                                    "size": span["size"],
                                    "bbox": span["bbox"],
                                    "flags": span["flags"]  # Bold, italic, etc.
                                })
            
            # Detect sections by analyzing font sizes and formatting
            sections = detect_document_sections(blocks)
            format_analysis["sections"].extend(sections)
            
            # Detect tables
            tables = detect_tables_in_page(page)
            format_analysis["tables"].extend(tables)
            
            # Analyze text styles
            styles = analyze_text_styles(blocks)
            format_analysis["text_styles"].extend(styles)
        
        # Generate formatting patterns
        format_analysis["formatting_patterns"] = generate_formatting_patterns(format_analysis)
        
        doc.close()
        return format_analysis
        
    except Exception as e:
        return {"error": f"Error analyzing PDF formatting: {str(e)}"}

def detect_document_sections(blocks: List[Dict]) -> List[Dict]:
    """Detect document sections based on text formatting"""
    sections = []
    
    # Find potential headers based on font size and formatting
    avg_font_size = sum(block["size"] for block in blocks) / len(blocks) if blocks else 12
    
    for block in blocks:
        if block["size"] > avg_font_size * 1.3 or block["flags"] & 2**4:  # Bold flag
            # Potential section header
            section_type = classify_section_header(block["text"])
            if section_type:
                sections.append({
                    "title": block["text"],
                    "type": section_type,
                    "font_size": block["size"],
                    "is_bold": bool(block["flags"] & 2**4),
                    "bbox": block["bbox"]
                })
    
    return sections

def classify_section_header(text: str) -> Optional[str]:
    """Classify section headers based on text content"""
    text_lower = text.lower().strip()
    
    section_patterns = {
        "overview": ["overview", "introduction", "description", "summary"],
        "features": ["features", "benefits", "highlights", "capabilities"],
        "specifications": ["specifications", "technical specifications", "specs", "technical specs"],
        "performance": ["performance", "benchmarks", "metrics", "capacity"],
        "physical": ["physical", "dimensions", "mounting", "environmental"],
        "power": ["power", "electrical", "consumption", "requirements"],
        "management": ["management", "software", "configuration", "control"],
        "security": ["security", "authentication", "encryption", "compliance"],
        "ordering": ["ordering", "part numbers", "models", "availability"]
    }
    
    for section_type, keywords in section_patterns.items():
        if any(keyword in text_lower for keyword in keywords):
            return section_type
    
    return None

def detect_tables_in_page(page) -> List[Dict]:
    """Detect and analyze table structures in PDF page"""
    tables = []
    
    try:
        # Use PyMuPDF's table detection
        table_data = page.find_tables()
        
        for table in table_data:
            table_info = {
                "bbox": table.bbox,
                "rows": len(table.extract()),
                "cols": len(table.extract()[0]) if table.extract() else 0,
                "content_preview": table.extract()[:3] if table.extract() else []  # First 3 rows
            }
            tables.append(table_info)
    
    except Exception as e:
        # Fallback: detect tables by text patterns
        text = page.get_text()
        table_patterns = re.findall(r'(\w+:\s*[^\n]+\n){3,}', text)
        if table_patterns:
            tables.append({
                "type": "pattern_detected",
                "count": len(table_patterns),
                "pattern_preview": table_patterns[0][:200] if table_patterns else ""
            })
    
    return tables

def analyze_text_styles(blocks: List[Dict]) -> List[Dict]:
    """Analyze text styles and formatting patterns"""
    styles = []
    
    # Group by font and size to identify style patterns
    style_groups = {}
    
    for block in blocks:
        style_key = f"{block['font']}_{block['size']}"
        if style_key not in style_groups:
            style_groups[style_key] = {
                "font": block["font"],
                "size": block["size"],
                "examples": [],
                "is_bold": bool(block["flags"] & 2**4),
                "is_italic": bool(block["flags"] & 2**6)
            }
        
        style_groups[style_key]["examples"].append(block["text"][:50])
        
        if len(style_groups[style_key]["examples"]) > 5:
            style_groups[style_key]["examples"] = style_groups[style_key]["examples"][:5]
    
    return list(style_groups.values())

def generate_formatting_patterns(analysis: Dict) -> Dict:
    """Generate formatting patterns from analysis"""
    patterns = {
        "section_hierarchy": {},
        "table_styles": {},
        "text_formatting": {},
        "layout_preferences": {}
    }
    
    # Analyze section hierarchy
    sections = analysis.get("sections", [])
    if sections:
        font_sizes = [s["font_size"] for s in sections]
        patterns["section_hierarchy"] = {
            "header_sizes": sorted(set(font_sizes), reverse=True),
            "bold_headers": [s for s in sections if s["is_bold"]],
            "section_types": list(set(s["type"] for s in sections if s["type"]))
        }
    
    # Analyze table patterns
    tables = analysis.get("tables", [])
    if tables:
        patterns["table_styles"] = {
            "avg_rows": sum(t.get("rows", 0) for t in tables) / len(tables),
            "avg_cols": sum(t.get("cols", 0) for t in tables) / len(tables),
            "has_structured_tables": any("content_preview" in t for t in tables)
        }
    
    return patterns

def load_pdf_format_library() -> Dict:
    """Load and analyze PDF formatting from RDSpdf folder"""
    pdf_folder = "RDSpdfs"
    format_library = {}
    
    if not os.path.exists(pdf_folder):
        st.warning(f"📁 {pdf_folder} folder not found. Create it and add PDF datasheets for format analysis.")
        return format_library
    
    pdf_files = glob.glob(os.path.join(pdf_folder, "*.pdf"))
    
    if not pdf_files:
        st.info(f"📄 No PDF files found in {pdf_folder} folder.")
        return format_library
    
    for pdf_path in pdf_files:
        try:
            filename = os.path.basename(pdf_path)
            format_analysis = analyze_pdf_formatting(pdf_path)
            
            if "error" not in format_analysis:
                format_library[filename] = {
                    "file_path": pdf_path,
                    "analysis": format_analysis,
                    "analyzed_date": datetime.now().isoformat()
                }
        except Exception as e:
            st.warning(f"Could not analyze {pdf_path}: {str(e)}")
    
    return format_library

def auto_train_from_library(templates: Dict, api_key: str, model: str = "llama-3.1-8b-instant") -> Dict:
    """Automatically train AI using existing template library"""
    if not GROQ_AVAILABLE or not api_key:
        return {"error": "Groq not available or no API key"}
    
    try:
        client = Groq(api_key=api_key)
        
        # Prepare training data from templates
        training_examples = []
        for template_id, template_data in templates.items():
            
            # Calculate quality score based on template analysis
            quality_score = template_data.get('quality_score', 0.7)
            
            training_example = {
                "name": template_data['name'],
                "product_type": template_data['product_type'],
                "quality_score": quality_score,
                "content": template_data['content'],
                "sections": template_data.get('sections', {}),
                "specifications": template_data.get('sections', {}).get('specifications', {}),
                "features": template_data.get('sections', {}).get('features', [])
            }
            training_examples.append(training_example)
        
        if not training_examples:
            return {"error": "No training examples available"}
        
        # Create comprehensive training prompt
        training_prompt = f"""You are being trained to generate exceptional network equipment datasheets by analyzing {len(training_examples)} high-quality examples from the Ruckus template library.

TRAINING OBJECTIVES:
1. Learn content structure patterns from existing datasheets
2. Understand technical specification organization
3. Master professional writing style and terminology
4. Identify key sections and their optimal arrangement
5. Learn feature presentation techniques

TEMPLATE LIBRARY ANALYSIS:
{json.dumps(training_examples, indent=2)[:4000]}

Based on this comprehensive library analysis, identify and learn:

CONTENT PATTERNS:
- How are technical specifications organized and presented?
- What sections appear consistently across high-quality datasheets?
- How are features described to highlight benefits?
- What terminology and language patterns are used?

STRUCTURE PATTERNS:
- What is the optimal section ordering?
- How are specifications formatted and grouped?
- What level of technical detail is appropriate?
- How are product benefits communicated effectively?

QUALITY INDICATORS:
- What makes a datasheet comprehensive and professional?
- How are complex technical concepts explained clearly?
- What formatting and organization enhance readability?

RUCKUS BRAND PATTERNS:
- What terminology is specific to Ruckus products?
- How are competitive advantages highlighted?
- What technical features are emphasized consistently?

Provide a comprehensive analysis of learned patterns that will improve future datasheet generation."""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert technical writer learning from a comprehensive library of professional datasheets. Analyze patterns and extract insights for generating superior documentation."},
                {"role": "user", "content": training_prompt}
            ],
            temperature=0.2,
            max_tokens=4000
        )
        
        training_insights = response.choices[0].message.content
        
        return {
            "success": True,
            "insights": training_insights,
            "templates_analyzed": len(training_examples),
            "timestamp": datetime.now().isoformat(),
            "auto_training": True
        }
        
    except Exception as e:
        return {"error": f"Auto-training failed: {str(e)}"}

def analyze_format_patterns_with_ai(format_library: Dict, api_key: str, model: str = "llama-3.1-8b-instant") -> Dict:
    """Analyze PDF formatting patterns using AI"""
    if not GROQ_AVAILABLE or not api_key or not format_library:
        return {"error": "Cannot analyze format patterns"}
    
    try:
        client = Groq(api_key=api_key)
        
        # Summarize format analysis for AI
        format_summary = {}
        for filename, data in format_library.items():
            analysis = data.get("analysis", {})
            format_summary[filename] = {
                "sections": [s.get("type") for s in analysis.get("sections", [])],
                "section_count": len(analysis.get("sections", [])),
                "table_count": len(analysis.get("tables", [])),
                "formatting_patterns": analysis.get("formatting_patterns", {}),
                "page_count": analysis.get("page_count", 0)
            }
        
        format_prompt = f"""You are analyzing PDF formatting patterns from professional network equipment datasheets to learn optimal layout and presentation techniques.

FORMATTING ANALYSIS DATA:
{json.dumps(format_summary, indent=2)}

Analyze these patterns and provide insights for:

LAYOUT PATTERNS:
- Optimal section organization and hierarchy
- Best practices for table and specification presentation
- Effective use of headers and formatting
- Professional document structure

VISUAL FORMATTING:
- How sections are visually separated and organized
- Table formatting and specification layout patterns
- Text formatting for readability and emphasis
- Professional document appearance standards

CONTENT ORGANIZATION:
- Which sections appear most frequently and in what order?
- How are technical specifications best presented?
- What formatting enhances technical readability?

BEST PRACTICES:
- What formatting patterns indicate high-quality professional documents?
- How should complex technical information be laid out?
- What visual elements enhance comprehension?

Provide actionable formatting insights that will improve datasheet generation quality and professional appearance."""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert in document formatting and layout design, analyzing professional technical documentation patterns."},
                {"role": "user", "content": format_prompt}
            ],
            temperature=0.2,
            max_tokens=3000
        )
        
        format_insights = response.choices[0].message.content
        
        return {
            "success": True,
            "format_insights": format_insights,
            "pdfs_analyzed": len(format_library),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": f"Format analysis failed: {str(e)}"}

def generate_master_trained_datasheet(template: Dict, specs: Dict, features: List[str], api_key: str, model: str = "llama-3.1-8b-instant") -> str:
    """Generate datasheet using both content training and format analysis"""
    if not GROQ_AVAILABLE:
        return None
    
    try:
        client = Groq(api_key=api_key)
        
        # Get training insights
        content_training = st.session_state.ai_feedback.get('insights', '')
        format_training = st.session_state.format_patterns.get('format_insights', '')
        
        product_type = template['product_type']
        enhanced_specs = generate_comprehensive_specifications(product_type, specs)
        
        # Create master prompt with both content and format training
        master_prompt = f"""You are a master technical writer for Ruckus Networks, trained on comprehensive content patterns and professional formatting standards.

CONTENT TRAINING INSIGHTS:
{content_training}

FORMAT AND LAYOUT INSIGHTS:
{format_training}

ASSIGNMENT: Create an exceptional professional datasheet that applies both content excellence and formatting best practices.

PRODUCT INFORMATION:
- Product Type: {PRODUCT_TYPES[product_type]['name']}
- Template: {template['name']}
- Specifications: {json.dumps(enhanced_specs, indent=2)}
- Features: {json.dumps(features, indent=2)}

REQUIREMENTS - APPLY BOTH CONTENT AND FORMAT TRAINING:
1. COMPREHENSIVE CONTENT (3000+ words)
   - Executive overview with compelling narrative
   - Detailed benefits with technical explanations
   - Advanced features with competitive advantages
   - Complete technical specifications
   - Performance metrics and benchmarks
   - Use cases and deployment scenarios

2. PROFESSIONAL FORMATTING & STRUCTURE
   - Apply learned section organization patterns
   - Use professional headers and hierarchy
   - Format specifications as structured tables
   - Include proper technical formatting
   - Maintain consistent professional tone
   - Follow Ruckus branding and terminology

3. TECHNICAL EXCELLENCE
   - Accurate specifications with proper units
   - Industry-standard terminology
   - Comprehensive technical coverage
   - Professional engineering language
   - Competitive positioning statements

4. VISUAL ORGANIZATION
   - Clear section breaks and headers
   - Structured specification tables
   - Logical information flow
   - Professional document appearance
   - Easy-to-scan format for technical buyers

GENERATE: A master-quality datasheet that represents the pinnacle of technical documentation, incorporating all learned patterns for maximum professional impact and technical accuracy."""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a master technical writer trained on comprehensive content patterns and professional formatting standards. Create exceptional documentation that applies all learned insights."},
                {"role": "user", "content": master_prompt}
            ],
            temperature=0.1,
            max_tokens=8000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        st.error(f"Error generating master-trained datasheet: {str(e)}")
        return None

# Enhanced Functions (keeping existing ones and adding new)
def generate_comprehensive_specifications(product_type: str, base_specs: Dict) -> Dict:
    """Generate comprehensive specifications based on product type"""
    
    if product_type == "wireless_ap":
        enhanced_specs = {
            **base_specs,
            "receive_sensitivity_2_4ghz": base_specs.get("receive_sensitivity_2_4ghz", "Up to -97 dBm @ MCS0"),
            "receive_sensitivity_5ghz": base_specs.get("receive_sensitivity_5ghz", "Up to -100 dBm @ MCS0"),
            "transmit_power_2_4ghz": base_specs.get("transmit_power_2_4ghz", "Up to 26 dBm per chain"),
            "transmit_power_5ghz": base_specs.get("transmit_power_5ghz", "Up to 25 dBm per chain"),
            "channel_width": base_specs.get("channel_width", "20/40/80/160 MHz"),
            "modulation": base_specs.get("modulation", "BPSK, QPSK, 16-QAM, 64-QAM, 256-QAM, 1024-QAM"),
            "security_protocols": base_specs.get("security_protocols", "WEP, WPA, WPA2, WPA3, WPA3-SAE, OWE, PMF"),
            "management_protocols": base_specs.get("management_protocols", "SNMP v1/v2c/v3, SSH, HTTP, HTTPS"),
            "environmental_rating": base_specs.get("environmental_rating", "0°C to 50°C operating"),
            "humidity_rating": base_specs.get("humidity_rating", "Up to 95%, non-condensing"),
            "certifications": base_specs.get("certifications", "FCC Part 15, CE, Wi-Fi Alliance"),
            "warranty": base_specs.get("warranty", "Limited lifetime warranty"),
            "client_capacity": base_specs.get("client_capacity", "Up to 512 clients per AP"),
            "ssid_support": base_specs.get("ssid_support", "Up to 32 per AP"),
            "roaming_support": base_specs.get("roaming_support", "802.11r/k/v fast roaming"),
            "mounting_options": base_specs.get("mounting_options", "Wall, ceiling, desk mount")
        }
    elif product_type == "switch":
        enhanced_specs = {
            **base_specs,
            "switching_method": base_specs.get("switching_method", "Store-and-forward"),
            "buffer_size": base_specs.get("buffer_size", "4.1 MB"),
            "jumbo_frame_support": base_specs.get("jumbo_frame_support", "9216 bytes"),
            "spanning_tree": base_specs.get("spanning_tree", "STP, RSTP, MSTP"),
            "link_aggregation": base_specs.get("link_aggregation", "IEEE 802.3ad LACP"),
            "multicast_support": base_specs.get("multicast_support", "IGMP v1/v2/v3 snooping"),
            "access_control": base_specs.get("access_control", "MAC-based, IP-based ACLs"),
            "snmp_support": base_specs.get("snmp_support", "v1, v2c, v3"),
            "warranty": base_specs.get("warranty", "Limited lifetime warranty")
        }
    elif product_type == "controller":
        enhanced_specs = {
            **base_specs,
            "database_support": base_specs.get("database_support", "PostgreSQL, MySQL"),
            "backup_options": base_specs.get("backup_options", "Local, Remote, Cloud"),
            "monitoring_features": base_specs.get("monitoring_features", "Real-time statistics, reporting"),
            "high_availability": base_specs.get("high_availability", "Active-standby redundancy"),
            "api_support": base_specs.get("api_support", "REST API, SOAP"),
            "integration_support": base_specs.get("integration_support", "LDAP, Active Directory, RADIUS"),
            "warranty": base_specs.get("warranty", "Limited lifetime warranty")
        }
    else:
        enhanced_specs = base_specs
    
    return enhanced_specs

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF using PyMuPDF or PyPDF2"""
    try:
        if PYMUPDF_AVAILABLE:
            # Use PyMuPDF (fitz) for better text extraction
            doc = fitz.open(stream=file_content, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        elif PDF_READ_AVAILABLE:
            # Fallback to PyPDF2
            from io import BytesIO
            reader = PyPDF2.PdfReader(BytesIO(file_content))
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        else:
            return "PDF processing not available"
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"

def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX file"""
    try:
        if DOCX_AVAILABLE:
            from io import BytesIO
            doc = docx.Document(BytesIO(file_content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        else:
            return "DOCX processing not available"
    except Exception as e:
        return f"Error extracting DOCX text: {str(e)}"

def analyze_prd_with_groq(prd_content: str, api_key: str, model: str = "llama-3.1-8b-instant") -> Dict:
    """Analyze PRD content using Groq AI to extract specifications"""
    if not GROQ_AVAILABLE:
        return {"error": "Groq library not available"}
    
    try:
        client = Groq(api_key=api_key)
        
        # Create comprehensive prompt for PRD analysis
        prompt = f"""You are an expert technical analyst for network equipment Product Requirements Documents (PRDs). 

Analyze the following PRD content and extract ALL technical specifications and product details in JSON format.

REQUIREMENTS:
1. Extract ALL numerical specifications with units
2. Identify product model numbers and names
3. Extract all technical features and capabilities
4. Determine the product type (wireless_ap, switch, or controller)
5. Extract dimensions, power requirements, and environmental specs
6. List all supported standards and certifications
7. Extract performance metrics and capacity information

Return ONLY a valid JSON object with these keys:
{{
    "product_type": "wireless_ap|switch|controller",
    "model_number": "extracted model number",
    "specifications": {{
        "wireless_standards": "value",
        "frequency_bands": "value", 
        "max_data_rate": "value",
        "antenna_config": "value",
        "mimo_streams": "value",
        "max_clients": "value",
        "ethernet_ports": "value",
        "poe_requirements": "value",
        "power_consumption": "value",
        "dimensions": "value",
        "weight": "value",
        "operating_temp": "value",
        "certifications": "value"
    }},
    "features": ["feature1", "feature2", "feature3"],
    "performance_metrics": {{}},
    "confidence_score": 0.0-1.0
}}

PRD CONTENT:
{prd_content[:8000]}"""  # Limit content to stay within token limits

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert technical analyst specializing in network equipment PRDs. Extract specifications accurately and return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Try to parse JSON from response
        try:
            # Extract JSON from response if it's wrapped in markdown
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.rfind("```")
                content = content[json_start:json_end].strip()
            
            parsed_data = json.loads(content)
            return parsed_data
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, try to extract key information manually
            return extract_specs_fallback(prd_content)
            
    except Exception as e:
        return {"error": f"Error analyzing PRD: {str(e)}"}

def extract_specs_fallback(content: str) -> Dict:
    """Fallback specification extraction using regex patterns"""
    specs = {
        "product_type": detect_product_type(content),
        "specifications": {},
        "features": [],
        "confidence_score": 0.5
    }
    
    # Common patterns for specification extraction
    patterns = {
        "model_number": r'(?:Model|Part|Product)\s*(?:Number|#|ID):\s*([A-Z0-9\-]+)',
        "max_data_rate": r'(?:Data\s*Rate|Speed|Throughput):\s*([0-9.,]+\s*[GMK]?bps)',
        "frequency_bands": r'(?:Frequency|Band):\s*([0-9.]+\s*GHz[^.]*)',
        "power_consumption": r'(?:Power|Consumption):\s*([0-9.]+\s*W)',
        "dimensions": r'(?:Dimensions|Size):\s*([0-9.,\s×x]+\s*(?:cm|mm|in))',
        "weight": r'(?:Weight):\s*([0-9.]+\s*(?:kg|lbs|g))',
        "operating_temp": r'(?:Operating\s*Temperature|Temp):\s*([0-9\-°C\s]+)'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            specs["specifications"][key] = match.group(1).strip()
    
    # Extract features using bullet points or numbered lists
    feature_patterns = [
        r'[•\-\*]\s*([^.\n]+)',
        r'\d+\.\s*([^.\n]+)',
        r'^\s*([A-Z][^.]+)$'
    ]
    
    for pattern in feature_patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        for match in matches[:10]:  # Limit to first 10 features
            if len(match.strip()) > 10 and len(match.strip()) < 100:
                specs["features"].append(match.strip())
    
    return specs

def detect_product_type(content: str) -> str:
    """Detect product type from datasheet content"""
    
    content_lower = content.lower()
    scores = {}
    
    for prod_type, config in PRODUCT_TYPES.items():
        score = 0
        for keyword in config["keywords"]:
            score += content_lower.count(keyword) * (2 if keyword in config["name"].lower() else 1)
        scores[prod_type] = score
    
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    return "wireless_ap"

def extract_key_sections(content: str) -> Dict:
    """Extract key sections from datasheet content"""
    
    sections = {
        "overview": "",
        "features": [],
        "specifications": {},
        "ordering_info": ""
    }
    
    lines = content.split('\n')
    current_section = None
    
    for line in lines:
        line_lower = line.lower().strip()
        
        if any(kw in line_lower for kw in ['overview', 'introduction', 'description']) and len(line_lower) < 50:
            current_section = 'overview'
        elif any(kw in line_lower for kw in ['features', 'benefits', 'highlights']) and len(line_lower) < 50:
            current_section = 'features'
        elif any(kw in line_lower for kw in ['specifications', 'technical specs', 'specs']) and len(line_lower) < 50:
            current_section = 'specifications'
        elif any(kw in line_lower for kw in ['ordering', 'model', 'part number']) and len(line_lower) < 50:
            current_section = 'ordering_info'
        elif not line.strip():
            continue
        
        if current_section == 'features':
            if re.match(r'^[\s]*[\•\-\*\▪\d\.]+\s+', line):
                feature = re.sub(r'^[\s]*[\•\-\*\▪\d\.]+\s+', '', line).strip()
                if feature:
                    sections['features'].append(feature)
        elif current_section == 'overview':
            if line.strip():
                sections['overview'] += line.strip() + " "
        elif current_section == 'specifications':
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value:
                        sections['specifications'][key] = value
        elif current_section == 'ordering_info':
            if line.strip():
                sections['ordering_info'] += line.strip() + "\n"
    
    sections['overview'] = ' '.join(sections['overview'].split())
    sections['ordering_info'] = sections['ordering_info'].strip()
    
    return sections

def calculate_template_quality(sections: Dict) -> float:
    """Calculate template quality score"""
    
    score = 0.0
    
    if sections.get('overview'):
        overview_len = len(sections['overview'])
        if overview_len > 200:
            score += 0.3
        elif overview_len > 100:
            score += 0.2
        elif overview_len > 50:
            score += 0.1
    
    features = sections.get('features', [])
    if len(features) >= 5:
        score += 0.3
    elif len(features) >= 3:
        score += 0.2
    elif len(features) >= 1:
        score += 0.1
    
    specs = sections.get('specifications', {})
    if len(specs) >= 8:
        score += 0.3
    elif len(specs) >= 5:
        score += 0.2
    elif len(specs) >= 2:
        score += 0.1
    
    if sections.get('ordering_info'):
        score += 0.1
    
    return round(score, 2)

def load_preloaded_datasheets():
    """Load pre-existing datasheets and trigger auto-training"""
    
    if st.session_state.templates:
        return 0
    
    upload_count = 0
    rds_folder = "RDS"
    
    if not os.path.exists(rds_folder):
        # Create sample template for R670
        sample_templates = {
            "r670_sample": {
                "name": "RUCKUS R670 Wi-Fi 7 Access Point",
                "original_filename": "r670_datasheet.pdf",
                "product_type": "wireless_ap",
                "content": """RUCKUS R670 Wi-Fi 7 Access Point

Overview
The RUCKUS R670 is a mid-range Wi-Fi 7, tri-band concurrent indoor AP that delivers 6 spatial streams. It delivers industry-leading performance environments with a combined data rate of 9.34 Gbps. Furthermore, a 5 Gbps Ethernet port eliminates wired backhaul bottleneck for full use of available Wi-Fi capacity.

Key Features
• Wi-Fi 7 (802.11be) support with up to 9.34 Gbps aggregate data rate
• Advanced BeamFlex+ adaptive antenna technology with over 4,000 antenna patterns
• OFDMA and MU-MIMO support for improved efficiency in high-density environments
• Enterprise-grade security with WPA3 and DPSK3 support
• Converged access point with built-in BLE or Zigbee IoT radio
• 5 GbE port eliminates backhaul bottleneck
• Multiple management options including cloud and on-premises

Technical Specifications
Wireless Standards: IEEE 802.11a/b/g/n/ac/ax/be (Wi-Fi 7)
Frequency Bands: 2.4 GHz, 5 GHz, and 6 GHz tri-band concurrent
Maximum Data Rate: 9.34 Gbps combined (689 Mbps @ 2.4GHz + 5765 Mbps @ 5GHz + 2882 Mbps @ 6GHz)
Antenna Configuration: 6 spatial streams (2x2:2 in all three bands or 2x2:2 in 2.4GHz and 4x4:4 in 5GHz)
Ethernet Ports: One 5/2.5/1 Gbps PoE port and one 1 Gbps port
Power Consumption: 36W maximum (PoH/uPoE/802.3bt)
Dimensions: 22cm (L) x 22cm (W) x 4.9cm (H)
Weight: 1.02 kg (2.25 lbs)
Operating Temperature: 0°C to 50°C (32°F to 122°F)
Client Capacity: Up to 768 clients per AP
SSID Support: Up to 36 per AP

Ordering Information
Model: 901-R670-XX00
Contact your Ruckus Networks representative for pricing and availability.""",
                "sections": {
                    "overview": "The RUCKUS R670 is a mid-range Wi-Fi 7, tri-band concurrent indoor AP that delivers 6 spatial streams. It delivers industry-leading performance environments with a combined data rate of 9.34 Gbps.",
                    "features": [
                        "Wi-Fi 7 (802.11be) support with up to 9.34 Gbps aggregate data rate",
                        "Advanced BeamFlex+ adaptive antenna technology with over 4,000 antenna patterns",
                        "OFDMA and MU-MIMO support for improved efficiency in high-density environments",
                        "Enterprise-grade security with WPA3 and DPSK3 support",
                        "Converged access point with built-in BLE or Zigbee IoT radio",
                        "5 GbE port eliminates backhaul bottleneck",
                        "Multiple management options including cloud and on-premises"
                    ],
                    "specifications": {
                        "Wireless Standards": "IEEE 802.11a/b/g/n/ac/ax/be (Wi-Fi 7)",
                        "Frequency Bands": "2.4 GHz, 5 GHz, and 6 GHz tri-band concurrent",
                        "Maximum Data Rate": "9.34 Gbps combined",
                        "Antenna Configuration": "6 spatial streams (2x2:2 in all three bands)",
                        "Ethernet Ports": "One 5/2.5/1 Gbps PoE port and one 1 Gbps port",
                        "Power Consumption": "36W maximum",
                        "Dimensions": "22cm (L) x 22cm (W) x 4.9cm (H)",
                        "Weight": "1.02 kg (2.25 lbs)",
                        "Operating Temperature": "0°C to 50°C",
                        "Client Capacity": "Up to 768 clients per AP"
                    },
                    "ordering_info": "Model: 901-R670-XX00\nContact your Ruckus Networks representative for pricing and availability."
                },
                "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "quality_score": 0.95
            }
        }
        
        for template_id, template_data in sample_templates.items():
            st.session_state.templates[template_id] = template_data
        
        return len(sample_templates)
    
    txt_files = glob.glob(os.path.join(rds_folder, "*.txt"))
    
    if not txt_files:
        # Create sample template if no files
        sample_templates = {
            "r670_sample": {
                "name": "RUCKUS R670 Wi-Fi 7 Access Point",
                "original_filename": "sample_r670.txt",
                "product_type": "wireless_ap",
                "content": "Sample R670 content...",  # Truncated for brevity
                "sections": {"overview": "Sample overview", "features": [], "specifications": {}},
                "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "quality_score": 0.8
            }
        }
        
        for template_id, template_data in sample_templates.items():
            st.session_state.templates[template_id] = template_data
        
        return len(sample_templates)
    
    txt_files.sort()
    
    for file_path in txt_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            
            if not content.strip():
                continue
            
            filename = os.path.basename(file_path)
            template_name = os.path.splitext(filename)[0]
            template_name = template_name.replace('data-sheet-', '').replace('ds-', '')
            template_name = template_name.replace('ruckus-', 'RUCKUS ').replace('-', ' ')
            template_name = ' '.join(word.capitalize() for word in template_name.split())
            
            product_type = detect_product_type(content)
            sections = extract_key_sections(content)
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

def validate_datasheet_quality(content: str, specs: Dict, features: List[str]) -> Dict:
    """Validate datasheet quality"""
    
    quality_metrics = {
        "word_count": len(content.split()),
        "has_overview": "overview" in content.lower(),
        "has_specifications": "specification" in content.lower(),
        "has_features": "feature" in content.lower(),
        "has_benefits": "benefit" in content.lower(),
        "spec_coverage": 0,
        "feature_coverage": 0,
        "quality_score": 0
    }
    
    if specs:
        spec_count = sum(1 for spec_key in specs.keys() if spec_key.lower() in content.lower())
        quality_metrics["spec_coverage"] = spec_count / len(specs)
    
    if features:
        feature_count = sum(1 for feature in features if any(word in content.lower() for word in feature.lower().split()[:3]))
        quality_metrics["feature_coverage"] = feature_count / len(features)
    
    score = 0
    if quality_metrics["word_count"] >= 3000:
        score += 0.4
    elif quality_metrics["word_count"] >= 2000:
        score += 0.3
    elif quality_metrics["word_count"] >= 1000:
        score += 0.2
    
    if quality_metrics["has_overview"] and quality_metrics["has_specifications"] and quality_metrics["has_features"]:
        score += 0.3
    
    score += quality_metrics["spec_coverage"] * 0.15
    score += quality_metrics["feature_coverage"] * 0.15
    
    quality_metrics["quality_score"] = min(1.0, score)
    return quality_metrics

# Main UI
st.title("📊 Ruckus Professional Datasheet Generator")
st.markdown("AI-powered datasheet generation with auto-training from your library and PDF format analysis")

# Top navigation
col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

with col2:
    if st.button("📋 Library", type="secondary" if st.session_state.current_step != 4 else "primary"):
        st.session_state.current_step = 4
        st.rerun()

with col3:
    if st.button("📄 PRD Library", type="secondary" if st.session_state.current_step != 6 else "primary"):
        st.session_state.current_step = 6
        st.rerun()

with col4:
    if st.button("🧠 AI Training", type="secondary" if st.session_state.current_step != 5 else "primary"):
        st.session_state.current_step = 5
        st.rerun()

with col5:
    if st.button("🏠 Home", type="secondary" if st.session_state.current_step not in [1, 2, 3] else "primary"):
        st.session_state.current_step = 1
        st.rerun()

# Sidebar
with st.sidebar:
    st.title("⚙️ Configuration")
    
    ai_provider = st.selectbox(
        "AI Provider",
        ["groq_free", "openai_paid"],
        format_func=lambda x: {
            "groq_free": "🆓 Groq (Free - Recommended)",
            "openai_paid": "💳 OpenAI (Paid)"
        }.get(x, x)
    )
    
    api_key = None
    model_choice = None
    
    if ai_provider == "groq_free":
        if GROQ_AVAILABLE:
            api_key = st.text_input("Groq API Key (Free)", type="password")
            if api_key:
                st.success("✅ Free Groq API configured")
                model_choice = st.selectbox(
                    "Groq Model",
                    ["llama-3.1-8b-instant", "llama-3.2-3b-preview", "mixtral-8x7b-32768"],
                    index=0
                )
        else:
            st.error("❌ Groq library not installed")
            st.code("pip install groq")
            
    elif ai_provider == "openai_paid":
        if OPENAI_AVAILABLE:
            api_key = st.text_input("OpenAI API Key", type="password")
            if api_key:
                st.success("✅ OpenAI API configured")
                model_choice = st.selectbox(
                    "OpenAI Model",
                    ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
                    index=0
                )
        else:
            st.error("❌ OpenAI library not installed")
            st.code("pip install openai")
    
    st.divider()
    
    # Auto-Training Status
    st.subheader("🧠 AI Training Status")
    
    if st.session_state.auto_training_completed:
        st.success("✅ Auto-trained from library")
        st.info(f"📚 {len(st.session_state.templates)} templates analyzed")
        if st.session_state.pdf_format_analysis:
            st.success("✅ PDF format analysis complete")
            st.info(f"📄 {len(st.session_state.pdf_format_analysis)} PDFs analyzed")
    else:
        st.warning("⏳ Auto-training pending")
        if api_key and st.button("🚀 Auto-Train Now", use_container_width=True):
            with st.spinner("Auto-training from library..."):
                # Auto-train from existing templates
                training_result = auto_train_from_library(st.session_state.templates, api_key, model_choice)
                if training_result.get("success"):
                    st.session_state.ai_feedback = training_result
                    
                    # Analyze PDF formats
                    format_library = load_pdf_format_library()
                    if format_library:
                        st.session_state.pdf_format_analysis = format_library
                        format_result = analyze_format_patterns_with_ai(format_library, api_key, model_choice)
                        if format_result.get("success"):
                            st.session_state.format_patterns = format_result
                    
                    st.session_state.auto_training_completed = True
                    st.success("🧠 Auto-training completed!")
                    st.rerun()
                else:
                    st.error(f"Training failed: {training_result.get('error')}")
    
    st.divider()
    
    # Library statistics
    st.subheader("📊 Library Statistics")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Templates", len(st.session_state.templates))
        st.metric("PRD Docs", len(st.session_state.prd_documents))
    with col2:
        st.metric("Generated", len(st.session_state.generated_datasheets))
        st.metric("PDF Formats", len(st.session_state.pdf_format_analysis))

# Initialize library if needed
if not st.session_state.templates:
    with st.spinner("Loading template library..."):
        count = load_preloaded_datasheets()
        if count > 0:
            st.info(f"📚 Loaded {count} templates from library")
            
            # Auto-trigger format analysis
            if api_key and not st.session_state.auto_training_completed:
                format_library = load_pdf_format_library()
                if format_library:
                    st.session_state.pdf_format_analysis = format_library

# Main content sections
if st.session_state.current_step == 1:
    # Step 1: Select Template
    steps = ["Select Template", "Enter Specifications", "Generate Datasheet"]
    cols = st.columns(len(steps))
    for idx, (col, step) in enumerate(zip(cols, steps)):
        with col:
            if idx + 1 <= st.session_state.current_step:
                st.info(f"**Step {idx + 1}: {step}**")
            else:
                st.text(f"Step {idx + 1}: {step}")
    
    st.divider()
    
    st.header("Step 1: Select Template Datasheet")
    
    # Show training status
    if st.session_state.auto_training_completed:
        st.success("🧠 **AI Auto-Trained** - Enhanced generation ready!")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Library Training", f"{len(st.session_state.templates)} templates")
        with col2:
            pdf_count = len(st.session_state.pdf_format_analysis)
            st.metric("Format Analysis", f"{pdf_count} PDFs" if pdf_count > 0 else "No PDFs")
        with col3:
            st.metric("AI Status", "Master-Trained" if pdf_count > 0 else "Content-Trained")
    else:
        st.info("💡 Configure API key and click 'Auto-Train Now' in sidebar for enhanced generation")
    
    # Template selection
    if st.session_state.templates:
        st.write("Select a template from your auto-analyzed library:")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            product_types = list(set(t['product_type'] for t in st.session_state.templates.values()))
            product_types.insert(0, "All")
            selected_filter = st.selectbox(
                "Filter by Product Type",
                product_types,
                format_func=lambda x: "All Types" if x == "All" else PRODUCT_TYPES.get(x, {}).get('name', x)
            )
        
        with col2:
            sort_option = st.selectbox(
                "Sort by",
                ["quality", "name", "date"],
                format_func=lambda x: {"name": "Name", "quality": "Quality", "date": "Date"}[x]
            )
        
        # Filter templates
        templates_to_show = {
            tid: tdata for tid, tdata in st.session_state.templates.items()
            if selected_filter == "All" or tdata['product_type'] == selected_filter
        }
        
        if templates_to_show:
            st.write(f"**{len(templates_to_show)} template(s) available for AI training**")
            
            # Sort templates
            if sort_option == "quality":
                sorted_templates = sorted(templates_to_show.items(), key=lambda x: x[1].get('quality_score', 0), reverse=True)
            elif sort_option == "date":
                sorted_templates = sorted(templates_to_show.items(), key=lambda x: x[1]['upload_date'], reverse=True)
            else:
                sorted_templates = sorted(templates_to_show.items(), key=lambda x: x[1]['name'])
            
            for tid, tdata in sorted_templates:
                quality_score = tdata.get('quality_score', 0)
                quality_emoji = "🏆" if quality_score >= 0.8 else "⭐" if quality_score >= 0.6 else "👍" if quality_score >= 0.4 else "📄"
                
                with st.expander(f"{quality_emoji} {tdata['name']} (Quality: {quality_score}) 🧠 AI-Analyzed", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Product Type:** {PRODUCT_TYPES[tdata['product_type']]['name']}")
                        st.write(f"**Upload Date:** {tdata['upload_date']}")
                        st.write(f"**Quality Score:** {quality_score}/1.0")
                        st.write(f"**Training Status:** {'✅ Analyzed' if st.session_state.auto_training_completed else '⏳ Pending'}")
                        
                        if tdata['sections'].get('overview'):
                            st.write("**Overview Preview:**")
                            preview = tdata['sections']['overview'][:200] + "..." if len(tdata['sections']['overview']) > 200 else tdata['sections']['overview']
                            st.info(preview)
                        
                        if tdata['sections'].get('features'):
                            st.write(f"**Features:** {len(tdata['sections']['features'])} found")
                            for feature in tdata['sections']['features'][:3]:
                                st.write(f"• {feature[:100]}...")
                    
                    with col2:
                        button_label = "🧠 Use AI-Enhanced Template" if st.session_state.auto_training_completed else "Use This Template"
                        if st.button(button_label, key=f"select_{tid}", type="primary"):
                            st.session_state.selected_template_id = tid
                            st.session_state.current_step = 2
                            st.rerun()

elif st.session_state.current_step == 2:
    # Step 2: Enhanced with PRD integration (keep existing logic)
    steps = ["Select Template", "Enter Specifications", "Generate Datasheet"]
    cols = st.columns(len(steps))
    for idx, (col, step) in enumerate(zip(cols, steps)):
        with col:
            if idx + 1 <= st.session_state.current_step:
                st.info(f"**Step {idx + 1}: {step}**")
            else:
                st.text(f"Step {idx + 1}: {step}")
    
    st.divider()
    
    st.header("Step 2: Enter New Product Specifications")
    
    template = st.session_state.templates.get(st.session_state.selected_template_id)
    
    if template:
        # Check if PRD data is available
        prd_data_available = st.session_state.selected_prd_id and st.session_state.selected_prd_id in st.session_state.prd_documents
        
        if prd_data_available:
            prd_data = st.session_state.prd_documents[st.session_state.selected_prd_id]
            st.success(f"✅ Using PRD: **{prd_data['name']}** (Confidence: {prd_data.get('confidence_score', 0)*100:.1f}%)")
            
            # Option to modify PRD data
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info("Specifications have been pre-filled from the PRD. You can modify them below.")
            with col2:
                if st.button("🔄 Clear PRD Data"):
                    st.session_state.selected_prd_id = None
                    st.session_state.new_specs = {}
                    st.session_state.new_features = []
                    st.rerun()
        
        # Show AI training status
        training_badge = ""
        if st.session_state.auto_training_completed:
            training_badge = "🧠 AI-Enhanced"
            if st.session_state.format_patterns:
                training_badge = "🧠 Master AI-Enhanced"
        
        st.info(f"Using Template: **{template['name']}** ({PRODUCT_TYPES[template['product_type']]['name']}) {training_badge}")
        
        # Get spec fields
        spec_fields = PRODUCT_TYPES[template['product_type']]['spec_fields']
        
        with st.form("specifications_form"):
            st.subheader("Product Specifications")
            if prd_data_available:
                st.write("✨ Fields pre-filled from PRD analysis - modify as needed:")
            else:
                st.write("Fill in the specifications for your new product:")
            
            col1, col2 = st.columns(2)
            specs = {}
            
            # Pre-fill with PRD data if available
            prefill_specs = st.session_state.new_specs if prd_data_available else {}
            
            for idx, (field_id, label, field_type) in enumerate(spec_fields):
                col = col1 if idx % 2 == 0 else col2
                
                with col:
                    # Get prefilled value
                    prefill_value = prefill_specs.get(field_id, "")
                    
                    if field_type == "text":
                        specs[field_id] = st.text_input(label, value=prefill_value, key=f"spec_{field_id}")
                    elif field_type == "number":
                        specs[field_id] = st.text_input(label, value=prefill_value, key=f"spec_{field_id}")
                    elif field_type == "textarea":
                        specs[field_id] = st.text_area(label, value=prefill_value, height=100, key=f"spec_{field_id}")
            
            st.divider()
            
            st.subheader("New/Enhanced Features")
            # Pre-fill features from PRD
            prefill_features = '\n'.join(st.session_state.new_features) if prd_data_available and st.session_state.new_features else ""
            
            features_text = st.text_area(
                "List new or enhanced features (one per line)",
                value=prefill_features,
                height=150,
                placeholder="Example:\nAdvanced beamforming technology\nAI-powered RF optimization\nEnhanced security with WPA3 support"
            )
            
            st.subheader("Marketing Message (Optional)")
            marketing_message = st.text_area(
                "Key marketing message or unique selling proposition",
                height=80,
                placeholder="What makes this product special?"
            )
            
            # Buttons
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.form_submit_button("← Back"):
                    st.session_state.current_step = 1
                    st.rerun()
            
            with col3:
                if st.form_submit_button("Generate Datasheet →", type="primary"):
                    filled_specs = {k: v for k, v in specs.items() if v}
                    features_list = [f.strip() for f in features_text.split('\n') if f.strip()]
                    
                    if not filled_specs and not features_list:
                        st.error("Please provide at least one specification or feature.")
                    else:
                        st.session_state.new_specs = filled_specs
                        st.session_state.new_features = features_list
                        if marketing_message:
                            st.session_state.new_specs['marketing_message'] = marketing_message
                        st.session_state.current_step = 3
                        st.rerun()
    else:
        st.error("No template selected. Please go back and select a template.")
        if st.button("← Back"):
            st.session_state.current_step = 1
            st.rerun()

elif st.session_state.current_step == 3:
    # Step 3: Master AI-Enhanced generation
    steps = ["Select Template", "Enter Specifications", "Generate Datasheet"]
    cols = st.columns(len(steps))
    for idx, (col, step) in enumerate(zip(cols, steps)):
        with col:
            if idx + 1 <= st.session_state.current_step:
                st.info(f"**Step {idx + 1}: {step}**")
            else:
                st.text(f"Step {idx + 1}: {step}")
    
    st.divider()
    
    st.header("Step 3: Generate Master AI-Enhanced Datasheet")
    
    template = st.session_state.templates.get(st.session_state.selected_template_id)
    
    if template:
        # Summary
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Template Information")
            st.write(f"**Template:** {template['name']}")
            st.write(f"**Product Type:** {PRODUCT_TYPES[template['product_type']]['name']}")
            st.write(f"**Quality Score:** {template.get('quality_score', 'N/A')}")
        
        with col2:
            st.subheader("AI Enhancement Level")
            spec_count = len([k for k, v in st.session_state.new_specs.items() if k != 'marketing_message' and v])
            feature_count = len(st.session_state.new_features)
            
            st.write(f"**Specifications:** {spec_count}")
            st.write(f"**Features:** {feature_count}")
            
            # Show AI training status
            if st.session_state.auto_training_completed and st.session_state.format_patterns:
                st.success("🧠 **Master AI-Enhanced**")
                st.write("✅ Content training + Format analysis")
            elif st.session_state.auto_training_completed:
                st.info("🧠 **AI-Enhanced**")
                st.write("✅ Content training active")
            else:
                st.warning("📝 **Standard Generation**")
                st.write("⏳ AI training pending")
        
        # Quality prediction
        st.divider()
        st.subheader("📊 Expected Quality Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            base_words = 2500
            if st.session_state.auto_training_completed:
                base_words = 3000  # Enhanced for training
            if st.session_state.format_patterns:
                base_words = 3500  # Master enhanced
            predicted_words = base_words + (spec_count * 30) + (feature_count * 70)
            st.metric("Predicted Words", f"{predicted_words:,}")
        
        with col2:
            content_score = min(1.0, (spec_count + feature_count) / 20)
            if st.session_state.auto_training_completed:
                content_score = min(1.0, content_score * 1.3)  # Training bonus
            if st.session_state.format_patterns:
                content_score = min(1.0, content_score * 1.1)  # Format bonus
            st.metric("Content Score", f"{content_score:.1%}")
        
        with col3:
            expected_quality = min(1.0, template.get('quality_score', 0.5) + 0.2)
            if st.session_state.auto_training_completed:
                expected_quality = min(1.0, expected_quality + 0.15)  # Training bonus
            if st.session_state.format_patterns:
                expected_quality = min(1.0, expected_quality + 0.1)  # Format bonus
            st.metric("Expected Quality", f"{expected_quality:.1%}")
        
        with col4:
            if st.session_state.auto_training_completed and st.session_state.format_patterns:
                output_format = "Master AI-Enhanced"
            elif st.session_state.auto_training_completed:
                output_format = "AI-Enhanced"
            else:
                output_format = "Standard"
            st.metric("Generation Mode", output_format)
        
        st.divider()
        
        # Generate button
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("← Back"):
                st.session_state.current_step = 2
                st.rerun()
        
        with col2:
            can_generate = api_key is not None
            
            if st.session_state.auto_training_completed and st.session_state.format_patterns:
                button_text = "🧠 Generate Master AI-Enhanced Datasheet"
            elif st.session_state.auto_training_completed:
                button_text = "🧠 Generate AI-Enhanced Datasheet"
            else:
                button_text = "📝 Generate Standard Datasheet"
            
            if not can_generate:
                button_text = "❌ Configure API Key First"
            
            if st.button(button_text, type="primary", disabled=not can_generate, use_container_width=True):
                if api_key:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # Generate enhanced specs
                        status_text.text("🔧 Preparing comprehensive specifications...")
                        progress_bar.progress(20)
                        
                        enhanced_specs = generate_comprehensive_specifications(template['product_type'], st.session_state.new_specs)
                        time.sleep(0.5)
                        
                        # Generate datasheet with appropriate enhancement level
                        if st.session_state.auto_training_completed and st.session_state.format_patterns:
                            status_text.text("🧠 Generating Master AI-Enhanced datasheet with content & format training...")
                            generated_content = generate_master_trained_datasheet(
                                template, enhanced_specs, st.session_state.new_features, api_key, model_choice
                            )
                        elif st.session_state.auto_training_completed:
                            status_text.text("🧠 Generating AI-Enhanced datasheet with content training...")
                            # Use enhanced generation with content training only
                            try:
                                client = Groq(api_key=api_key)
                                content_training = st.session_state.ai_feedback.get('insights', '')
                                
                                enhanced_prompt = f"""You are a trained technical writer for Ruckus Networks with specialized knowledge from library analysis.

TRAINING INSIGHTS FROM LIBRARY:
{content_training}

Apply this training to create an exceptional datasheet for:
Product Type: {PRODUCT_TYPES[template['product_type']]['name']}
Specifications: {json.dumps(enhanced_specs, indent=2)}
Features: {json.dumps(st.session_state.new_features, indent=2)}

Generate a comprehensive 3000+ word professional datasheet applying all learned patterns."""
                                
                                response = client.chat.completions.create(
                                    model=model_choice,
                                    messages=[
                                        {"role": "system", "content": "You are a trained technical writer applying learned patterns from datasheet analysis."},
                                        {"role": "user", "content": enhanced_prompt}
                                    ],
                                    temperature=0.1,
                                    max_tokens=8000
                                )
                                
                                generated_content = response.choices[0].message.content
                            except Exception as e:
                                st.error(f"Enhanced generation failed: {str(e)}")
                                generated_content = None
                        else:
                            status_text.text(f"📝 Generating standard datasheet...")
                            # Fall back to basic generation
                            generated_content = "Standard generation would go here..."
                        
                        progress_bar.progress(80)
                        
                        if generated_content:
                            # Validate quality
                            status_text.text("🔍 Validating datasheet quality...")
                            progress_bar.progress(90)
                            
                            quality_metrics = validate_datasheet_quality(
                                generated_content, enhanced_specs, st.session_state.new_features
                            )
                            
                            # Save datasheet
                            status_text.text("💾 Saving master datasheet...")
                            progress_bar.progress(100)
                            
                            # Determine enhancement level
                            enhancement_level = "standard"
                            if st.session_state.auto_training_completed and st.session_state.format_patterns:
                                enhancement_level = "master_ai_enhanced"
                            elif st.session_state.auto_training_completed:
                                enhancement_level = "ai_enhanced"
                            
                            datasheet = {
                                "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                                "product_name": enhanced_specs.get('model_number', 'Professional Network Solution'),
                                "template_used": template['name'],
                                "product_type": template['product_type'],
                                "content": generated_content,
                                "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "specs": enhanced_specs,
                                "features": st.session_state.new_features,
                                "model_used": f"{ai_provider}: {model_choice}",
                                "ai_provider": ai_provider,
                                "template_quality": template.get('quality_score', 0),
                                "quality_metrics": quality_metrics,
                                "word_count": quality_metrics["word_count"],
                                "content_quality_score": quality_metrics["quality_score"],
                                "comprehensive_specs_count": len(enhanced_specs),
                                "output_format": "markdown",
                                "enhancement_level": enhancement_level,
                                "library_trained": st.session_state.auto_training_completed,
                                "format_enhanced": bool(st.session_state.format_patterns),
                                "prd_source": st.session_state.selected_prd_id if st.session_state.selected_prd_id else None
                            }
                            
                            st.session_state.generated_datasheets.append(datasheet)
                            
                            # Clear progress
                            progress_bar.empty()
                            status_text.empty()
                            
                            # Success message with enhancement badges
                            enhancement_badges = []
                            if st.session_state.auto_training_completed:
                                enhancement_badges.append("🧠 Library-Trained")
                            if st.session_state.format_patterns:
                                enhancement_badges.append("📄 Format-Enhanced")
                            if st.session_state.selected_prd_id:
                                enhancement_badges.append("📝 PRD-Powered")
                            
                            badge_text = " ".join(enhancement_badges)
                            
                            st.success(f"""✅ **Master datasheet generated successfully!** {badge_text}
                            
📊 **Quality Score:** {quality_metrics['quality_score']:.1%}
📝 **Word Count:** {quality_metrics['word_count']:,}
🔧 **Specifications:** {len(enhanced_specs)} total
🎯 **Features:** {len(st.session_state.new_features)}
🧠 **Enhancement:** {enhancement_level.replace('_', ' ').title()}""")
                            
                            # Display datasheet with enhanced download options
                            st.divider()
                            st.subheader("Generated Master AI-Enhanced Datasheet")
                            
                            # Action buttons
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.download_button(
                                    label="📥 Download Markdown",
                                    data=generated_content,
                                    file_name=f"{datasheet['product_name']}_master.md",
                                    mime="text/markdown",
                                    use_container_width=True
                                )
                            
                            with col2:
                                html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{datasheet['product_name']} - Master AI-Enhanced</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #ff6600; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #ff6600; color: white; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .enhancement-badge {{ background: #e8f5e8; color: #2d5d2d; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="enhancement-badge">🧠 Master AI-Enhanced Datasheet - Generated with Library Training & Format Analysis</div>
    {generated_content.replace(chr(10), '<br>')}
</body>
</html>"""
                                st.download_button(
                                    label="📥 Download HTML",
                                    data=html_content,
                                    file_name=f"{datasheet['product_name']}_master.html",
                                    mime="text/html",
                                    use_container_width=True
                                )
                            
                            with col3:
                                if PDF_AVAILABLE:
                                    try:
                                        from reportlab.lib.pagesizes import letter
                                        from reportlab.platypus import SimpleDocTemplate, Paragraph
                                        from reportlab.lib.styles import getSampleStyleSheet
                                        
                                        buffer = BytesIO()
                                        doc = SimpleDocTemplate(buffer, pagesize=letter)
                                        styles = getSampleStyleSheet()
                                        
                                        # Add enhancement header
                                        content_with_header = f"MASTER AI-ENHANCED DATASHEET\nGenerated with Library Training & Format Analysis\n\n{generated_content}"
                                        
                                        story = [Paragraph(content_with_header.replace('\n', '<br/>'), styles['Normal'])]
                                        doc.build(story)
                                        
                                        st.download_button(
                                            label="📥 Download PDF",
                                            data=buffer.getvalue(),
                                            file_name=f"{datasheet['product_name']}_master.pdf",
                                            mime="application/pdf",
                                            use_container_width=True
                                        )
                                    except Exception as e:
                                        st.button("❌ PDF Error", disabled=True, use_container_width=True)
                                else:
                                    st.button("❌ PDF N/A", disabled=True, use_container_width=True)
                            
                            with col4:
                                if st.button("🔄 Generate Another", use_container_width=True):
                                    st.session_state.current_step = 1
                                    st.session_state.new_specs = {}
                                    st.session_state.new_features = []
                                    st.session_state.selected_prd_id = None
                                    st.rerun()
                            
                            # Enhanced quality metrics
                            st.divider()
                            st.subheader("📊 Master Quality Metrics")
                            
                            metric_cols = st.columns(6)
                            with metric_cols[0]:
                                st.metric("Quality Score", f"{quality_metrics['quality_score']:.1%}")
                            with metric_cols[1]:
                                st.metric("Word Count", f"{quality_metrics['word_count']:,}")
                            with metric_cols[2]:
                                st.metric("Specifications", f"{len(enhanced_specs)}")
                            with metric_cols[3]:
                                st.metric("Features", f"{len(st.session_state.new_features)}")
                            with metric_cols[4]:
                                st.metric("AI Training", "✅ Active" if st.session_state.auto_training_completed else "❌ None")
                            with metric_cols[5]:
                                st.metric("Format Analysis", "✅ Active" if st.session_state.format_patterns else "❌ None")
                            
                            # Preview
                            st.divider()
                            st.subheader("📋 Master Datasheet Preview")
                            st.markdown(generated_content)
                        
                        else:
                            progress_bar.empty()
                            status_text.empty()
                            st.error("❌ Failed to generate datasheet. Please check your API key.")
                    
                    except Exception as e:
                        progress_bar.empty()
                        status_text.empty()
                        st.error(f"❌ Error: {str(e)}")
        
        with col3:
            if st.button("💡 AI Tips", use_container_width=True):
                tips_content = f"""**Master AI Enhancement Tips:**

🧠 **Library Training Active:** Using patterns from {len(st.session_state.templates)} templates
📄 **Format Analysis:** {"✅ Active" if st.session_state.format_patterns else "❌ Add PDFs to RDSpdf folder"}
📝 **PRD Integration:** {"✅ Active" if st.session_state.selected_prd_id else "Upload PRDs for auto-specs"}

**Expected Master Output:**
- {3500 + len(st.session_state.new_specs) * 30}+ words comprehensive content
- {len(generate_comprehensive_specifications(template['product_type'], st.session_state.new_specs))}+ technical specifications
- Professional formatting from PDF analysis
- Industry-standard terminology from library training

**Enhancement Levels:**
🏆 **Master:** Library + Format + PRD training
🧠 **Enhanced:** Library training active
📝 **Standard:** Basic generation only"""
                
                st.info(tips_content)

elif st.session_state.current_step == 4:
    # Library view with enhanced badges
    st.header("📋 Generated Datasheets Library")
    
    if not st.session_state.generated_datasheets:
        st.info("No datasheets generated yet. Click 'Home' to start generating with Master AI enhancement.")
    else:
        # Enhanced search and filter
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
            enhancement_filter = st.selectbox(
                "Filter by enhancement",
                ["All", "master_ai_enhanced", "ai_enhanced", "standard"],
                format_func=lambda x: {
                    "All": "All Enhancements",
                    "master_ai_enhanced": "🏆 Master AI-Enhanced",
                    "ai_enhanced": "🧠 AI-Enhanced", 
                    "standard": "📝 Standard"
                }.get(x, x)
            )
        
        # Filter datasheets
        filtered_datasheets = []
        for ds in st.session_state.generated_datasheets:
            if search_term and search_term.lower() not in ds['product_name'].lower():
                continue
            if filter_type != "All" and ds['product_type'] != filter_type:
                continue
            if enhancement_filter != "All" and ds.get('enhancement_level') != enhancement_filter:
                continue
            filtered_datasheets.append(ds)
        
        # Sort datasheets
        filtered_datasheets.sort(key=lambda x: x['generation_date'], reverse=True)
        
        st.write(f"Showing {len(filtered_datasheets)} of {len(st.session_state.generated_datasheets)} datasheets")
        
        # Display datasheets with enhanced information
        for ds in filtered_datasheets:
            quality_score = ds.get('content_quality_score', 0)
            quality_emoji = "🏆" if quality_score >= 0.8 else "⭐" if quality_score >= 0.6 else "👍"
            
            # Enhancement badges
            badges = []
            enhancement_level = ds.get('enhancement_level', 'standard')
            if enhancement_level == "master_ai_enhanced":
                badges.append("🏆 Master AI")
            elif enhancement_level == "ai_enhanced":
                badges.append("🧠 AI-Enhanced")
            elif ds.get('library_trained'):
                badges.append("📚 Library-Trained")
            
            if ds.get('format_enhanced'):
                badges.append("📄 Format-Enhanced")
            if ds.get('prd_source'):
                badges.append("📝 PRD-Powered")
            
            badge_text = " ".join(badges)
            
            with st.expander(f"{quality_emoji} {ds['product_name']} {badge_text} - {ds['generation_date']}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Product Type:** {PRODUCT_TYPES[ds['product_type']]['name']}")
                    st.write(f"**Template Used:** {ds['template_used']}")
                    st.write(f"**AI Model:** {ds.get('model_used', 'Unknown')}")
                    st.write(f"**Enhancement Level:** {enhancement_level.replace('_', ' ').title()}")
                    
                    # Enhancement status
                    if ds.get('library_trained'):
                        st.success("🧠 Library training applied")
                    if ds.get('format_enhanced'):
                        st.success("📄 PDF format analysis applied")
                    if ds.get('prd_source'):
                        prd_name = st.session_state.prd_documents.get(ds['prd_source'], {}).get('name', 'Unknown PRD')
                        st.info(f"📝 Generated from PRD: {prd_name}")
                    
                    # Quality metrics
                    st.subheader("📊 Quality Metrics")
                    
                    metric_cols = st.columns(4)
                    with metric_cols[0]:
                        st.metric("Quality Score", f"{quality_score:.1%}")
                    with metric_cols[1]:
                        st.metric("Word Count", f"{ds.get('word_count', 0):,}")
                    with metric_cols[2]:
                        st.metric("Specifications", f"{ds.get('comprehensive_specs_count', 0)}")
                    with metric_cols[3]:
                        st.metric("Features", f"{len(ds.get('features', []))}")
                
                with col2:
                    # Download buttons
                    file_suffix = "_master" if enhancement_level == "master_ai_enhanced" else "_enhanced" if enhancement_level == "ai_enhanced" else ""
                    
                    st.download_button(
                        label="📥 Download MD",
                        data=ds['content'],
                        file_name=f"{ds['product_name']}{file_suffix}.md",
                        mime="text/markdown",
                        key=f"download_{ds['id']}",
                        use_container_width=True
                    )
                    
                    # Delete button
                    if st.button("🗑️ Delete", key=f"delete_{ds['id']}", use_container_width=True):
                        st.session_state.generated_datasheets = [
                            d for d in st.session_state.generated_datasheets 
                            if d['id'] != ds['id']
                        ]
                        st.rerun()

elif st.session_state.current_step == 5:
    # AI Training Status and Management
    st.header("🧠 Master AI Training Center")
    st.markdown("Automated training from your library with PDF format analysis")
    
    if not api_key:
        st.warning("⚠️ Please configure your API key in the sidebar to use AI training features")
    
    tab1, tab2, tab3 = st.tabs(["📊 Training Status", "📚 Library Analysis", "📄 Format Analysis"])
    
    with tab1:
        st.subheader("🧠 Auto-Training Status")
        
        if st.session_state.auto_training_completed:
            training_result = st.session_state.ai_feedback
            
            # Training summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Templates Analyzed", training_result.get('templates_analyzed', 0))
            with col2:
                st.metric("Format PDFs", len(st.session_state.pdf_format_analysis))
            with col3:
                training_date = training_result.get('timestamp', '')[:10] if training_result.get('timestamp') else 'Unknown'
                st.metric("Training Date", training_date)
            
            st.success("✅ **Auto-Training Completed Successfully**")
            
            # Training insights
            if training_result.get('insights'):
                with st.expander("📊 Content Training Insights", expanded=True):
                    st.markdown(training_result['insights'])
            
            # Format insights
            if st.session_state.format_patterns.get('format_insights'):
                with st.expander("📄 Format Training Insights", expanded=True):
                    st.markdown(st.session_state.format_patterns['format_insights'])
            
            # Re-training option
            st.divider()
            st.subheader("🔄 Re-training Options")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Re-train Content from Library", use_container_width=True):
                    if api_key:
                        with st.spinner("Re-training from library..."):
                            training_result = auto_train_from_library(st.session_state.templates, api_key, model_choice)
                            if training_result.get("success"):
                                st.session_state.ai_feedback = training_result
                                st.success("✅ Content re-training completed!")
                                st.rerun()
                            else:
                                st.error(f"Re-training failed: {training_result.get('error')}")
                    else:
                        st.error("API key required for re-training")
            
            with col2:
                if st.button("📄 Re-analyze PDF Formats", use_container_width=True):
                    if api_key:
                        with st.spinner("Re-analyzing PDF formats..."):
                            format_library = load_pdf_format_library()
                            if format_library:
                                st.session_state.pdf_format_analysis = format_library
                                format_result = analyze_format_patterns_with_ai(format_library, api_key, model_choice)
                                if format_result.get("success"):
                                    st.session_state.format_patterns = format_result
                                    st.success(f"✅ Re-analyzed {len(format_library)} PDF formats!")
                                    st.rerun()
                                else:
                                    st.error(f"Format analysis failed: {format_result.get('error')}")
                            else:
                                st.warning("No PDFs found in RDSpdf folder")
                    else:
                        st.error("API key required for format analysis")
        
        else:
            st.warning("⏳ **Auto-Training Not Completed**")
            st.info("Auto-training will analyze your existing template library and PDF formats to enhance generation quality.")
            
            # Manual trigger
            if api_key:
                if st.button("🚀 Start Auto-Training Now", type="primary", use_container_width=True):
                    with st.spinner("Performing comprehensive auto-training..."):
                        # Step 1: Content training
                        st.info("Step 1: Analyzing template library for content patterns...")
                        training_result = auto_train_from_library(st.session_state.templates, api_key, model_choice)
                        
                        if training_result.get("success"):
                            st.session_state.ai_feedback = training_result
                            
                            # Step 2: Format analysis
                            st.info("Step 2: Analyzing PDF formats from RDSpdf folder...")
                            format_library = load_pdf_format_library()
                            if format_library:
                                st.session_state.pdf_format_analysis = format_library
                                format_result = analyze_format_patterns_with_ai(format_library, api_key, model_choice)
                                if format_result.get("success"):
                                    st.session_state.format_patterns = format_result
                            
                            st.session_state.auto_training_completed = True
                            st.success("🧠 **Master Auto-Training Completed!**")
                            st.balloons()
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Auto-training failed: {training_result.get('error')}")
            else:
                st.info("Configure API key in sidebar to enable auto-training")
    
    with tab2:
        st.subheader("📚 Template Library Analysis")
        
        if not st.session_state.templates:
            st.info("No templates loaded. Templates will be automatically loaded from the RDS folder.")
        else:
            st.write(f"**Library Statistics:** {len(st.session_state.templates)} templates available for training")
            
            # Library breakdown
            product_breakdown = {}
            quality_scores = []
            
            for template_data in st.session_state.templates.values():
                prod_type = template_data['product_type']
                product_breakdown[prod_type] = product_breakdown.get(prod_type, 0) + 1
                quality_scores.append(template_data.get('quality_score', 0))
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Templates", len(st.session_state.templates))
            with col2:
                avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
                st.metric("Average Quality", f"{avg_quality:.2f}")
            with col3:
                high_quality = sum(1 for q in quality_scores if q >= 0.8)
                st.metric("High Quality (≥0.8)", high_quality)
            
            # Product type breakdown
            st.subheader("📊 Product Type Distribution")
            for prod_type, count in product_breakdown.items():
                percentage = (count / len(st.session_state.templates)) * 100
                st.write(f"**{PRODUCT_TYPES[prod_type]['name']}:** {count} templates ({percentage:.1f}%)")
            
            # Template quality analysis
            st.subheader("⭐ Template Quality Analysis")
            
            # Show template quality distribution
            quality_ranges = {"High (0.8-1.0)": 0, "Medium (0.6-0.8)": 0, "Low (0.0-0.6)": 0}
            
            for score in quality_scores:
                if score >= 0.8:
                    quality_ranges["High (0.8-1.0)"] += 1
                elif score >= 0.6:
                    quality_ranges["Medium (0.6-0.8)"] += 1
                else:
                    quality_ranges["Low (0.0-0.6)"] += 1
            
            for range_name, count in quality_ranges.items():
                percentage = (count / len(quality_scores)) * 100 if quality_scores else 0
                st.write(f"**{range_name}:** {count} templates ({percentage:.1f}%)")
            
            # Show individual templates
            if st.checkbox("Show Individual Template Analysis"):
                for template_id, template_data in st.session_state.templates.items():
                    quality = template_data.get('quality_score', 0)
                    quality_emoji = "🏆" if quality >= 0.8 else "⭐" if quality >= 0.6 else "📄"
                    
                    with st.expander(f"{quality_emoji} {template_data['name']} (Quality: {quality})"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Product Type:** {PRODUCT_TYPES[template_data['product_type']]['name']}")
                            st.write(f"**Quality Score:** {quality}")
                            st.write(f"**Upload Date:** {template_data['upload_date']}")
                            
                        with col2:
                            sections = template_data.get('sections', {})
                            st.write(f"**Features:** {len(sections.get('features', []))}")
                            st.write(f"**Specifications:** {len(sections.get('specifications', {}))}")
                            st.write(f"**Has Overview:** {'✅' if sections.get('overview') else '❌'}")
    
    with tab3:
        st.subheader("📄 PDF Format Analysis")
        
        pdf_folder = "RDSpdf"
        st.info(f"📁 **PDF Analysis Folder:** Place PDF datasheets in `{pdf_folder}/` folder for format analysis")
        
        if not st.session_state.pdf_format_analysis:
            st.warning("No PDF format analysis available")
            
            # Check if folder exists and has files
            if os.path.exists(pdf_folder):
                pdf_files = glob.glob(os.path.join(pdf_folder, "*.pdf"))
                if pdf_files:
                    st.info(f"Found {len(pdf_files)} PDF files. Run auto-training to analyze formats.")
                    
                    # Show available files
                    st.write("**Available PDF files:**")
                    for pdf_file in pdf_files:
                        st.write(f"• {os.path.basename(pdf_file)}")
                    
                    if api_key and st.button("📄 Analyze PDF Formats Now"):
                        with st.spinner("Analyzing PDF formats..."):
                            format_library = load_pdf_format_library()
                            if format_library:
                                st.session_state.pdf_format_analysis = format_library
                                format_result = analyze_format_patterns_with_ai(format_library, api_key, model_choice)
                                if format_result.get("success"):
                                    st.session_state.format_patterns = format_result
                                    st.success(f"✅ Analyzed {len(format_library)} PDF formats!")
                                    st.rerun()
                else:
                    st.warning(f"No PDF files found in {pdf_folder} folder")
            else:
                st.warning(f"Folder {pdf_folder} does not exist. Create it and add PDF datasheets.")
        
        else:
            st.success(f"✅ **PDF Format Analysis Complete:** {len(st.session_state.pdf_format_analysis)} PDFs analyzed")
            
            # Analysis summary
            total_pages = 0
            total_sections = 0
            total_tables = 0
            
            for pdf_data in st.session_state.pdf_format_analysis.values():
                analysis = pdf_data.get('analysis', {})
                total_pages += analysis.get('page_count', 0)
                total_sections += len(analysis.get('sections', []))
                total_tables += len(analysis.get('tables', []))
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("PDFs Analyzed", len(st.session_state.pdf_format_analysis))
            with col2:
                st.metric("Total Pages", total_pages)
            with col3:
                st.metric("Sections Found", total_sections)
            with col4:
                st.metric("Tables Found", total_tables)
            
            # Format insights
            if st.session_state.format_patterns.get('format_insights'):
                st.subheader("🎯 Format Training Insights")
                with st.expander("View Format Analysis Results", expanded=True):
                    st.markdown(st.session_state.format_patterns['format_insights'])
            
            # Individual PDF analysis
            if st.checkbox("Show Individual PDF Analysis"):
                for filename, pdf_data in st.session_state.pdf_format_analysis.items():
                    analysis = pdf_data.get('analysis', {})
                    
                    with st.expander(f"📄 {filename}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Pages:** {analysis.get('page_count', 0)}")
                            st.write(f"**Sections:** {len(analysis.get('sections', []))}")
                            st.write(f"**Tables:** {len(analysis.get('tables', []))}")
                            st.write(f"**Analyzed:** {pdf_data.get('analyzed_date', 'Unknown')[:10]}")
                        
                        with col2:
                            sections = analysis.get('sections', [])
                            if sections:
                                st.write("**Section Types Found:**")
                                section_types = list(set(s.get('type') for s in sections if s.get('type')))
                                for section_type in section_types:
                                    st.write(f"• {section_type.title()}")
                            
                            patterns = analysis.get('formatting_patterns', {})
                            if patterns:
                                st.write("**Format Patterns:**")
                                hierarchy = patterns.get('section_hierarchy', {})
                                if hierarchy.get('section_types'):
                                    st.write(f"• Section types: {len(hierarchy['section_types'])}")

elif st.session_state.current_step == 6:
    # PRD Library (keep existing PRD functionality)
    st.header("📄 PRD Library & AI Analysis")
    st.markdown("Upload and analyze Product Requirements Documents with AI-powered specification extraction")
    
    if not api_key:
        st.warning("⚠️ Please configure your API key in the sidebar to use PRD analysis features")
    
    tab1, tab2, tab3 = st.tabs(["📁 Upload PRD", "📋 PRD Library", "🔄 Use PRD"])
    
    with tab1:
        st.subheader("📁 Upload New PRD Document")
        
        uploaded_file = st.file_uploader(
            "Upload PRD Document",
            type=['pdf', 'docx', 'txt'],
            help="Upload PDF, DOCX, or TXT files containing product requirements"
        )
        
        if uploaded_file:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                prd_name = st.text_input("PRD Name", value=uploaded_file.name.split('.')[0])
                prd_description = st.text_area("Description (optional)", 
                    placeholder="Brief description of this PRD...")
                expected_type = st.selectbox("Expected Product Type", 
                    list(PRODUCT_TYPES.keys()),
                    format_func=lambda x: PRODUCT_TYPES[x]['name'])
                
            with col2:
                st.write("**File Info:**")
                st.write(f"Name: {uploaded_file.name}")
                st.write(f"Size: {uploaded_file.size:,} bytes")
                st.write(f"Type: {uploaded_file.type}")
            
            if st.button("🔍 Analyze PRD with AI", type="primary") and api_key:
                with st.spinner("Extracting text and analyzing with AI..."):
                    # Extract text based on file type
                    file_content = uploaded_file.read()
                    
                    if uploaded_file.type == "application/pdf":
                        extracted_text = extract_text_from_pdf(file_content)
                    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        extracted_text = extract_text_from_docx(file_content)
                    else:
                        extracted_text = file_content.decode('utf-8', errors='ignore')
                    
                    if "Error" not in extracted_text:
                        # Analyze with AI
                        analysis_result = analyze_prd_with_groq(extracted_text, api_key, model_choice)
                        
                        if "error" not in analysis_result:
                            prd_id = datetime.now().strftime("%Y%m%d%H%M%S")
                            
                            st.session_state.prd_documents[prd_id] = {
                                "id": prd_id,
                                "name": prd_name,
                                "filename": uploaded_file.name,
                                "description": prd_description,
                                "expected_type": expected_type,
                                "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "raw_content": extracted_text,
                                "ai_analysis": analysis_result,
                                "extracted_specs": analysis_result.get('specifications', {}),
                                "extracted_features": analysis_result.get('features', []),
                                "confidence_score": analysis_result.get('confidence_score', 0.0)
                            }
                            
                            st.success(f"✅ PRD analyzed successfully! Confidence: {analysis_result.get('confidence_score', 0)*100:.1f}%")
                            
                            # Show analysis results
                            with st.expander("📊 AI Analysis Results", expanded=True):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.subheader("🔧 Extracted Specifications")
                                    if analysis_result.get('specifications'):
                                        for key, value in analysis_result['specifications'].items():
                                            if value:
                                                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                                    else:
                                        st.info("No specifications extracted")
                                
                                with col2:
                                    st.subheader("⭐ Extracted Features")
                                    if analysis_result.get('features'):
                                        for feature in analysis_result['features'][:10]:
                                            st.write(f"• {feature}")
                                    else:
                                        st.info("No features extracted")
                            
                            st.rerun()
                        else:
                            st.error(f"❌ AI analysis failed: {analysis_result['error']}")
                    else:
                        st.error(f"❌ Text extraction failed: {extracted_text}")
            
            elif not api_key:
                st.info("Configure API key to enable AI analysis")
    
    with tab2:
        st.subheader("📋 PRD Document Library")
        
        if not st.session_state.prd_documents:
            st.info("No PRD documents uploaded yet. Upload some PRDs to get started.")
        else:
            # Search and filter
            col1, col2 = st.columns(2)
            with col1:
                search_term = st.text_input("Search PRDs", placeholder="Search by name...")
            with col2:
                filter_type = st.selectbox("Filter by type", 
                    ["All"] + list(PRODUCT_TYPES.keys()),
                    format_func=lambda x: "All Types" if x == "All" else PRODUCT_TYPES.get(x, {}).get('name', x))
            
            # Filter PRDs
            filtered_prds = {}
            for prd_id, prd_data in st.session_state.prd_documents.items():
                if search_term and search_term.lower() not in prd_data['name'].lower():
                    continue
                if filter_type != "All" and prd_data['expected_type'] != filter_type:
                    continue
                filtered_prds[prd_id] = prd_data
            
            st.write(f"Showing {len(filtered_prds)} of {len(st.session_state.prd_documents)} PRDs")
            
            # Display PRDs
            for prd_id, prd_data in filtered_prds.items():
                confidence = prd_data.get('confidence_score', 0)
                confidence_emoji = "🎯" if confidence >= 0.8 else "⭐" if confidence >= 0.6 else "📄"
                
                with st.expander(f"{confidence_emoji} {prd_data['name']} (Confidence: {confidence*100:.1f}%)"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**File:** {prd_data['filename']}")
                        st.write(f"**Product Type:** {PRODUCT_TYPES[prd_data['expected_type']]['name']}")
                        st.write(f"**Upload Date:** {prd_data['upload_date']}")
                        st.write(f"**Confidence:** {confidence*100:.1f}%")
                        
                        if prd_data.get('description'):
                            st.write(f"**Description:** {prd_data['description']}")
                        
                        # Show extracted specs summary
                        specs_count = len([v for v in prd_data.get('extracted_specs', {}).values() if v])
                        features_count = len(prd_data.get('extracted_features', []))
                        st.write(f"**Extracted:** {specs_count} specifications, {features_count} features")
                    
                    with col2:
                        if st.button("🚀 Use This PRD", key=f"use_prd_{prd_id}"):
                            st.session_state.selected_prd_id = prd_id
                            st.session_state.current_step = 2
                            st.success("PRD selected! Redirecting to specifications...")
                            time.sleep(1)
                            st.rerun()
                        
                        if st.button("🗑️ Delete", key=f"del_prd_{prd_id}"):
                            del st.session_state.prd_documents[prd_id]
                            st.rerun()
                    
                    # Show detailed analysis
                    if st.checkbox("Show Analysis Details", key=f"details_{prd_id}"):
                        analysis_tabs = st.tabs(["🔧 Specifications", "⭐ Features", "📝 Raw Content"])
                        
                        with analysis_tabs[0]:
                            specs = prd_data.get('extracted_specs', {})
                            if specs:
                                for key, value in specs.items():
                                    if value:
                                        st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                            else:
                                st.info("No specifications extracted")
                        
                        with analysis_tabs[1]:
                            features = prd_data.get('extracted_features', [])
                            if features:
                                for feature in features:
                                    st.write(f"• {feature}")
                            else:
                                st.info("No features extracted")
                        
                        with analysis_tabs[2]:
                            content_preview = prd_data.get('raw_content', '')[:1000]
                            st.text_area("Raw Content (first 1000 chars)", content_preview, height=200, disabled=True)
    
    with tab3:
        st.subheader("🔄 Use PRD in Datasheet Generation")
        
        if not st.session_state.prd_documents:
            st.info("No PRD documents available. Upload some PRDs first.")
        else:
            st.write("Select a PRD to automatically populate specification fields:")
            
            # PRD selection
            prd_options = {prd_id: f"{prd_data['name']} (Confidence: {prd_data.get('confidence_score', 0)*100:.1f}%)" 
                          for prd_id, prd_data in st.session_state.prd_documents.items()}
            
            selected_prd_id = st.selectbox("Choose PRD", 
                options=list(prd_options.keys()),
                format_func=lambda x: prd_options[x])
            
            if selected_prd_id:
                prd_data = st.session_state.prd_documents[selected_prd_id]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📋 PRD Summary")
                    st.write(f"**Name:** {prd_data['name']}")
                    st.write(f"**Type:** {PRODUCT_TYPES[prd_data['expected_type']]['name']}")
                    st.write(f"**Confidence:** {prd_data.get('confidence_score', 0)*100:.1f}%")
                    
                    specs_count = len([v for v in prd_data.get('extracted_specs', {}).values() if v])
                    features_count = len(prd_data.get('extracted_features', []))
                    st.write(f"**Extracted:** {specs_count} specs, {features_count} features")
                
                with col2:
                    st.subheader("🎯 Quick Preview")
                    specs = prd_data.get('extracted_specs', {})
                    for key, value in list(specs.items())[:4]:
                        if value:
                            st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                
                if st.button("🚀 Use This PRD for Generation", type="primary"):
                    # Set the PRD data in session state
                    st.session_state.selected_prd_id = selected_prd_id
                    st.session_state.new_specs = prd_data.get('extracted_specs', {})
                    st.session_state.new_features = prd_data.get('extracted_features', [])
                    
                    # Redirect to step 2 (specifications)
                    st.session_state.current_step = 2
                    st.success("✅ PRD data loaded! Redirecting to specifications step...")
                    time.sleep(1)
                    st.rerun()

# Footer
st.divider()
enhancement_status = []
if st.session_state.auto_training_completed:
    enhancement_status.append(f"🧠 Library-Trained ({len(st.session_state.templates)} templates)")
if st.session_state.format_patterns:
    enhancement_status.append(f"📄 Format-Enhanced ({len(st.session_state.pdf_format_analysis)} PDFs)")
if st.session_state.prd_documents:
    enhancement_status.append(f"📝 PRD-Ready ({len(st.session_state.prd_documents)} docs)")

status_text = " | ".join(enhancement_status) if enhancement_status else "Ready for enhancement"

st.markdown(
    f"""
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
        Ruckus Master AI Datasheet Generator v6.0 | {status_text}<br>
        📊 {len(st.session_state.generated_datasheets)} Datasheets Generated | 
        🧠 AI Auto-Training from Library & Format Analysis
    </div>
    """,
    unsafe_allow_html=True
)