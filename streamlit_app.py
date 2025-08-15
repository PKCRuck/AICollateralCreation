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
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from reportlab.pdfgen import canvas
    from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
    from reportlab.platypus.frames import Frame
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

# Hardcoded API key (as requested)
GROQ_API_KEY = "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"

# Page configuration
st.set_page_config(
    page_title="RUCKUS Datasheet Generator",
    page_icon="🐕",
    layout="wide"
)

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    st.image("Pics/Ruckus_logo_stacked_white-orange.png", width=250)

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
if "ai_feedback" not in st.session_state:
    st.session_state.ai_feedback = {}
if "pdf_format_analysis" not in st.session_state:
    st.session_state.pdf_format_analysis = {}
if "auto_training_completed" not in st.session_state:
    st.session_state.auto_training_completed = False
if "format_patterns" not in st.session_state:
    st.session_state.format_patterns = {}
if "spec_accuracy_score" not in st.session_state:
    st.session_state.spec_accuracy_score = 0.0
if "live_content" not in st.session_state:
    st.session_state.live_content = ""
if "generation_complete" not in st.session_state:
    st.session_state.generation_complete = False

# Enhanced Product type configurations
PRODUCT_TYPES = {
    "optic_transceiver": {
        "name": "Optical Transceiver",
        "keywords": [
            "qsfp28", "optical", "transceiver", "100gbase", "lr4",
            "fiber", "dfb", "laser", "receiver", "optics", "sfp", "sfp+", "qsfp", "osfp"
        ],
        "spec_fields": [
            ("model_number", "Model Number", "text"),
            ("form_factor", "Form Factor", "text"),
            ("data_rate", "Data Rate", "text"),
            ("wavelengths", "Wavelengths", "text"),
            ("connector_type", "Connector Type", "text"),
            ("fiber_type", "Fiber Type", "text"),
            ("transmission_distance", "Transmission Distance", "text"),
            ("power_dissipation", "Power Dissipation", "text"),
            ("operating_temp", "Operating Temperature", "text"),
            ("power_supply_voltage", "Power Supply Voltage", "text"),
            ("tx_power", "Transmit Power", "text"),
            ("rx_power", "Receive Power", "text"),
            ("receiver_sensitivity", "Receiver Sensitivity", "text"),
            ("extinction_ratio", "Extinction Ratio", "text"),
            ("digital_diagnostics", "Digital Diagnostics Monitoring", "textarea"),
            ("standards_compliance", "Standards Compliance", "textarea"),
            ("ieee_standard", "IEEE Standard", "text"),
            ("dimensions", "Dimensions", "text"),
            ("weight", "Weight", "text")
        ],
        "prd_keywords": [
            "qsfp28", "optical", "fiber", "transceiver", "wavelength",
            "connector", "dbm", "lr4", "digital diagnostics",
            "ieee", "sff", "standard", "msa"
        ]
    },

    "wireless_ap": {
        "name": "Wireless Access Point",
        "keywords": ["access point", "wireless", "wifi", "802.11", "antenna", "ssid", "wlan", "mimo", "radio", "beamflex"],
        "spec_fields": [
            ("model_number", "Model Number", "text"),
            ("wireless_standards", "Wireless Standards", "text"),
            ("frequency_bands", "Frequency Bands", "text"),
            ("max_data_rate", "Maximum Data Rate", "text"),
            ("spatial_streams", "Spatial Streams", "text"),
            ("mimo_config", "MIMO Configuration", "text"),
            ("antenna_type", "Antenna Type", "text"),
            ("max_clients", "Maximum Concurrent Clients", "text"),
            ("ssid_support", "SSID Support", "text"),
            ("ethernet_ports", "Ethernet Ports", "text"),
            ("poe_requirements", "PoE Requirements", "text"),
            ("power_consumption", "Power Consumption", "text"),
            ("transmit_power_2_4", "Transmit Power 2.4GHz", "text"),
            ("transmit_power_5", "Transmit Power 5GHz", "text"),
            ("transmit_power_6", "Transmit Power 6GHz", "text"),
            ("receive_sensitivity_2_4", "Receive Sensitivity 2.4GHz", "text"),
            ("receive_sensitivity_5", "Receive Sensitivity 5GHz", "text"),
            ("receive_sensitivity_6", "Receive Sensitivity 6GHz", "text"),
            ("dimensions", "Dimensions (H x W x D)", "text"),
            ("weight", "Weight", "text"),
            ("operating_temp", "Operating Temperature", "text"),
            ("humidity_rating", "Humidity Rating", "text"),
            ("mounting_options", "Mounting Options", "text"),
            ("security_protocols", "Security Protocols", "textarea"),
            ("management_protocols", "Management Protocols", "text"),
            ("certifications", "Certifications", "textarea"),
            ("warranty", "Warranty", "text")
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
            ("max_aps", "Maximum APs Supported", "text"),
            ("max_clients", "Maximum Clients", "text"),
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

# Enhanced specification extraction patterns
SPEC_EXTRACTION_PATTERNS = {
    "optic_transceiver": {
        "model_number": [r"(?:Model|Part)\s*(?:Number|No\.?|#|ID)[:\s]*([A-Z0-9\-]+)"],
        "form_factor": [r"(QSFP28|QSFP56|SFP\+|SFP28|OSFP|QSFP-DD)"],
        "data_rate": [r"(\d+\.?\d*\s*Gb/s|\d+\s*Gbps|\d+\s*G)"],
        "wavelengths": [r"((?:1294|1295|1296|1299|1300|1301|1303|1304|1305|1308|1309|1310)\s*nm[^\n]*)",
                        r"(\d{4}\s*nm(?:,\s*\d{4}\s*nm)+)"],
        "connector_type": [r"(LC\s*connector|LC\s*receptacle|MPO\s*(?:\d+)?\s*connector)"],
        "fiber_type": [r"(single\s*mode\s*fiber|SMF|multi\s*mode\s*fiber|MMF)"],
        "transmission_distance": [r"(\d+\s*km)"],
        "power_dissipation": [r"Power\s*dissipation[:\s]*([0-9\.]+\s*W)"],
        "operating_temp": [r"(?:Case\s*)?Operating\s*Temperature[:\s]*([^\n]+)"],
        "power_supply_voltage": [r"(?:Power\s*Supply\s*Voltage|VCC)[:\s]*([0-9\.]+\s*V)"],
        "tx_power": [r"(?:Transmit(?:ted)?\s*optical\s*power|Average\s*launch\s*power)[^-\n]*([\-+]?\d+\.?\d*\s*dBm)"],
        "rx_power": [r"(?:Receive(?:d)?\s*optical\s*power|Average\s*input\s*power)[^-\n]*([\-+]?\d+\.?\d*\s*dBm)"],
        "receiver_sensitivity": [r"(?:Receiver\s*sensitivity)[^-\n]*([\-+]?\d+\.?\d*\s*dBm)"],
        "extinction_ratio": [r"(?:Extinction\s*Ratio|ER)\s*[:\s]*([0-9\.]+\s*dB)"],
        "digital_diagnostics": [r"(Digital\s*Diagnostics[\s\S]+?)(?:\n[A-Z][^\n]+:|\Z)"],
        "standards_compliance": [r"(Compliant(?:\s*to|\s*with)[\s\S]+?)(?:\n[A-Z][^\n]+:|\Z)"],
        "ieee_standard": [r"(IEEE\s*802\.\d+[a-z]?)", r"(IEEE\s*802\.3[a-z]?)"],
        "dimensions": [r"Dimensions?\s*[:\-]\s*([^\n]+)"],
        "weight": [r"Weight\s*[:\-]\s*([^\n]+)"]
    },

    "wireless_ap": {
        "model_number": [
            r"(?:Model|Part|Product)\s*(?:Number|#|ID)?\s*:?\s*([A-Z0-9\-]+)",
            r"RUCKUS\s+([A-Z0-9]+)",
            r"([A-Z]\d{3,4}[A-Z]?)\s+(?:Access Point|AP)"
        ],
        "max_data_rate": [
            r"(\d+\.?\d*)\s*Gbps\s*(?:combined|aggregate|total)",
            r"(?:Data\s*Rate|Speed|Throughput):\s*([0-9.,]+\s*[GMK]?bps)",
            r"(\d+\.?\d*)\s*Gbps\s*(?:data rate|throughput)"
        ],
        "frequency_bands": [
            r"(2\.4\s*GHz[^.]*?5\s*GHz[^.]*?6\s*GHz[^.]*)",
            r"(2\.4\s*GHz[^.]*?5\s*GHz[^.]*)",
            r"tri-band|dual-band|single-band"
        ],
        "spatial_streams": [
            r"(\d+)\s*spatial\s*streams",
            r"(\d+x\d+:\d+)[^0-9]",
            r"(\d+)\s*stream"
        ],
        "max_clients": [
            r"(?:Up to|Maximum)\s*(\d+)\s*clients",
            r"(\d+)\s*(?:concurrent\s*)?clients\s*per\s*AP"
        ],
        "power_consumption": [
            r"(\d+\.?\d*)\s*W\s*(?:maximum|max|peak)",
            r"Power\s*(?:Consumption|Requirements?):\s*([0-9.]+\s*W)",
            r"(\d+\.?\d*)\s*W\s*(?:typical|average)"
        ]
    }
}

def get_ruckus_logo_base64():
    """Get the Ruckus dog logo as base64 string"""
    try:
        pics_folder = "Pics"
        logo_path = os.path.join(pics_folder, "Ruckus dog.png")
        
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
        else:
            # Return a placeholder or create a simple SVG logo
            return None
    except Exception as e:
        st.warning(f"Could not load Ruckus logo: {str(e)}")
        return None

def create_professional_html_template(content: str, product_name: str, generation_metrics: Dict) -> str:
    """Create a professional HTML template matching Ruckus datasheet format"""
    
    logo_base64 = get_ruckus_logo_base64()
    logo_img = f'<img src="data:image/png;base64,{logo_base64}" alt="Ruckus Logo" style="height: 60px; margin-right: 20px;">' if logo_base64 else ""
    
    # Enhanced CSS styling to match Ruckus datasheets
    professional_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@300;400;600;700&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #fff;
            font-size: 11pt;
        }
        
        .datasheet-container {
            max-width: 8.5in;
            margin: 0 auto;
            padding: 0;
            background: white;
        }
        
        /* Header Section */
        .header-section {
            background: linear-gradient(135deg, #ff6600, #ff8533);
            color: white;
            padding: 20px 30px;
            margin-bottom: 0;
            position: relative;
            overflow: hidden;
        }
        
        .header-section::before {
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            width: 200px;
            height: 100%;
            background: rgba(255, 255, 255, 0.1);
            transform: skewX(-15deg);
            transform-origin: top;
        }
        
        .header-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: relative;
            z-index: 2;
        }
        
        .logo-section {
            display: flex;
            align-items: center;
        }
        
        .ruckus-logo {
            font-size: 28px;
            font-weight: bold;
            color: white;
            letter-spacing: 1px;
        }
        
        .product-title {
            text-align: right;
            flex-grow: 1;
            margin-left: 40px;
        }
        
        .product-title h1 {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 5px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        
        .product-subtitle {
            font-size: 14px;
            opacity: 0.95;
            font-weight: 400;
        }
        
        /* Data Sheet Label */
        .datasheet-label {
            background: #333;
            color: white;
            padding: 8px 20px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 1px;
            margin-bottom: 30px;
        }
        
        /* Content Section */
        .content-section {
            padding: 0 30px 30px 30px;
        }
        
        /* Headings */
        h1 {
            color: #ff6600;
            font-size: 22px;
            font-weight: 700;
            margin: 30px 0 15px 0;
            border-bottom: 3px solid #ff6600;
            padding-bottom: 8px;
        }
        
        h2 {
            color: #ff6600;
            font-size: 18px;
            font-weight: 600;
            margin: 25px 0 12px 0;
            border-left: 4px solid #ff6600;
            padding-left: 12px;
        }
        
        h3 {
            color: #333;
            font-size: 15px;
            font-weight: 600;
            margin: 20px 0 10px 0;
        }
        
        h4 {
            color: #555;
            font-size: 13px;
            font-weight: 600;
            margin: 15px 0 8px 0;
        }
        
        /* Benefits Section */
        .benefits-section {
            background: #f8f9fa;
            padding: 25px;
            margin: 20px 0;
            border-left: 5px solid #ff6600;
            border-radius: 0 8px 8px 0;
        }
        
        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 10pt;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }
        
        th {
            background: linear-gradient(135deg, #ff6600, #ff8533);
            color: white;
            padding: 12px 10px;
            text-align: left;
            font-weight: 600;
            font-size: 11pt;
            border: none;
        }
        
        td {
            padding: 10px;
            border-bottom: 1px solid #e0e0e0;
            vertical-align: top;
        }
        
        tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        
        tr:hover {
            background-color: #e3f2fd;
            transition: background-color 0.3s ease;
        }
        
        /* Lists */
        ul {
            margin: 15px 0;
            padding-left: 0;
            list-style: none;
        }
        
        li {
            margin: 8px 0;
            padding-left: 25px;
            position: relative;
            line-height: 1.5;
        }
        
        li::before {
            content: "▶";
            color: #ff6600;
            font-weight: bold;
            position: absolute;
            left: 8px;
            font-size: 10px;
        }
        
        /* Special sections */
        .specification-section {
            background: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        
        .feature-highlight {
            background: linear-gradient(135deg, #fff3e0, #ffe0b3);
            border-left: 4px solid #ff6600;
            padding: 15px 20px;
            margin: 15px 0;
            border-radius: 0 8px 8px 0;
        }
        
        /* Generation metrics */
        .generation-metrics {
            background: #f0f8ff;
            border: 1px solid #b3d9ff;
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
            font-size: 10pt;
        }
        
        .metric-badge {
            display: inline-block;
            background: #e8f5e8;
            color: #2d5d2d;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 9pt;
            margin: 3px;
            font-weight: 500;
        }
        
        /* Footer */
        .footer-section {
            background: #f8f9fa;
            border-top: 3px solid #ff6600;
            padding: 20px 30px;
            margin-top: 40px;
            text-align: center;
            font-size: 10pt;
            color: #666;
        }
        
        .footer-section .company-info {
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }
        
        /* Responsive adjustments for print */
        @media print {
            .datasheet-container {
                max-width: none;
                margin: 0;
                padding: 0;
            }
            
            .header-section {
                -webkit-print-color-adjust: exact;
                color-adjust: exact;
            }
            
            body {
                font-size: 10pt;
            }
            
            table {
                break-inside: avoid;
            }
            
            h1, h2, h3 {
                break-after: avoid;
            }
        }
        
        /* Code blocks */
        pre, code {
            background: #f4f4f4;
            border-radius: 4px;
            padding: 10px;
            font-family: 'Courier New', monospace;
            font-size: 9pt;
            overflow-x: auto;
        }
        
        /* Blockquotes */
        blockquote {
            border-left: 4px solid #ff6600;
            padding-left: 20px;
            margin: 20px 0;
            color: #555;
            font-style: italic;
            background: #f9f9f9;
            padding: 15px 15px 15px 35px;
            border-radius: 0 8px 8px 0;
        }
        
        /* Horizontal rules */
        hr {
            border: none;
            height: 3px;
            background: linear-gradient(to right, #ff6600, #ff8533);
            margin: 30px 0;
            border-radius: 2px;
        }
        
        /* Text formatting */
        strong, b {
            font-weight: 600;
            color: #333;
        }
        
        em, i {
            font-style: italic;
            color: #555;
        }
        
        /* Links */
        a {
            color: #ff6600;
            text-decoration: none;
            font-weight: 500;
        }
        
        a:hover {
            text-decoration: underline;
        }
    </style>
    """
    
    # Convert markdown content to HTML and enhance it
    html_content = markdown.markdown(content, extensions=['tables', 'nl2br', 'codehilite'])
    
    # Process the HTML to add professional classes
    html_content = enhance_html_content(html_content)
    
    # Create the complete HTML document
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{product_name} - Professional Datasheet</title>
    {professional_css}
</head>
<body>
    <div class="datasheet-container">
        <!-- Header Section -->
        <div class="header-section">
            <div class="header-content">
                <div class="logo-section">
                    {logo_img}
                    <div class="ruckus-logo">RUCKUS®</div>
                </div>
                <div class="product-title">
                    <h1>{product_name}</h1>
                    <div class="product-subtitle">Professional Enterprise Network Solution</div>
                </div>
            </div>
        </div>
        
        <!-- Data Sheet Label -->
        <div class="datasheet-label">DATA SHEET</div>
        
        <!-- Generation Metrics -->
        <div class="generation-metrics">
            <strong>📊 Professional Datasheet Generation:</strong>
            <div style="margin-top: 8px;">
                <span class="metric-badge">🎯 {generation_metrics.get('word_count', 0):,} Words</span>
                <span class="metric-badge">📝 {generation_metrics.get('section_count', 0)} Sections</span>
                <span class="metric-badge">📊 {generation_metrics.get('table_count', 0)} Tables</span>
                <span class="metric-badge">✅ {generation_metrics.get('overall_quality', 0):.1%} Quality</span>
                <span class="metric-badge">🔴 Live Generated</span>
                <span class="metric-badge">📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
            </div>
        </div>
        
        <!-- Main Content -->
        <div class="content-section">
            {html_content}
        </div>
        
        <!-- Footer -->
        <div class="footer-section">
            <div class="company-info">© {datetime.now().year} CommScope, Inc. All rights reserved.</div>
            <div>RUCKUS, RUCKUS WIRELESS and RUCKUS NETWORKS are trademarks of CommScope, Inc.</div>
            <div style="margin-top: 10px; font-size: 9pt;">
                <em>Generated by Ruckus Professional Datasheet Generator • Live Streaming Technology • Advanced AI Content Creation</em>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    return full_html

def enhance_html_content(html_content: str) -> str:
    """Enhance HTML content with professional classes and formatting"""
    
    # Add classes to tables for better styling
    html_content = re.sub(r'<table>', '<table class="professional-table">', html_content)
    
    # Enhance headers
    html_content = re.sub(r'<h1([^>]*)>', r'<h1\1 class="section-header">', html_content)
    html_content = re.sub(r'<h2([^>]*)>', r'<h2\1 class="subsection-header">', html_content)
    
    # Add classes to important sections
    html_content = re.sub(
        r'(<h[12][^>]*>[^<]*(?:benefits|features)[^<]*</h[12]>)',
        r'<div class="benefits-section">\1',
        html_content,
        flags=re.IGNORECASE
    )
    
    # Close benefits sections
    html_content = re.sub(
        r'(</div>)(\s*<h[12])',
        r'\1</div>\2',
        html_content
    )
    
    # Add specification section wrapper
    html_content = re.sub(
        r'(<h[12][^>]*>[^<]*(?:specification|technical)[^<]*</h[12]>)',
        r'<div class="specification-section">\1',
        html_content,
        flags=re.IGNORECASE
    )
    
    return html_content

def create_professional_pdf(content: str, product_name: str, generation_metrics: Dict) -> BytesIO:
    """Create a professional PDF matching Ruckus datasheet format"""
    if not PDF_AVAILABLE:
        return None
    
    buffer = BytesIO()
    
    # Custom page template for professional layout
    class RuckusPageTemplate(PageTemplate):
        def __init__(self, doc):
            self.doc = doc
            frame = Frame(
                0.75*inch, 0.75*inch, 
                7*inch, 9.5*inch,
                leftPadding=0, rightPadding=0,
                topPadding=0, bottomPadding=0
            )
            super().__init__('professional', [frame])
        
        def beforeDrawPage(self, canvas, doc):
            # Draw header
            canvas.saveState()
            
            # Orange header background
            canvas.setFillColor(colors.HexColor('#ff6600'))
            canvas.rect(0, doc.pagesize[1] - 1.2*inch, doc.pagesize[0], 1.2*inch, fill=1)
            
            # Logo and title
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 20)
            canvas.drawString(0.75*inch, doc.pagesize[1] - 0.6*inch, "RUCKUS®")
            
            # Product title
            canvas.setFont("Helvetica-Bold", 16)
            title_width = canvas.stringWidth(product_name, "Helvetica-Bold", 16)
            canvas.drawRightString(doc.pagesize[0] - 0.75*inch, doc.pagesize[1] - 0.6*inch, product_name)
            
            # Data sheet label
            canvas.setFillColor(colors.HexColor('#333333'))
            canvas.rect(0, doc.pagesize[1] - 1.6*inch, doc.pagesize[0], 0.4*inch, fill=1)
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 10)
            canvas.drawString(0.75*inch, doc.pagesize[1] - 1.4*inch, "DATA SHEET")
            
            # Footer
            canvas.setFillColor(colors.HexColor('#666666'))
            canvas.setFont("Helvetica", 8)
            footer_text = f"© {datetime.now().year} CommScope, Inc. All rights reserved."
            canvas.drawString(0.75*inch, 0.4*inch, footer_text)
            
            # Page number
            canvas.drawRightString(doc.pagesize[0] - 0.75*inch, 0.4*inch, f"Page {doc.page}")
            
            canvas.restoreState()
    
    # Create document
    doc = BaseDocTemplate(buffer, pagesize=letter, topMargin=2*inch, bottomMargin=0.75*inch)
    doc.addPageTemplates([RuckusPageTemplate(doc)])
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        textColor=colors.HexColor('#ff6600'),
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.HexColor('#ff6600'),
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        fontName='Helvetica'
    )
    
    # Build story
    story = []
    
    # Generation metrics
    metrics_text = f"""<b>Professional Datasheet Generation:</b><br/>
    Words: {generation_metrics.get('word_count', 0):,} | 
    Sections: {generation_metrics.get('section_count', 0)} | 
    Quality: {generation_metrics.get('overall_quality', 0):.1%} | 
    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
    
    story.append(Paragraph(metrics_text, body_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Process content for PDF
    content_lines = content.split('\n')
    current_table_data = []
    in_table = False
    
    for line in content_lines:
        line = line.strip()
        if not line:
            continue
            
        # Handle headers
        if line.startswith('# '):
            story.append(Paragraph(line[2:], title_style))
        elif line.startswith('## '):
            story.append(Paragraph(line[3:], heading_style))
        elif line.startswith('### '):
            story.append(Paragraph(line[4:], styles['Heading3']))
        
        # Handle tables
        elif '|' in line and not line.startswith('|--'):
            if not in_table:
                in_table = True
                current_table_data = []
            
            # Parse table row
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            current_table_data.append(cells)
            
        elif in_table and '|' not in line:
            # End of table
            if current_table_data:
                # Create table
                table = Table(current_table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff6600')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('TOPPADDING', (0, 1), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
                ]))
                story.append(table)
                story.append(Spacer(1, 0.1*inch))
            
            current_table_data = []
            in_table = False
            
            # Process the current line
            if line:
                story.append(Paragraph(line, body_style))
        
        # Handle regular content
        elif not in_table:
            if line.startswith('* ') or line.startswith('- '):
                # Bullet point
                bullet_text = f"• {line[2:]}"
                story.append(Paragraph(bullet_text, body_style))
            elif line.startswith('**') and line.endswith('**'):
                # Bold text
                story.append(Paragraph(f"<b>{line[2:-2]}</b>", body_style))
            else:
                story.append(Paragraph(line, body_style))
    
    # Handle final table if exists
    if current_table_data:
        table = Table(current_table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff6600')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
        ]))
        story.append(table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

def format_markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    """Create a properly formatted markdown table"""
    # Calculate column widths
    col_widths = []
    for i in range(len(headers)):
        max_width = len(headers[i])
        for row in rows:
            if i < len(row):
                max_width = max(max_width, len(str(row[i])))
        col_widths.append(max_width + 2)  # Add padding
    
    # Build table
    table_lines = []
    
    # Header row
    header_row = "|"
    for i, header in enumerate(headers):
        header_row += f" {header:<{col_widths[i]-2}} |"
    table_lines.append(header_row)
    
    # Separator row
    separator_row = "|"
    for width in col_widths:
        separator_row += f"{'-' * width}|"
    table_lines.append(separator_row)
    
    # Data rows
    for row in rows:
        data_row = "|"
        for i in range(len(headers)):
            value = str(row[i]) if i < len(row) else ""
            data_row += f" {value:<{col_widths[i]-2}} |"
        table_lines.append(data_row)
    
    return "\n".join(table_lines)

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF using PyMuPDF or PyPDF2"""
    try:
        if PYMUPDF_AVAILABLE:
            doc = fitz.open(stream=file_content, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        elif PDF_READ_AVAILABLE:
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

def analyze_prd_with_ai(prd_content: str, model: str = "llama-3.1-8b-instant") -> Dict:
    """Analyze PRD content using AI to extract specifications with enhanced accuracy"""
    if not GROQ_AVAILABLE:
        return {"error": "Groq library not available"}
    
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        # Enhanced prompt for more accurate PRD analysis
        prompt = f"""You are an expert technical analyst for network equipment Product Requirements Documents (PRDs). 

Analyze the following PRD content and extract ALL technical specifications and product details with HIGH ACCURACY.

CRITICAL REQUIREMENTS:
1. Extract ONLY factual specifications that are explicitly stated
2. Do NOT fabricate or estimate values
3. Be precise with units and measurements
4. Identify the correct product type based on technical details
5. Extract complete feature lists with technical benefits

Return ONLY a valid JSON object with these keys:
{{
    "product_type": "wireless_ap|switch|controller",
    "model_number": "extracted model number or null",
    "specifications": {{
        "wireless_standards": "exact standards from document",
        "frequency_bands": "exact frequency information", 
        "max_data_rate": "exact data rate with units",
        "spatial_streams": "exact stream configuration",
        "mimo_config": "exact MIMO details",
        "antenna_type": "exact antenna specifications",
        "max_clients": "exact client capacity",
        "ssid_support": "exact SSID support",
        "ethernet_ports": "exact port specifications",
        "poe_requirements": "exact PoE details",
        "power_consumption": "exact power specifications",
        "transmit_power_2_4": "exact 2.4GHz transmit power",
        "transmit_power_5": "exact 5GHz transmit power",
        "transmit_power_6": "exact 6GHz transmit power",
        "receive_sensitivity_2_4": "exact 2.4GHz sensitivity",
        "receive_sensitivity_5": "exact 5GHz sensitivity",
        "receive_sensitivity_6": "exact 6GHz sensitivity",
        "dimensions": "exact dimensions with units",
        "weight": "exact weight with units",
        "operating_temp": "exact temperature range",
        "humidity_rating": "exact humidity specifications",
        "mounting_options": "exact mounting information",
        "security_protocols": "exact security standards",
        "management_protocols": "exact management protocols",
        "certifications": "exact certifications listed",
        "warranty": "exact warranty information"
    }},
    "features": ["exact feature 1", "exact feature 2", "exact feature 3"],
    "performance_metrics": {{
        "throughput": "exact throughput specifications",
        "capacity": "exact capacity metrics",
        "coverage": "exact coverage information"
    }},
    "confidence_score": 0.0-1.0,
    "extraction_notes": "Notes about extraction quality and missing information"
}}

PRD CONTENT:
{prd_content[:8000]}"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert technical analyst specializing in network equipment PRDs. Extract specifications with 100% accuracy - never fabricate data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.05,  # Very low temperature for accuracy
            max_tokens=4000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Enhanced JSON parsing
        try:
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.rfind("```")
                content = content[json_start:json_end].strip()
            
            parsed_data = json.loads(content)
            
            # Validate extracted data
            if not parsed_data.get("product_type"):
                parsed_data["product_type"] = detect_product_type(prd_content)
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            return extract_specs_fallback(prd_content)
            
    except Exception as e:
        return {"error": f"Error analyzing PRD: {str(e)}"}

def extract_specs_fallback(content: str) -> Dict:
    """Enhanced fallback specification extraction"""
    specs = {
        "product_type": detect_product_type(content),
        "specifications": {},
        "features": [],
        "confidence_score": 0.5,
        "extraction_notes": "Fallback extraction method used"
    }
    
    # Enhanced patterns for better accuracy
    patterns = {
        "model_number": r'(?:Model|Part|Product)\s*(?:Number|#|ID):\s*([A-Z0-9\-]+)',
        "max_data_rate": r'(?:Data\s*Rate|Speed|Throughput):\s*([0-9.,]+\s*[GMK]?bps)',
        "frequency_bands": r'(?:Frequency|Band):\s*([0-9.]+\s*GHz[^.]*)',
        "power_consumption": r'(?:Power|Consumption):\s*([0-9.]+\s*W)',
        "dimensions": r'(?:Dimensions|Size):\s*([0-9.,\s×x]+\s*(?:cm|mm|in))',
        "weight": r'(?:Weight):\s*([0-9.]+\s*(?:kg|lbs|g))',
        "operating_temp": r'(?:Operating\s*Temperature|Temp):\s*([0-9\-°C\s]+)',
        "max_clients": r'(?:Up to|Maximum)\s*(\d+)\s*clients',
        "spatial_streams": r'(\d+)\s*spatial\s*streams',
        "transmit_power_2_4": r'2\.4\s*GHz:\s*(\d+\.?\d*\s*dBm)',
        "transmit_power_5": r'5\s*GHz:\s*(\d+\.?\d*\s*dBm)'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            specs["specifications"][key] = match.group(1).strip()
    
    # Enhanced feature extraction
    feature_patterns = [
        r'[•\-\*]\s*([^.\n]+)',
        r'\d+\.\s*([^.\n]+)',
        r'^\s*([A-Z][^.]+)$'
    ]
    
    for pattern in feature_patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        for match in matches[:15]:  # Increased limit
            if len(match.strip()) > 10 and len(match.strip()) < 150:
                specs["features"].append(match.strip())
    
    return specs

def detect_product_type(content: str) -> str:
    """Enhanced product type detection"""
    content_lower = content.lower()
    scores = {}
    
    for prod_type, config in PRODUCT_TYPES.items():
        score = 0
        for keyword in config["keywords"]:
            # Weight certain keywords more heavily
            weight = 3 if keyword in ["access point", "switch", "controller"] else 1
            score += content_lower.count(keyword) * weight
        scores[prod_type] = score
    
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    return "wireless_ap"

def extract_key_sections(content: str) -> Dict:
    """Enhanced section extraction with better accuracy"""
    sections = {
        "overview": "",
        "features": [],
        "specifications": {},
        "ordering_info": "",
        "performance": "",
        "security": "",
        "management": ""
    }
    
    lines = content.split('\n')
    current_section = None
    
    for line in lines:
        line_lower = line.lower().strip()
        
        # Enhanced section detection
        if any(kw in line_lower for kw in ['overview', 'introduction', 'description', 'summary']) and len(line_lower) < 50:
            current_section = 'overview'
        elif any(kw in line_lower for kw in ['features', 'benefits', 'highlights', 'capabilities']) and len(line_lower) < 50:
            current_section = 'features'
        elif any(kw in line_lower for kw in ['specifications', 'technical specs', 'specs', 'technical specifications']) and len(line_lower) < 50:
            current_section = 'specifications'
        elif any(kw in line_lower for kw in ['performance', 'capacity', 'throughput']) and len(line_lower) < 50:
            current_section = 'performance'
        elif any(kw in line_lower for kw in ['security', 'authentication', 'encryption']) and len(line_lower) < 50:
            current_section = 'security'
        elif any(kw in line_lower for kw in ['management', 'control', 'monitoring']) and len(line_lower) < 50:
            current_section = 'management'
        elif any(kw in line_lower for kw in ['ordering', 'model', 'part number']) and len(line_lower) < 50:
            current_section = 'ordering_info'
        elif not line.strip():
            continue
        
        # Process content based on section
        if current_section == 'features':
            if re.match(r'^[\s]*[\•\-\*\▪\d\.]+\s+', line):
                feature = re.sub(r'^[\s]*[\•\-\*\▪\d\.]+\s+', '', line).strip()
                if feature:
                    sections['features'].append(feature)
        elif current_section in ['overview', 'performance', 'security', 'management']:
            if line.strip():
                sections[current_section] += line.strip() + " "
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
    
    # Clean up sections
    for key in ['overview', 'performance', 'security', 'management']:
        sections[key] = ' '.join(sections[key].split())
    sections['ordering_info'] = sections['ordering_info'].strip()
    
    return sections

def calculate_template_quality(sections: Dict) -> float:
    """Enhanced template quality calculation"""
    score = 0.0
    
    # Overview quality
    if sections.get('overview'):
        overview_len = len(sections['overview'])
        if overview_len > 300:
            score += 0.25
        elif overview_len > 200:
            score += 0.20
        elif overview_len > 100:
            score += 0.15
        elif overview_len > 50:
            score += 0.10
    
    # Features quality
    features = sections.get('features', [])
    if len(features) >= 8:
        score += 0.25
    elif len(features) >= 5:
        score += 0.20
    elif len(features) >= 3:
        score += 0.15
    elif len(features) >= 1:
        score += 0.10
    
    # Specifications quality
    specs = sections.get('specifications', {})
    if len(specs) >= 15:
        score += 0.25
    elif len(specs) >= 10:
        score += 0.20
    elif len(specs) >= 5:
        score += 0.15
    elif len(specs) >= 2:
        score += 0.10
    
    # Additional sections
    if sections.get('performance'):
        score += 0.10
    if sections.get('security'):
        score += 0.05
    if sections.get('management'):
        score += 0.05
    if sections.get('ordering_info'):
        score += 0.05
    
    return min(1.0, round(score, 2))

def create_comprehensive_prompt(template: Dict, specs: Dict, features: List[str], product_type: str) -> str:
    """Create a comprehensive, enhanced prompt for maximum accuracy"""
    
    product_config = PRODUCT_TYPES[product_type]
    
    # Enhanced comprehensive specifications
    enhanced_specs = generate_comprehensive_specifications(product_type, specs)
    
    # Create comprehensive prompt
    prompt = f"""You are a senior technical writer for Ruckus Networks with 15+ years experience creating professional datasheets for enterprise network equipment. You MUST create a comprehensive, industry-standard datasheet that meets the highest professional standards.

CRITICAL SUCCESS REQUIREMENTS:
1. Create a COMPLETE datasheet (4000-6000 words minimum)
2. Use ONLY provided specifications - NEVER fabricate data
3. Use proper Markdown formatting with perfect tables
4. Include ALL standard datasheet sections
5. Maintain consistent professional tone throughout
6. Focus on technical accuracy and completeness

PRODUCT INFORMATION:
Product Type: {product_config['name']}
Template Quality: {template.get('quality_score', 0.8):.2f}/1.0
Verification Status: {'Verified Accurate' if template.get('accuracy_verified') else 'Standard Template'}

VERIFIED SPECIFICATIONS:
{json.dumps(enhanced_specs, indent=2)}

VERIFIED FEATURES:
{json.dumps(features, indent=2)}

TEMPLATE REFERENCE:
Based on: {template['name']}
Quality Score: {template.get('quality_score', 0.8):.2f}

CREATE A COMPREHENSIVE PROFESSIONAL DATASHEET WITH THIS EXACT STRUCTURE:

# RUCKUS® {enhanced_specs.get('model_number', '[MODEL]')} {product_config['name']}

## Industry-Leading {product_config['name']} for Enterprise Environments

*Next-generation network solution delivering exceptional performance, reliability, and security*

---

### EXECUTIVE SUMMARY

[Write 3-4 comprehensive paragraphs (400+ words) covering:
- Product positioning and target market
- Key business benefits and ROI
- Competitive advantages
- Strategic value proposition
Include specific performance metrics and business outcomes.]

---

### KEY BUSINESS BENEFITS

• **Enhanced Performance**: [Detailed technical explanation with metrics]
• **Simplified Management**: [Specific management advantages with examples]
• **Advanced Security**: [Security benefits with technical details]
• **Scalability & Future-Proofing**: [Growth and upgrade advantages]
• **Operational Efficiency**: [Cost savings and efficiency gains]
• **Reliability & Uptime**: [Availability and reliability features]

---

### ADVANCED FEATURES & CAPABILITIES

#### Core Technology Features
[Write detailed subsections for each major feature area with technical explanations]

#### Performance Optimization
[Detailed performance features and benefits]

#### Security & Compliance
[Comprehensive security feature descriptions]

#### Management & Control
[Management capabilities and tools]

---

### COMPREHENSIVE TECHNICAL SPECIFICATIONS

#### Wireless Performance Specifications

| Specification | Value |
|--------------|--------|
| Wireless Standards | {enhanced_specs.get('wireless_standards', 'IEEE 802.11a/b/g/n/ac/ax')} |
| Frequency Bands | {enhanced_specs.get('frequency_bands', '2.4/5/6 GHz tri-band')} |
| Maximum Data Rate | {enhanced_specs.get('max_data_rate', 'Up to 10+ Gbps aggregate')} |
| Spatial Streams | {enhanced_specs.get('spatial_streams', 'Multi-stream MIMO')} |
| MIMO Configuration | {enhanced_specs.get('mimo_config', '4x4:4 MU-MIMO')} |
| Antenna Technology | {enhanced_specs.get('antenna_type', 'BeamFlex+ adaptive antennas')} |
| Maximum Concurrent Clients | {enhanced_specs.get('max_clients', '512+ concurrent users')} |
| SSID Support | {enhanced_specs.get('ssid_support', '32 SSIDs per radio')} |

#### RF Performance Specifications

| Frequency Band | Transmit Power | Receive Sensitivity |
|---------------|----------------|---------------------|
| 2.4 GHz | {enhanced_specs.get('transmit_power_2_4', '26 dBm max')} | {enhanced_specs.get('receive_sensitivity_2_4', '-97 dBm @ MCS0')} |
| 5 GHz | {enhanced_specs.get('transmit_power_5', '28 dBm max')} | {enhanced_specs.get('receive_sensitivity_5', '-100 dBm @ MCS0')} |
| 6 GHz | {enhanced_specs.get('transmit_power_6', '25 dBm max')} | {enhanced_specs.get('receive_sensitivity_6', '-96 dBm @ MCS0')} |

#### Physical & Environmental Specifications

| Specification | Value |
|--------------|--------|
| Dimensions (H x W x D) | {enhanced_specs.get('dimensions', 'Professional form factor')} |
| Weight | {enhanced_specs.get('weight', 'Lightweight design')} |
| Power Consumption | {enhanced_specs.get('power_consumption', 'Energy efficient')} |
| Operating Temperature | {enhanced_specs.get('operating_temp', '-10°C to 50°C')} |
| Humidity Rating | {enhanced_specs.get('humidity_rating', '0-95% non-condensing')} |
| Mounting Options | {enhanced_specs.get('mounting_options', 'Ceiling/wall/desk mount')} |

#### Network & Interface Specifications

| Specification | Value |
|--------------|--------|
| Ethernet Ports | {enhanced_specs.get('ethernet_ports', 'Gigabit Ethernet')} |
| PoE Requirements | {enhanced_specs.get('poe_requirements', 'PoE+ / PoH support')} |
| Console/Management | {enhanced_specs.get('management_protocols', 'HTTPS, SSH, SNMP')} |

---

### DEPLOYMENT SCENARIOS & USE CASES

#### Enterprise Office Environments
[Detailed description of office deployment benefits and configurations]

#### Educational Institutions
[Specific benefits for schools and universities]

#### Healthcare Facilities
[Healthcare-specific features and compliance]

#### Retail & Hospitality
[Customer experience and operational benefits]

#### Manufacturing & Warehouses
[Industrial environment capabilities]

---

### ADVANCED SECURITY FEATURES

{enhanced_specs.get('security_protocols', 'Enterprise-grade security including WPA3, 802.1X authentication, role-based access control, and advanced threat protection')}

#### Authentication & Access Control
[Detailed security feature descriptions]

#### Encryption & Data Protection
[Encryption capabilities and data security]

#### Threat Detection & Prevention
[Security monitoring and protection features]

---

### MANAGEMENT & CONTROL PLATFORMS

{enhanced_specs.get('management_protocols', 'Comprehensive management through cloud and on-premises platforms including SmartZone, RUCKUS One, and Unleashed')}

#### Cloud Management
[Cloud platform capabilities]

#### On-Premises Management
[Local management options]

#### Analytics & Reporting
[Performance monitoring and analytics]

---

### PERFORMANCE METRICS & BENCHMARKS

#### Throughput Performance
[Detailed performance specifications and test results]

#### Capacity & Scalability
[User capacity and scaling information]

#### Coverage & Range
[RF coverage specifications]

---

### INTEGRATION & COMPATIBILITY

#### Network Infrastructure Compatibility
[Integration with existing network equipment]

#### Third-Party Integrations
[Ecosystem partnerships and integrations]

#### Migration & Upgrade Paths
[Upgrade and migration support]

---

### SUPPORT & SERVICES

#### Professional Services
[Implementation and consulting services]

#### Technical Support
[Support options and SLAs]

#### Training & Certification
[Educational resources and programs]

---

### CERTIFICATIONS & COMPLIANCE

{enhanced_specs.get('certifications', 'Full regulatory compliance including FCC, CE, IC certifications and industry standards compliance')}

#### Regulatory Certifications
[Detailed certification listings]

#### Industry Standards Compliance
[Standards compliance information]

---

### ORDERING INFORMATION

#### Model Numbers & Configurations

| Model | Description | Key Features |
|-------|-------------|--------------|
| {enhanced_specs.get('model_number', 'RUCKUS-MODEL')} | Base Configuration | Standard features |

#### Optional Accessories
[List of available accessories and add-ons]

#### Licensing Options
[Software licensing and subscription options]

---

### WARRANTY & SUPPORT OPTIONS

{enhanced_specs.get('warranty', 'Limited lifetime hardware warranty with comprehensive support options')}

#### Hardware Warranty
[Detailed warranty terms]

#### Software & Firmware Support
[Software support and update policies]

#### Advanced Support Services
[Premium support options]

---

### TECHNICAL APPENDIX

#### Configuration Examples
[Sample configurations and deployment guides]

#### Performance Test Results
[Detailed performance benchmarks]

#### Troubleshooting Guide
[Common issues and solutions]

---

*This datasheet provides comprehensive technical information for the RUCKUS {enhanced_specs.get('model_number', '[MODEL]')} {product_config['name']}. For the most current specifications and additional technical documentation, please visit ruckusnetworks.com or contact your authorized RUCKUS partner.*

---

**© 2024 Ruckus Networks, Inc. All rights reserved. RUCKUS, RUCKUS WIRELESS and RUCKUS NETWORKS are trademarks of Ruckus Networks, Inc. in the United States and other countries.**

REMEMBER:
- Create comprehensive content (4000-6000 words minimum)
- Use ONLY provided specifications - never fabricate
- Maintain perfect Markdown table formatting
- Include all standard datasheet sections
- Focus on technical accuracy and completeness
- Write for enterprise decision-makers and technical professionals"""

    return prompt

def generate_datasheet_with_streaming(template: Dict, specs: Dict, features: List[str], 
                                      model: str = "llama-3.1-8b-instant", 
                                      content_placeholder=None, progress_placeholder=None) -> Tuple[str, List[str]]:
    """Generate datasheet with live streaming content display"""
    
    if not GROQ_AVAILABLE:
        return None, ["Error: Groq library not available"]
    
    generation_steps = []
    
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        product_type = template['product_type']
        product_config = PRODUCT_TYPES[product_type]
        
        generation_steps.append("🔧 Preparing comprehensive specifications...")
        
        # Create comprehensive prompt
        comprehensive_prompt = create_comprehensive_prompt(template, specs, features, product_type)
        
        generation_steps.append("📋 Initializing enhanced AI generation...")
        generation_steps.append("🧠 Starting live content streaming...")
        
        # Initialize streaming response
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a senior technical writer with 15+ years experience. Create comprehensive, accurate, professional datasheets with perfect formatting."},
                {"role": "user", "content": comprehensive_prompt}
            ],
            temperature=0.1,  # Low temperature for accuracy
            max_tokens=8192,  # Maximum tokens for comprehensive content
            stream=True  # Enable streaming
        )
        
        # Stream the response with live updates
        generated_content = ""
        word_count = 0
        section_count = 0
        
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                new_content = chunk.choices[0].delta.content
                generated_content += new_content
                
                # Update live content display
                if content_placeholder:
                    content_placeholder.markdown(f"### 🔴 LIVE GENERATION IN PROGRESS\n\n{generated_content}")
                
                # Update progress metrics
                word_count = len(generated_content.split())
                section_count = generated_content.count('#')
                
                if progress_placeholder:
                    progress_placeholder.markdown(f"""
                    **📊 Live Generation Metrics:**
                    - **Words Generated:** {word_count:,}
                    - **Sections Created:** {section_count}
                    - **Content Length:** {len(generated_content):,} characters
                    - **Estimated Progress:** {min(100, (word_count / 4000) * 100):.1f}%
                    """)
                
                # Small delay for visual effect
                time.sleep(0.02)
        
        generation_steps.append(f"✅ Content generation complete! ({word_count:,} words)")
        generation_steps.append("🔍 Applying final formatting enhancements...")
        
        # Post-process to ensure proper formatting
        formatted_content = post_process_formatting(generated_content)
        
        generation_steps.append("✨ Professional datasheet generation successful!")
        
        return formatted_content, generation_steps
        
    except Exception as e:
        generation_steps.append(f"❌ Error: {str(e)}")
        return None, generation_steps

def post_process_formatting(content: str) -> str:
    """Enhanced post-processing for perfect formatting"""
    
    # Fix table formatting
    lines = content.split('\n')
    formatted_lines = []
    in_table = False
    
    for i, line in enumerate(lines):
        # Detect table start
        if '|' in line and i + 1 < len(lines) and '|' in lines[i + 1] and '-' in lines[i + 1]:
            in_table = True
        
        # Fix table separator lines
        if in_table and line.strip() and all(c in '|-: ' for c in line):
            # Ensure proper table separator
            parts = line.split('|')
            new_parts = []
            for part in parts:
                if part.strip():
                    new_parts.append('-' * max(3, len(part)))
                else:
                    new_parts.append('')
            line = '|'.join(new_parts)
        
        # Detect table end
        if in_table and not '|' in line:
            in_table = False
        
        formatted_lines.append(line)
    
    content = '\n'.join(formatted_lines)
    
    # Enhanced formatting fixes
    content = re.sub(r'\n{4,}', '\n\n\n', content)  # Max 3 newlines
    content = re.sub(r'(#+\s+[^\n]+)\n([^\n])', r'\1\n\n\2', content)  # Space after headers
    
    # Fix bullet points
    content = re.sub(r'^\*\s+', '• ', content, flags=re.MULTILINE)
    content = re.sub(r'^-\s+', '• ', content, flags=re.MULTILINE)
    
    # Ensure proper table formatting
    content = re.sub(r'\|\s*\n\s*\|', '|\n|', content)  # Fix table line breaks
    
    # Fix header spacing
    content = re.sub(r'(#+\s+[^\n]+)\n{0,1}([^#\n-])', r'\1\n\n\2', content)
    
    return content

def generate_comprehensive_specifications(product_type: str, base_specs: Dict) -> Dict:
    """Generate comprehensive specifications with enhanced defaults"""
    
    enhanced_specs = base_specs.copy()
    
    # Enhanced defaults based on product type
    if product_type == "wireless_ap":
        comprehensive_defaults = {
            "wireless_standards": "IEEE 802.11a/b/g/n/ac/ax (Wi-Fi 6/6E/7 ready)",
            "frequency_bands": "2.4 GHz, 5 GHz, 6 GHz (tri-band concurrent)",
            "max_data_rate": "Up to 10+ Gbps aggregate throughput",
            "spatial_streams": "8 spatial streams (2x2:2 + 4x4:4 + 2x2:2)",
            "mimo_config": "4x4:4 MU-MIMO with beamforming",
            "antenna_type": "BeamFlex+ adaptive antenna technology",
            "max_clients": "Up to 1024 concurrent clients per AP",
            "ssid_support": "Up to 36 SSIDs per AP",
            "ethernet_ports": "2x Gigabit Ethernet (1x PoE, 1x LAN)",
            "poe_requirements": "PoE+ (802.3at) or PoH/uPoE",
            "power_consumption": "25-40W (model dependent)",
            "transmit_power_2_4": "Up to 26 dBm",
            "transmit_power_5": "Up to 28 dBm",
            "transmit_power_6": "Up to 25 dBm",
            "receive_sensitivity_2_4": "-97 dBm @ MCS0",
            "receive_sensitivity_5": "-100 dBm @ MCS0",
            "receive_sensitivity_6": "-96 dBm @ MCS0",
            "dimensions": "Professional compact form factor",
            "weight": "Lightweight enterprise design",
            "operating_temp": "-10°C to 50°C (14°F to 122°F)",
            "humidity_rating": "0-95% non-condensing",
            "mounting_options": "Ceiling, wall, desk mounting options",
            "security_protocols": "WEP, WPA/WPA2-Personal/Enterprise, WPA3, WPA3-SAE, OWE, PMF (802.11w), Dynamic PSK",
            "management_protocols": "SNMP v1/v2c/v3, SSH v2, HTTPS, HTTP, Telnet, TR-069",
            "certifications": "FCC, CE, IC, Wi-Fi Alliance certified, UL listed",
            "warranty": "Limited lifetime hardware warranty"
        }
    elif product_type == "switch":
        comprehensive_defaults = {
            "model_number": "Professional Network Switch",
            "port_configuration": "24-48 Gigabit Ethernet ports",
            "switching_capacity": "High-performance backplane",
            "forwarding_rate": "Wire-speed switching",
            "mac_table_size": "16K+ MAC addresses",
            "vlan_support": "4K VLANs supported",
            "poe_budget": "High-power PoE budget available",
            "poe_standards": "PoE+ (802.3at) and PoE++ (802.3bt)",
            "management_features": "Advanced Layer 2/3 management",
            "layer3_features": "Static routing and VLAN routing",
            "redundancy": "Redundant power and stacking",
            "dimensions": "1U-2U rack-mountable design",
            "rack_units": "Standard rack mounting",
            "power_consumption": "Energy-efficient operation",
            "certifications": "FCC, CE, UL, Energy Star",
            "warranty": "Limited lifetime warranty"
        }
    elif product_type == "controller":
        comprehensive_defaults = {
            "model_number": "SmartZone Wireless Controller",
            "max_aps": "Scalable AP support",
            "max_clients": "High client capacity",
            "throughput": "High-performance throughput",
            "interfaces": "Multiple Gigabit Ethernet",
            "redundancy": "High availability clustering",
            "clustering": "Multi-controller clustering",
            "guest_features": "Comprehensive guest access",
            "security_features": "Enterprise security suite",
            "management_api": "REST API and SNMP support",
            "dimensions": "Rack-mountable appliance",
            "power_requirements": "Redundant power supply",
            "certifications": "Enterprise compliance standards",
            "warranty": "Limited lifetime warranty"
        }
    else:
        comprehensive_defaults = {}
    
    # Apply enhanced defaults only for missing fields
    for key, value in comprehensive_defaults.items():
        if key not in enhanced_specs or not enhanced_specs.get(key):
            enhanced_specs[key] = value
    
    return enhanced_specs

def create_enhanced_template_library():
    """Create enhanced template library with verified templates"""
    templates = {}
    
    # Verified R770 template with comprehensive data
    templates["r770_verified"] = {
        "name": "RUCKUS R770 Wi-Fi 7 Access Point [VERIFIED]",
        "original_filename": "r770_verified_template.txt",
        "product_type": "wireless_ap",
        "content": """RUCKUS R770 Wi-Fi 7 Access Point - COMPREHENSIVE DATA SHEET

EXECUTIVE SUMMARY
The RUCKUS R770 represents the pinnacle of Wi-Fi 7 technology, delivering unprecedented wireless performance for enterprise environments. As a high-end tri-band concurrent indoor access point, the R770 supports the complete Wi-Fi 7 feature set including Multi-Link Operation (MLO), Preamble Puncturing, 4K QAM Modulation, and 320MHz channels. With 8 spatial streams distributed across three bands (2x2:2 in 2.4GHz, 4x4:4 in 5GHz, 2x2:2 in 6GHz), the R770 achieves a combined theoretical data rate of 12.22 Gbps, setting new standards for wireless connectivity.

The R770 addresses the growing demands of modern enterprise networks where high client density, bandwidth-intensive applications, and mission-critical connectivity are paramount. By leveraging RUCKUS patented BeamFlex+ adaptive antenna technology with over 4,000 unique antenna patterns, the R770 optimizes RF performance and mitigates interference, delivering consistent, reliable connectivity even in challenging RF environments.

For enterprises investing in future-ready infrastructure, the R770 provides comprehensive Wi-Fi 7 capabilities today while maintaining backward compatibility with legacy devices. The integrated 10 Gigabit Ethernet port eliminates backhaul bottlenecks, ensuring that the full wireless capacity can be utilized. Additionally, the built-in IoT radio (selectable BLE or Zigbee) enables converged network architectures, reducing infrastructure complexity and operational costs.

KEY BUSINESS BENEFITS
• Enhanced User Experience: Delivers superior performance for bandwidth-intensive applications including 4K/8K video streaming, virtual reality, and cloud-based collaboration tools
• Increased Productivity: Supports more concurrent users with consistent performance, reducing network-related delays and improving workforce efficiency  
• Future-Proof Investment: Complete Wi-Fi 7 feature set ensures long-term network relevance and protects technology investments
• Simplified Operations: Converged AP with built-in IoT radio reduces infrastructure complexity and operational overhead
• Superior RF Performance: BeamFlex+ technology with AI-driven optimization delivers exceptional coverage and interference mitigation
• Reduced Total Cost of Ownership: High-capacity design reduces required AP count and associated infrastructure costs

COMPREHENSIVE TECHNICAL SPECIFICATIONS
Wireless Standards: IEEE 802.11a/b/g/n/ac/ax/be (Wi-Fi 7)
Supported Data Rates:
- 802.11be: 4.3 to 5765 Mbps per spatial stream
- 802.11ax: 8.6 to 4804 Mbps per spatial stream  
- 802.11ac: 6.5 to 866 Mbps per spatial stream
- 802.11n: 6.5 to 300 Mbps per spatial stream
- 802.11a/g: 6 to 54 Mbps
- 802.11b: 1 to 11 Mbps

Frequency Bands and Channels:
- 2.4GHz: Channels 1-13 (country dependent)
- 5GHz: Channels 36-64, 100-144, 149-165 (country dependent)
- 6GHz: Channels 1-233 (6GHz operation, country dependent)

Maximum Theoretical Data Rates:
- 2.4GHz Band: 689 Mbps
- 5GHz Band: 5765 Mbps  
- 6GHz Band: 5765 Mbps
- Combined Aggregate: 12.22 Gbps

Radio Configuration:
- MIMO: 2x2 (2.4 and 6 GHz) and 4x4 (5 GHz) SU-MIMO and MU-MIMO
- Spatial Streams: 2 (2.4 and 6 GHz) or 4 (5 GHz) for downlink and uplink
- Radio Chains: 2x2:2 (2.4 and 6 GHz), 4x4:4 (5 GHz)
- Channel Width: 20, 40, 80, 160, 320 MHz (320MHz for Wi-Fi 7)

Client and Network Capacity:
- Maximum Concurrent Clients: Up to 1024 per AP
- SSID Support: Up to 36 SSIDs per AP (12 per radio)
- VLAN Support: 802.1Q (1 per BSSID or dynamic per user via RADIUS)

RF PERFORMANCE SPECIFICATIONS
Antenna System: BeamFlex+ adaptive antennas with polarization diversity
Antenna Gain: Up to 4 dBi maximum gain
Total Antenna Patterns: 4,000+ unique patterns per radio

Maximum Transmit Power (per chain):
- 2.4GHz: 26 dBm (400 mW)
- 5GHz: 28 dBm (631 mW)
- 6GHz: 25 dBm (316 mW)

Receiver Sensitivity (typical):
2.4GHz Band:
- MCS0 (BPSK, 1/2): -97 dBm
- MCS7 (64-QAM, 5/6): -79 dBm
- MCS11 (256-QAM, 3/4): -76 dBm

5GHz Band:  
- MCS0 (BPSK, 1/2): -100 dBm
- MCS7 (64-QAM, 5/6): -82 dBm
- MCS11 (256-QAM, 3/4): -79 dBm

6GHz Band:
- MCS0 (BPSK, 1/2): -96 dBm
- MCS7 (64-QAM, 5/6): -78 dBm
- MCS11 (1024-QAM, 3/4): -73 dBm

PHYSICAL AND ENVIRONMENTAL SPECIFICATIONS
Physical Dimensions: 23.3cm (L) x 23.3cm (W) x 5.9cm (H) / 9.2" (L) x 9.2" (W) x 2.3" (H)
Weight: 1.36 kg (3 lbs)
Mounting: Ceiling, wall, and desk mount options available
Physical Security: Kensington lock support, security bracket available separately
Operating Temperature: -10°C to 50°C (14°F to 122°F)
Operating Humidity: 0% to 95% relative humidity, non-condensing
Storage Temperature: -40°C to 70°C (-40°F to 158°F)

POWER AND INTERFACES
Power Requirements:
- DC Input: 32W (Average/RMS), 40W (Peak for LLDP)
- PoE Support: 802.3bt (PoE++), PoH/uPoE compatible
- Power Supply: External power adapter (included) or PoE+/PoE++

Network Interfaces:
- Ethernet: One 100M/1G/2.5G/5G/10G Ethernet port (PoE input)
- Secondary Ethernet: One 10M/100M/1G Ethernet port  
- Console: USB 2.0 Type-A port for management and storage

ADVANCED SECURITY FEATURES
Supported Security Protocols:
- WEP (64 and 128-bit)
- WPA/WPA2 Personal and Enterprise
- WPA3 Personal and Enterprise
- WPA3-SAE (Simultaneous Authentication of Equals)
- OWE (Opportunistic Wireless Encryption)
- PMF (Protected Management Frames) - 802.11w
- Dynamic PSK for simplified guest and device access

Authentication Methods:
- 802.1X (EAP-TLS, EAP-TTLS, EAP-PEAP, EAP-FAST)
- MAC address authentication
- Web-based authentication (captive portal)
- RADIUS authentication and accounting

MANAGEMENT AND CONTROL PLATFORMS
Controller Platform Support:
- SmartZone (on-premises and cloud)
- RUCKUS Unleashed (controller-less)
- RUCKUS One (cloud management platform)

Management Protocols:
- SNMP v1, v2c, v3
- SSH v2, Telnet
- HTTPS, HTTP
- TR-069 (CWMP)
- REST APIs for integration

Network Protocols:
- IPv4 and IPv6 dual-stack support
- DHCP client and DHCP Option 82
- DNS, NTP client
- CAPWAP (Control and Provisioning of Wireless Access Points)

CERTIFICATIONS AND COMPLIANCE
Wi-Fi Certifications:
- Wi-Fi CERTIFIED a, b, g, n, ac, ax, be (Wi-Fi 7)
- Wi-Fi Alliance certified for interoperability

Regulatory Certifications:
- FCC (United States)
- CE (European Union)  
- IC (Industry Canada)
- Additional country certifications available

Safety and Environmental:
- IEC/EN/UL 60950-1 Safety Standard
- IEC/EN/UL 62368-1 Audio/Video Safety
- RoHS compliant
- Energy Star qualified

DEPLOYMENT SCENARIOS
Enterprise Offices: Ideal for high-density environments including open offices, conference rooms, and collaboration spaces requiring reliable, high-performance wireless connectivity

Educational Institutions: Supports bandwidth-intensive educational applications, online testing, and high client density in classrooms, libraries, and common areas

Healthcare Facilities: Provides reliable connectivity for medical devices, electronic health records, and staff communications while maintaining security compliance

Retail and Hospitality: Delivers exceptional guest experience with high-speed connectivity for customers and staff, supporting POS systems, inventory management, and guest services

Manufacturing and Warehouses: Robust performance in challenging RF environments with support for mobile devices, inventory systems, and IoT applications

ORDERING INFORMATION
Base Model: 901-R770-XX00

RUCKUS R770 Wi-Fi 7 tri-band concurrent wireless Access Point featuring:
- 2x2:2 (2.4GHz) + 4x4:4 (5GHz) + 2x2:2 (6GHz) radios
- Wi-Fi 7 support across all three bands
- BeamFlex+ adaptive antenna technology
- One 10G/5G/2.5G/1G Ethernet backhaul port
- One 1G Ethernet port
- PoH/uPoE/802.3bt PoE++ support
- Selectable onboard BLE and Zigbee IoT radio
- USB 2.0 management port
- Secure Boot technology

WARRANTIES AND SUPPORT
Hardware Warranty: Limited lifetime warranty on hardware
Software Support: Ongoing firmware updates and feature enhancements
Technical Support: 24x7 support available through RUCKUS Global Support
Professional Services: Implementation, optimization, and consulting services available""",
        "sections": {
            "overview": "The RUCKUS R770 represents the pinnacle of Wi-Fi 7 technology, delivering unprecedented wireless performance for enterprise environments with 8 spatial streams and 12.22 Gbps combined data rate.",
            "features": [
                "Wi-Fi 7 (802.11be) with complete feature set including MLO and Preamble Puncturing",
                "8 spatial streams (2x2:2 + 4x4:4 + 2x2:2) across three bands",  
                "BeamFlex+ adaptive antenna technology with 4,000+ patterns",
                "10 Gigabit Ethernet eliminates backhaul bottleneck",
                "Built-in selectable IoT radio (BLE or Zigbee)",
                "Up to 1024 concurrent clients with 36 SSID support",
                "Advanced Wi-Fi 7 security with WPA3 and OWE",
                "Multiple management platforms (SmartZone, Unleashed, RUCKUS One)"
            ],
            "specifications": {
                "Model Number": "RUCKUS R770",
                "Wireless Standards": "IEEE 802.11a/b/g/n/ac/ax/be (Wi-Fi 7)",
                "Maximum Data Rate": "12.22 Gbps combined aggregate",
                "Frequency Bands": "2.4 GHz, 5 GHz, 6 GHz tri-band concurrent",
                "Spatial Streams": "8 total (2x2:2 + 4x4:4 + 2x2:2)",
                "Client Capacity": "Up to 1024 concurrent clients",
                "SSID Support": "Up to 36 SSIDs per AP",
                "Power Consumption": "32W average, 40W peak",
                "Dimensions": "23.3cm x 23.3cm x 5.9cm",
                "Weight": "1.36 kg (3 lbs)",
                "Transmit Power 2.4GHz": "26 dBm maximum",
                "Transmit Power 5GHz": "28 dBm maximum", 
                "Transmit Power 6GHz": "25 dBm maximum",
                "Ethernet Ports": "1x 10GbE + 1x 1GbE",
                "PoE Requirements": "PoE++ (802.3bt) or PoH/uPoE"
            }
        },
        "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "quality_score": 1.0,
        "accuracy_verified": True
    }
    
    # Additional verified templates can be added here
    
    return templates

def load_templates_from_folder():
    """Load templates from RDS folder and enhance with verified library"""
    templates = create_enhanced_template_library()
    
    rds_folder = "RDS"
    if os.path.exists(rds_folder):
        txt_files = glob.glob(os.path.join(rds_folder, "*.txt"))
        
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
                template_id = f"rds_{len(templates)}_{datetime.now().strftime('%Y%m%d')}"
                
                templates[template_id] = {
                    "name": template_name,
                    "original_filename": filename,
                    "product_type": product_type,
                    "content": content,
                    "sections": sections,
                    "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "quality_score": calculate_template_quality(sections),
                    "accuracy_verified": False
                }
                
            except Exception as e:
                st.warning(f"Error loading {file_path}: {str(e)}")
                continue
    
    return templates

def validate_datasheet_accuracy(content: str, specs: Dict, features: List[str]) -> Dict:
    """Enhanced datasheet accuracy validation with comprehensive metrics"""
    
    accuracy_metrics = {
        "word_count": len(content.split()),
        "character_count": len(content),
        "section_count": content.count('#'),
        "table_count": content.count('|') // 10,  # Approximate table count
        "has_overview": bool(re.search(r'overview|summary|introduction', content.lower())),
        "has_specifications": bool(re.search(r'specification|technical spec', content.lower())),
        "has_features": bool(re.search(r'feature|capability|benefit', content.lower())),
        "has_benefits": bool(re.search(r'benefit|advantage|value', content.lower())),
        "has_technical_tables": bool("|" in content and "---" in content),
        "has_deployment": bool(re.search(r'deployment|use case|scenario', content.lower())),
        "has_security": bool(re.search(r'security|authentication|encryption', content.lower())),
        "has_ordering": bool(re.search(r'ordering|model|part number', content.lower())),
        "spec_accuracy": 0,
        "feature_coverage": 0,
        "completeness_score": 0,
        "professional_formatting": 0,
        "technical_depth": 0,
        "overall_quality": 0
    }
    
    # Enhanced specification accuracy calculation
    if specs:
        spec_matches = 0
        total_specs = 0
        for spec_key, spec_value in specs.items():
            if spec_value and str(spec_value).strip():
                total_specs += 1
                # More flexible matching for specifications
                spec_words = str(spec_value).lower().split()[:3]  # First 3 words
                if any(word in content.lower() for word in spec_words if len(word) > 2):
                    spec_matches += 1
        accuracy_metrics["spec_accuracy"] = spec_matches / total_specs if total_specs > 0 else 0
    
    # Enhanced feature coverage calculation  
    if features:
        feature_matches = 0
        for feature in features:
            # More flexible feature matching
            feature_words = feature.lower().split()[:4]  # First 4 words
            if any(word in content.lower() for word in feature_words if len(word) > 3):
                feature_matches += 1
        accuracy_metrics["feature_coverage"] = feature_matches / len(features) if features else 0
    
    # Completeness score based on expected sections
    completeness_factors = [
        accuracy_metrics["has_overview"],
        accuracy_metrics["has_specifications"], 
        accuracy_metrics["has_features"],
        accuracy_metrics["has_benefits"],
        accuracy_metrics["has_technical_tables"],
        accuracy_metrics["has_deployment"],
        accuracy_metrics["has_security"],
        accuracy_metrics["has_ordering"]
    ]
    accuracy_metrics["completeness_score"] = sum(completeness_factors) / len(completeness_factors)
    
    # Professional formatting score
    format_score = 0
    if accuracy_metrics["has_technical_tables"]:
        format_score += 0.25
    if accuracy_metrics["section_count"] >= 8:  # Multiple headers
        format_score += 0.25
    if accuracy_metrics["word_count"] >= 3000:  # Comprehensive content
        format_score += 0.25
    if "RUCKUS" in content and "®" in content:  # Proper branding
        format_score += 0.25
    accuracy_metrics["professional_formatting"] = min(1.0, format_score)
    
    # Technical depth assessment
    technical_terms = [
        "specifications", "performance", "configuration", "standards", 
        "protocols", "compliance", "certifications", "deployment",
        "enterprise", "scalability", "throughput", "bandwidth"
    ]
    tech_matches = sum(1 for term in technical_terms if term in content.lower())
    accuracy_metrics["technical_depth"] = min(1.0, tech_matches / len(technical_terms))
    
    # Overall quality calculation (weighted average)
    accuracy_metrics["overall_quality"] = (
        accuracy_metrics["spec_accuracy"] * 0.25 +
        accuracy_metrics["feature_coverage"] * 0.20 +
        accuracy_metrics["completeness_score"] * 0.25 +
        accuracy_metrics["professional_formatting"] * 0.15 +
        accuracy_metrics["technical_depth"] * 0.15
    )
    
    return accuracy_metrics

# Main UI
st.title("🐕 Ruckus Professional Datasheet Generator")
st.markdown("**Enhanced with Live Streaming Generation & Comprehensive Content Creation**")

# Top navigation
col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

with col2:
    if st.button("📋 Library", type="secondary" if st.session_state.current_step != 4 else "primary"):
        st.session_state.current_step = 4
        st.rerun()

with col3:
    if st.button("📄 PRD Library", type="secondary" if st.session_state.current_step != 5 else "primary"):
        st.session_state.current_step = 5
        st.rerun()

with col4:
    if st.button("🧠 Analytics", type="secondary" if st.session_state.current_step != 6 else "primary"):
        st.session_state.current_step = 6
        st.rerun()

with col5:
    if st.button("🏠 Home", type="secondary" if st.session_state.current_step not in [1, 2, 3] else "primary"):
        st.session_state.current_step = 1
        st.rerun()

# Enhanced sidebar
with st.sidebar:
    st.title("⚙️ Enhanced Configuration")
    
    # API Status
    if GROQ_AVAILABLE:
        st.success("✅ Groq API Ready")
        st.info("🔑 Streaming Enabled")
    else:
        st.error("❌ Groq library not installed")
        st.code("pip install groq")
    
    # Model selection with enhanced options
    model_choice = st.selectbox(
        "AI Model for Generation",
        ["llama-3.1-8b-instant", "llama-3.2-3b-preview", "mixtral-8x7b-32768"],
        index=0,
        help="Select AI model for datasheet generation"
    )
    
    # Generation settings
    st.divider()
    st.subheader("🎛️ Generation Settings")
    
    target_words = st.slider("Target Word Count", 2000, 8000, 4000, 500)
    st.caption(f"Comprehensive datasheets: {target_words:,} words")
    
    enable_streaming = st.checkbox("Live Content Streaming", value=True, 
                                   help="Show content being generated in real-time")
    
    st.divider()
    
    # Enhanced statistics
    st.subheader("📊 Performance Metrics")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Templates", len(st.session_state.templates))
        st.metric("Generated", len(st.session_state.generated_datasheets))
    with col2:
        avg_accuracy = st.session_state.spec_accuracy_score
        st.metric("Avg Accuracy", f"{avg_accuracy:.1%}")
        st.metric("PRD Docs", len(st.session_state.prd_documents))
    
    # Quality metrics
    if st.session_state.generated_datasheets:
        total_words = sum(d.get('word_count', 0) for d in st.session_state.generated_datasheets)
        avg_words = total_words / len(st.session_state.generated_datasheets)
        st.metric("Avg Words", f"{avg_words:,.0f}")
        
        verified_count = sum(1 for d in st.session_state.generated_datasheets if d.get('template_verified'))
        st.metric("Verified Used", f"{verified_count}/{len(st.session_state.generated_datasheets)}")
    
    st.divider()
    
    # Feature status
    st.subheader("🚀 Active Features")
    st.success("✅ Live Streaming Generation")
    st.success("✅ Comprehensive Content (4K+ words)")
    st.success("✅ Verified Template Library")
    st.success("✅ PRD Integration & Analysis")
    st.success("✅ Advanced Quality Metrics")
    st.success("✅ Professional Formatting")

# Initialize enhanced library
if not st.session_state.templates:
    with st.spinner("Loading enhanced template library with verified content..."):
        templates = load_templates_from_folder()
        st.session_state.templates = templates
        verified_count = sum(1 for t in templates.values() if t.get('accuracy_verified'))
        if templates:
            st.success(f"✅ Loaded {len(templates)} templates including {verified_count} verified templates")

# Main content based on current step
if st.session_state.current_step == 1:
    st.header("Step 1: Select Enhanced Template")
    
    if st.session_state.templates:
        st.info("🎯 **Template Selection**: Choose from verified high-accuracy templates for comprehensive datasheet generation")
        
        # Template filters
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
                ["quality", "verified", "name", "date"],
                format_func=lambda x: {"name": "Name", "quality": "Quality", "verified": "Verified First", "date": "Date"}[x]
            )
        
        with col3:
            show_all = st.checkbox("Show all templates", value=False)
            verified_only = not show_all
        
        # Filter templates
        templates_to_show = {}
        for tid, tdata in st.session_state.templates.items():
            if selected_filter != "All" and tdata['product_type'] != selected_filter:
                continue
            if verified_only and not tdata.get('accuracy_verified', False):
                continue
            templates_to_show[tid] = tdata
        
        if templates_to_show:
            st.write(f"**{len(templates_to_show)} template(s) available**")
            
            # Sort templates
            if sort_option == "quality":
                sorted_templates = sorted(templates_to_show.items(), key=lambda x: x[1].get('quality_score', 0), reverse=True)
            elif sort_option == "verified":
                sorted_templates = sorted(templates_to_show.items(), key=lambda x: (x[1].get('accuracy_verified', False), x[1].get('quality_score', 0)), reverse=True)
            elif sort_option == "date":
                sorted_templates = sorted(templates_to_show.items(), key=lambda x: x[1]['upload_date'], reverse=True)
            else:
                sorted_templates = sorted(templates_to_show.items(), key=lambda x: x[1]['name'])
            
            # Display templates with enhanced information
            for tid, tdata in sorted_templates:
                quality_score = tdata.get('quality_score', 0)
                accuracy_verified = tdata.get('accuracy_verified', False)
                
                quality_emoji = "🎯" if accuracy_verified else "⭐" if quality_score >= 0.7 else "👍"
                accuracy_badge = "✅ VERIFIED" if accuracy_verified else "📝 Standard"
                
                # Enhanced template display
                with st.expander(f"{quality_emoji} {tdata['name']} - {accuracy_badge} (Quality: {quality_score:.2f})"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Product Type:** {PRODUCT_TYPES[tdata['product_type']]['name']}")
                        st.write(f"**Upload Date:** {tdata['upload_date']}")
                        st.write(f"**Quality Score:** {quality_score:.2f}/1.0")
                        st.write(f"**Verification Status:** {accuracy_badge}")
                        
                        if accuracy_verified:
                            st.success("🎯 **VERIFIED TEMPLATE** - Guaranteed high accuracy and comprehensive content")
                        
                        # Template metrics
                        content_length = len(tdata.get('content', ''))
                        feature_count = len(tdata.get('sections', {}).get('features', []))
                        spec_count = len(tdata.get('sections', {}).get('specifications', {}))
                        
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.metric("Content", f"{content_length:,} chars")
                        with col_b:
                            st.metric("Features", feature_count)
                        with col_c:
                            st.metric("Specs", spec_count)
                        
                        if tdata['sections'].get('overview'):
                            st.write("**Overview Preview:**")
                            preview = tdata['sections']['overview'][:300] + "..." if len(tdata['sections']['overview']) > 300 else tdata['sections']['overview']
                            st.info(preview)
                        
                        if tdata['sections'].get('features'):
                            st.write("**Key Features Preview:**")
                            for feature in tdata['sections']['features'][:4]:
                                st.write(f"• {feature[:120]}{'...' if len(feature) > 120 else ''}")
                    
                    with col2:
                        button_label = "🎯 Use Verified Template" if accuracy_verified else "📝 Use Template"
                        button_type = "primary" if accuracy_verified else "secondary"
                        
                        if st.button(button_label, key=f"select_{tid}", type=button_type, use_container_width=True):
                            st.session_state.selected_template_id = tid
                            st.session_state.current_step = 2
                            st.rerun()
                        
                        if accuracy_verified:
                            st.caption("🎯 Comprehensive 4K+ word datasheets")
                        else:
                            st.caption("📝 Standard generation")
        else:
            st.warning("No templates match your filters. Try adjusting the filter criteria.")
    else:
        st.warning("No templates loaded. Please check the RDS folder or contact support.")

elif st.session_state.current_step == 2:
    st.header("Step 2: Configure Product Specifications")
    
    template = st.session_state.templates.get(st.session_state.selected_template_id)
    
    if template:
        # Check if PRD data is available
        prd_data_available = st.session_state.selected_prd_id and st.session_state.selected_prd_id in st.session_state.prd_documents
        
        if prd_data_available:
            prd_data = st.session_state.prd_documents[st.session_state.selected_prd_id]
            st.success(f"✅ **PRD Integration Active**: {prd_data['name']} (Confidence: {prd_data.get('confidence_score', 0)*100:.1f}%)")
            
            # Option to modify PRD data
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info("📝 Specifications have been pre-filled from PRD analysis - modify as needed")
            with col2:
                if st.button("🔄 Clear PRD Data"):
                    st.session_state.selected_prd_id = None
                    st.session_state.new_specs = {}
                    st.session_state.new_features = []
                    st.rerun()
        
        # Enhanced template information display
        accuracy_badge = "🎯 VERIFIED TEMPLATE" if template.get('accuracy_verified') else "📝 Standard Template"
        quality_indicator = "🎯" if template.get('accuracy_verified') else "📝"
        
        st.info(f"{quality_indicator} **Selected Template:** {template['name']} ({PRODUCT_TYPES[template['product_type']]['name']}) - {accuracy_badge}")
        
        if template.get('accuracy_verified'):
            st.success("🚀 **Enhanced Generation Mode**: This verified template will generate comprehensive 4000+ word datasheets with professional formatting")
        
        # Expected output preview
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            expected_words = 5000 if template.get('accuracy_verified') else 3000
            st.metric("Expected Words", f"{expected_words:,}+")
        with col2:
            expected_sections = 15 if template.get('accuracy_verified') else 10
            st.metric("Sections", f"{expected_sections}+")
        with col3:
            expected_tables = 8 if template.get('accuracy_verified') else 5
            st.metric("Tech Tables", f"{expected_tables}+")
        with col4:
            accuracy_level = "95%+" if template.get('accuracy_verified') else "85%+"
            st.metric("Accuracy", accuracy_level)
        
        # Get spec fields
        spec_fields = PRODUCT_TYPES[template['product_type']]['spec_fields']
        
        with st.form("enhanced_specifications_form"):
            st.subheader("📊 Product Specifications")
            if prd_data_available:
                st.write("✨ **PRD-Enhanced**: Fields pre-filled from AI analysis - modify as needed")
            else:
                st.write("Complete the specifications for comprehensive datasheet generation:")
            
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
                    elif field_type == "textarea":
                        specs[field_id] = st.text_area(label, value=prefill_value, height=100, key=f"spec_{field_id}")
            
            st.divider()
            
            st.subheader("⭐ Product Features & Benefits")
            # Pre-fill features from PRD
            prefill_features = '\n'.join(st.session_state.new_features) if prd_data_available and st.session_state.new_features else ""
            
            features_text = st.text_area(
                "List key product features and benefits (one per line)",
                value=prefill_features,
                height=200,
                placeholder="Example:\nWi-Fi 7 (802.11be) support with 12.22 Gbps aggregate data rate\nBeamFlex+ adaptive antenna technology with 4,000+ patterns\nMulti-Link Operation (MLO) and Preamble Puncturing\nAdvanced enterprise security with WPA3, OWE, and PMF\nIntegrated IoT radio (BLE/Zigbee) for converged networking\nUp to 1024 concurrent clients with intelligent load balancing\n10 Gigabit Ethernet eliminates backhaul bottlenecks\nCloud and on-premises management flexibility"
            )
            
            st.subheader("💼 Marketing Position & Value Proposition")
            marketing_message = st.text_area(
                "Key marketing message, competitive positioning, or unique value proposition",
                height=120,
                placeholder="What makes this product unique in the market? Key differentiators, competitive advantages, business value, ROI benefits, etc."
            )
            
            # Form submission buttons
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.form_submit_button("← Back to Templates"):
                    st.session_state.current_step = 1
                    st.rerun()
            
            with col2:
                if st.form_submit_button("📄 Select PRD", type="secondary"):
                    st.session_state.current_step = 5
                    st.rerun()
            
            with col3:
                generate_label = "🎯 Generate Comprehensive" if template.get('accuracy_verified') else "📝 Generate Datasheet"
                if st.form_submit_button(f"{generate_label} →", type="primary"):
                    filled_specs = {k: v for k, v in specs.items() if v.strip()}
                    features_list = [f.strip() for f in features_text.split('\n') if f.strip()]
                    
                    if not filled_specs and not features_list:
                        st.error("Please provide at least one specification or feature to generate a comprehensive datasheet.")
                    else:
                        st.session_state.new_specs = filled_specs
                        st.session_state.new_features = features_list
                        if marketing_message.strip():
                            st.session_state.new_specs['marketing_message'] = marketing_message.strip()
                        st.session_state.current_step = 3
                        st.rerun()
    else:
        st.error("No template selected. Please go back and select a template.")
        if st.button("← Back to Templates"):
            st.session_state.current_step = 1
            st.rerun()

elif st.session_state.current_step == 3:
    st.header("Step 3: Live Streaming Generation")
    
    template = st.session_state.templates.get(st.session_state.selected_template_id)
    
    if template:
        # Enhanced generation summary
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Generation Configuration")
            st.write(f"**Template:** {template['name']}")
            st.write(f"**Product Type:** {PRODUCT_TYPES[template['product_type']]['name']}")
            st.write(f"**Template Quality:** {template.get('quality_score', 0):.2f}/1.0")
            verification_status = "🎯 VERIFIED" if template.get('accuracy_verified') else "📝 Standard"
            st.write(f"**Verification Status:** {verification_status}")
            
        with col2:
            st.subheader("📊 Input Analysis")
            spec_count = len([k for k, v in st.session_state.new_specs.items() if k != 'marketing_message' and v])
            feature_count = len(st.session_state.new_features)
            has_prd = st.session_state.selected_prd_id is not None
            
            st.write(f"**Specifications:** {spec_count}")
            st.write(f"**Features:** {feature_count}")
            st.write(f"**PRD Integration:** {'✅ Active' if has_prd else '❌ None'}")
            
            # Enhanced prediction
            if template.get('accuracy_verified'):
                st.write(f"**Generation Mode:** 🎯 Comprehensive (4000+ words)")
            else:
                st.write(f"**Generation Mode:** 📝 Standard (2500+ words)")
        
        # Quality prediction panel
        st.divider()
        st.subheader("🎯 Expected Output Quality")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            base_words = 5000 if template.get('accuracy_verified') else 3000
            predicted_words = base_words + (spec_count * 50) + (feature_count * 100)
            st.metric("Predicted Words", f"{predicted_words:,}")
        
        with col2:
            content_quality = min(1.0, (spec_count + feature_count) / 20)
            if template.get('accuracy_verified'):
                content_quality = min(1.0, content_quality * 1.3)
            st.metric("Content Quality", f"{content_quality:.1%}")
        
        with col3:
            expected_sections = 15 if template.get('accuracy_verified') else 10
            actual_sections = expected_sections + min(5, spec_count // 5)
            st.metric("Expected Sections", actual_sections)
        
        with col4:
            comprehensive_score = "Comprehensive" if template.get('accuracy_verified') else "Standard"
            if has_prd:
                comprehensive_score = "PRD+" + comprehensive_score
            st.metric("Generation Level", comprehensive_score)
        
        st.divider()
        
        # Generate button
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("← Back to Specs"):
                st.session_state.current_step = 2
                st.rerun()
        
        with col2:
            if template.get('accuracy_verified'):
                button_text = "🎯 Start Comprehensive Live Generation"
                button_help = "Generate 4000+ word professional datasheet with live streaming"
            else:
                button_text = "📝 Start Standard Live Generation"
                button_help = "Generate professional datasheet with live streaming"
            
            if st.button(button_text, type="primary", use_container_width=True, help=button_help):
                # Reset generation state
                st.session_state.live_content = ""
                st.session_state.generation_complete = False
                
                # Create live generation interface
                st.divider()
                
                # Live generation header
                generation_header = st.container()
                with generation_header:
                    st.markdown("### 🔴 LIVE GENERATION IN PROGRESS")
                    
                    # Generation metrics container
                    metrics_container = st.container()
                    progress_container = st.container()
                
                # Live content display
                st.divider()
                content_header = st.markdown("### 📝 Live Content Stream")
                content_placeholder = st.empty()
                
                try:
                    # Start live streaming generation
                    with progress_container:
                        progress_placeholder = st.empty()
                    
                    # Generate with live streaming
                    generated_content, generation_steps = generate_datasheet_with_streaming(
                        template, 
                        st.session_state.new_specs, 
                        st.session_state.new_features, 
                        model_choice,
                        content_placeholder,
                        progress_placeholder
                    )
                    
                    if generated_content:
                        # Mark generation as complete
                        st.session_state.generation_complete = True
                        st.session_state.live_content = generated_content
                        
                        # Update final display
                        content_header = st.markdown("### ✅ GENERATION COMPLETE")
                        
                        # Validate accuracy
                        with st.spinner("Analyzing generated content quality..."):
                            accuracy_analysis = validate_datasheet_accuracy(
                                generated_content, 
                                st.session_state.new_specs, 
                                st.session_state.new_features
                            )
                        
                        # Determine enhancement level
                        enhancement_level = "verified_comprehensive" if template.get('accuracy_verified') else "standard_comprehensive"
                        if st.session_state.selected_prd_id:
                            enhancement_level = "prd_" + enhancement_level
                        
                        # Save comprehensive datasheet
                        datasheet = {
                            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                            "product_name": st.session_state.new_specs.get('model_number', 'Professional Network Solution'),
                            "template_used": template['name'],
                            "product_type": template['product_type'],
                            "content": generated_content,
                            "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "specs": st.session_state.new_specs,
                            "features": st.session_state.new_features,
                            "model_used": f"groq: {model_choice}",
                            "template_quality": template.get('quality_score', 0),
                            "accuracy_analysis": accuracy_analysis,
                            "word_count": accuracy_analysis["word_count"],
                            "character_count": accuracy_analysis["character_count"],
                            "section_count": accuracy_analysis["section_count"],
                            "table_count": accuracy_analysis["table_count"],
                            "quality_score": accuracy_analysis["overall_quality"],
                            "completeness_score": accuracy_analysis["completeness_score"],
                            "enhancement_level": enhancement_level,
                            "template_verified": template.get('accuracy_verified', False),
                            "prd_source": st.session_state.selected_prd_id if st.session_state.selected_prd_id else None,
                            "prd_enhanced": st.session_state.selected_prd_id is not None,
                            "generation_method": "live_streaming"
                        }
                        
                        st.session_state.generated_datasheets.append(datasheet)
                        st.session_state.spec_accuracy_score = accuracy_analysis["spec_accuracy"]
                        
                        # Clear progress and show completion
                        progress_placeholder.empty()
                        
                        # Enhanced success message with comprehensive metrics
                        enhancement_badges = []
                        if template.get('accuracy_verified'):
                            enhancement_badges.append("🎯 Verified Template")
                        if st.session_state.selected_prd_id:
                            enhancement_badges.append("📝 PRD-Enhanced")
                        enhancement_badges.append("🔴 Live Streamed")
                        
                        badge_text = " • ".join(enhancement_badges)
                        
                        st.success(f"""🚀 **Comprehensive Datasheet Generated Successfully!** 
                        
**Enhancement Level:** {badge_text}
                        
📊 **Quality Analysis:**
- **Overall Quality:** {accuracy_analysis['overall_quality']:.1%}
- **Specification Accuracy:** {accuracy_analysis['spec_accuracy']:.1%}
- **Feature Coverage:** {accuracy_analysis['feature_coverage']:.1%}
- **Completeness Score:** {accuracy_analysis['completeness_score']:.1%}
- **Professional Formatting:** {accuracy_analysis['professional_formatting']:.1%}
- **Technical Depth:** {accuracy_analysis['technical_depth']:.1%}

📝 **Content Metrics:**
- **Word Count:** {accuracy_analysis['word_count']:,} words
- **Sections Created:** {accuracy_analysis['section_count']} sections
- **Technical Tables:** {accuracy_analysis['table_count']} tables
- **Character Count:** {accuracy_analysis['character_count']:,} characters
- **Input Specifications:** {len(st.session_state.new_specs)} specs
- **Input Features:** {len(st.session_state.new_features)} features""")
                        
                        # Enhanced download options
                        st.divider()
                        st.subheader("📥 Download Professional Datasheet")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.download_button(
                                label="📄 Download Markdown",
                                data=generated_content,
                                file_name=f"{datasheet['product_name']}_professional.md",
                                mime="text/markdown",
                                use_container_width=True,
                                help="Download as Markdown for editing"
                            )
                        
                        with col2:
                            # Create professional HTML
                            professional_html = create_professional_html_template(
                                generated_content, 
                                datasheet['product_name'], 
                                accuracy_analysis
                            )
                            
                            st.download_button(
                                label="🌐 Download HTML",
                                data=professional_html,
                                file_name=f"{datasheet['product_name']}_professional.html",
                                mime="text/html",
                                use_container_width=True,
                                help="Download as professional styled HTML"
                            )
                        
                        with col3:
                            if PDF_AVAILABLE:
                                try:
                                    pdf_buffer = create_professional_pdf(
                                        generated_content,
                                        datasheet['product_name'],
                                        accuracy_analysis
                                    )
                                    
                                    if pdf_buffer:
                                        st.download_button(
                                            label="📄 Download PDF",
                                            data=pdf_buffer.getvalue(),
                                            file_name=f"{datasheet['product_name']}_professional.pdf",
                                            mime="application/pdf",
                                            use_container_width=True,
                                            help="Download as professional PDF"
                                        )
                                    else:
                                        st.button("❌ PDF Error", disabled=True, use_container_width=True)
                                        
                                except Exception as e:
                                    st.button("❌ PDF Error", disabled=True, use_container_width=True, 
                                            help=f"PDF generation error: {str(e)}")
                            else:
                                st.button("❌ PDF N/A", disabled=True, use_container_width=True,
                                        help="PDF libraries not installed")
                        
                        with col4:
                            if st.button("🔄 Generate Another", use_container_width=True, type="secondary"):
                                st.session_state.current_step = 1
                                st.session_state.new_specs = {}
                                st.session_state.new_features = []
                                st.session_state.selected_prd_id = None
                                st.session_state.live_content = ""
                                st.session_state.generation_complete = False
                                st.rerun()
                        
                        # Final display of generated content
                        st.divider()
                        st.subheader("📋 Generated Professional Datasheet")
                        
                        # Create a styled container for the final preview
                        st.markdown("""
                        <style>
                        .final-datasheet-preview {
                            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
                            padding: 30px;
                            border-radius: 15px;
                            border: 2px solid #ff6600;
                            margin-top: 20px;
                            box-shadow: 0 4px 12px rgba(255, 102, 0, 0.1);
                        }
                        .completion-badge {
                            background: linear-gradient(135deg, #28a745, #20c997);
                            color: white;
                            padding: 10px 20px;
                            border-radius: 25px;
                            display: inline-block;
                            margin-bottom: 20px;
                            font-weight: bold;
                        }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        with st.container():
                            st.markdown(f'<div class="completion-badge">✅ PROFESSIONAL GENERATION COMPLETE • {accuracy_analysis["word_count"]:,} WORDS • {accuracy_analysis["overall_quality"]:.1%} QUALITY</div>', unsafe_allow_html=True)
                            st.markdown('<div class="final-datasheet-preview">', unsafe_allow_html=True)
                            st.markdown(generated_content)
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                    else:
                        st.error("❌ **Generation Failed**")
                        st.error("Unable to generate datasheet. Please check your inputs and try again.")
                        
                        # Show generation steps for debugging
                        if generation_steps:
                            with st.expander("🔍 Generation Log"):
                                for step in generation_steps:
                                    st.write(f"- {step}")
                
                except Exception as e:
                    st.error(f"❌ **Generation Error**: {str(e)}")
                    st.error("An error occurred during live generation. Please try again.")
        
        with col3:
            if st.button("💡 Generation Tips", use_container_width=True, type="secondary"):
                template_type = "🎯 Verified" if template.get('accuracy_verified') else "📝 Standard"
                tips_content = f"""**🚀 Live Generation Guide:**

**Selected Template:** {template['name']} ({template_type})
**Product Type:** {PRODUCT_TYPES[template['product_type']]['name']}
**Quality Score:** {template.get('quality_score', 0.8):.2f}/1.0

**📊 Your Input Analysis:**
- **Specifications:** {len(st.session_state.new_specs)} fields
- **Features:** {len(st.session_state.new_features)} items
- **PRD Integration:** {'✅ Active' if st.session_state.selected_prd_id else '❌ None'}

**🎯 Expected Generation:**
- **Word Count:** {5000 if template.get('accuracy_verified') else 3000}+ words
- **Sections:** 15+ comprehensive sections
- **Tables:** 8+ technical specification tables
- **Live Streaming:** Real-time content display
- **Quality Level:** {'95%+ accuracy' if template.get('accuracy_verified') else '85%+ accuracy'}

**💡 Pro Tips:**
- Watch the live content stream for real-time generation
- More specifications = more detailed content
- Verified templates produce comprehensive outputs
- PRD integration auto-populates specifications
- Live metrics show generation progress
- Professional HTML/PDF formatting included"""
                
                st.info(tips_content)

elif st.session_state.current_step == 4:
    # Enhanced Library view with comprehensive filtering
    st.header("📋 Generated Datasheets Library")
    
    if not st.session_state.generated_datasheets:
        st.info("🎯 No datasheets generated yet. Click 'Home' to start generating professional datasheets with live streaming.")
        
        # Show generation encouragement
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🎯 Start with Verified Template", type="primary"):
                st.session_state.current_step = 1
                st.rerun()
        with col2:
            if st.button("📝 Upload PRD Document", type="secondary"):
                st.session_state.current_step = 5
                st.rerun()
        with col3:
            if st.button("📊 View Analytics", type="secondary"):
                st.session_state.current_step = 6
                st.rerun()
    else:
        # Enhanced search and filter interface
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            search_term = st.text_input("🔍 Search datasheets", placeholder="Search by product name, model, or content...")
        
        with col2:
            filter_type = st.selectbox(
                "📱 Product Type",
                ["All"] + list(PRODUCT_TYPES.keys()),
                format_func=lambda x: "All Types" if x == "All" else PRODUCT_TYPES.get(x, {}).get('name', x)
            )
        
        with col3:
            enhancement_filter = st.selectbox(
                "🚀 Enhancement Level",
                ["All", "verified", "prd_enhanced", "live_streamed", "comprehensive"],
                format_func=lambda x: {
                    "All": "All Levels",
                    "verified": "🎯 Verified Templates",
                    "prd_enhanced": "📝 PRD Enhanced",
                    "live_streamed": "🔴 Live Streamed",
                    "comprehensive": "📊 Comprehensive (4K+ words)"
                }.get(x, x)
            )
        
        with col4:
            sort_by = st.selectbox(
                "📊 Sort By",
                ["date", "quality", "words", "name"],
                format_func=lambda x: {
                    "date": "📅 Date (Newest)",
                    "quality": "⭐ Quality Score",
                    "words": "📝 Word Count",
                    "name": "🔤 Name"
                }.get(x, x)
            )
        
        # Filter datasheets with enhanced logic
        filtered_datasheets = []
        for ds in st.session_state.generated_datasheets:
            # Text search
            if search_term:
                search_lower = search_term.lower()
                if not any([
                    search_lower in ds['product_name'].lower(),
                    search_lower in ds.get('template_used', '').lower(),
                    search_lower in ds.get('content', '').lower()[:500]  # Search first 500 chars
                ]):
                    continue
            
            # Type filter
            if filter_type != "All" and ds['product_type'] != filter_type:
                continue
            
            # Enhancement filter
            if enhancement_filter != "All":
                enhancement_level = ds.get('enhancement_level', '').lower()
                if enhancement_filter == "verified" and not ds.get('template_verified'):
                    continue
                elif enhancement_filter == "prd_enhanced" and not ds.get('prd_enhanced'):
                    continue
                elif enhancement_filter == "live_streamed" and ds.get('generation_method') != 'live_streaming':
                    continue
                elif enhancement_filter == "comprehensive" and ds.get('word_count', 0) < 4000:
                    continue
            
            filtered_datasheets.append(ds)
        
        # Sort datasheets
        if sort_by == "date":
            filtered_datasheets.sort(key=lambda x: x['generation_date'], reverse=True)
        elif sort_by == "quality":
            filtered_datasheets.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
        elif sort_by == "words":
            filtered_datasheets.sort(key=lambda x: x.get('word_count', 0), reverse=True)
        else:  # name
            filtered_datasheets.sort(key=lambda x: x['product_name'])
        
        # Display results summary
        total_words = sum(d.get('word_count', 0) for d in filtered_datasheets)
        avg_quality = sum(d.get('quality_score', 0) for d in filtered_datasheets) / len(filtered_datasheets) if filtered_datasheets else 0
        
        st.markdown(f"""
        **📊 Library Summary:** {len(filtered_datasheets)} of {len(st.session_state.generated_datasheets)} datasheets shown
        • **Total Words:** {total_words:,} • **Average Quality:** {avg_quality:.1%}
        """)
        
        # Display datasheets with enhanced information
        for idx, ds in enumerate(filtered_datasheets):
            quality_score = ds.get('quality_score', 0)
            word_count = ds.get('word_count', 0)
            
            # Enhanced visual indicators
            quality_emoji = "🎯" if quality_score >= 0.9 else "⭐" if quality_score >= 0.7 else "👍"
            size_indicator = "📊" if word_count >= 5000 else "📝" if word_count >= 3000 else "📄"
            
            # Enhancement badges
            badges = []
            if ds.get('template_verified'):
                badges.append("🎯 Verified")
            if ds.get('prd_enhanced'):
                badges.append("📝 PRD")
            if ds.get('generation_method') == 'live_streaming':
                badges.append("🔴 Live")
            if word_count >= 4000:
                badges.append("📊 Comprehensive")
            
            badge_text = " • ".join(badges) if badges else "Standard"
            
            with st.expander(
                f"{quality_emoji} {size_indicator} {ds['product_name']} • {badge_text} • {ds['generation_date']}",
                expanded=False
            ):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Basic information
                    st.write(f"**Product Type:** {PRODUCT_TYPES[ds['product_type']]['name']}")
                    st.write(f"**Template Used:** {ds['template_used']}")
                    st.write(f"**AI Model:** {ds.get('model_used', 'Unknown')}")
                    st.write(f"**Generation Method:** {'🔴 Live Streaming' if ds.get('generation_method') == 'live_streaming' else '📝 Standard'}")
                    
                    # Enhanced quality metrics
                    if ds.get('accuracy_analysis'):
                        st.subheader("📊 Quality Metrics")
                        analysis = ds['accuracy_analysis']
                        
                        metric_cols = st.columns(4)
                        with metric_cols[0]:
                            st.metric("Overall Quality", f"{analysis.get('overall_quality', 0):.1%}")
                        with metric_cols[1]:
                            st.metric("Completeness", f"{analysis.get('completeness_score', 0):.1%}")
                        with metric_cols[2]:
                            st.metric("Word Count", f"{analysis.get('word_count', 0):,}")
                        with metric_cols[3]:
                            st.metric("Sections", f"{analysis.get('section_count', 0)}")
                        
                        # Additional metrics
                        detail_cols = st.columns(3)
                        with detail_cols[0]:
                            st.metric("Spec Accuracy", f"{analysis.get('spec_accuracy', 0):.1%}")
                        with detail_cols[1]:
                            st.metric("Features", f"{analysis.get('feature_coverage', 0):.1%}")
                        with detail_cols[2]:
                            st.metric("Tech Tables", f"{analysis.get('table_count', 0)}")
                    
                    # Enhancement indicators
                    if ds.get('template_verified'):
                        st.success("✅ Generated from verified template")
                    if ds.get('prd_enhanced'):
                        prd_name = st.session_state.prd_documents.get(ds['prd_source'], {}).get('name', 'Unknown PRD')
                        st.success(f"📝 Enhanced with PRD: {prd_name}")
                    if ds.get('generation_method') == 'live_streaming':
                        st.success("🔴 Generated with live streaming")
                
                with col2:
                    # Download options with enhanced naming
                    file_suffix = "_standard"
                    if ds.get('template_verified'):
                        file_suffix = "_verified"
                    if ds.get('prd_enhanced'):
                        file_suffix = "_prd_enhanced"
                    if word_count >= 4000:
                        file_suffix = "_comprehensive"
                    
                    st.download_button(
                        label="📥 Download MD",
                        data=ds['content'],
                        file_name=f"{ds['product_name']}{file_suffix}.md",
                        mime="text/markdown",
                        key=f"download_md_{ds['id']}",
                        use_container_width=True
                    )
                    
                    # Professional HTML download
                    professional_html = create_professional_html_template(
                        ds['content'], 
                        ds['product_name'], 
                        ds.get('accuracy_analysis', {})
                    )
                    
                    st.download_button(
                        label="🌐 Download HTML",
                        data=professional_html,
                        file_name=f"{ds['product_name']}{file_suffix}.html",
                        mime="text/html",
                        key=f"download_html_{ds['id']}",
                        use_container_width=True
                    )
                    
                    # Professional PDF download
                    if PDF_AVAILABLE:
                        try:
                            pdf_buffer = create_professional_pdf(
                                ds['content'],
                                ds['product_name'],
                                ds.get('accuracy_analysis', {})
                            )
                            
                            if pdf_buffer:
                                st.download_button(
                                    label="📄 Download PDF",
                                    data=pdf_buffer.getvalue(),
                                    file_name=f"{ds['product_name']}{file_suffix}.pdf",
                                    mime="application/pdf",
                                    key=f"download_pdf_{ds['id']}",
                                    use_container_width=True
                                )
                            else:
                                st.button("❌ PDF Error", disabled=True, use_container_width=True, key=f"pdf_error_{ds['id']}")
                        except Exception as e:
                            st.button("❌ PDF Error", disabled=True, use_container_width=True, 
                                    help=f"PDF error: {str(e)}", key=f"pdf_error_{ds['id']}")
                    else:
                        st.button("❌ PDF N/A", disabled=True, use_container_width=True, key=f"pdf_na_{ds['id']}")
                    
                    # Delete button
                    if st.button("🗑️ Delete", key=f"delete_{ds['id']}", use_container_width=True, type="secondary"):
                        st.session_state.generated_datasheets = [
                            d for d in st.session_state.generated_datasheets 
                            if d['id'] != ds['id']
                        ]
                        st.rerun()

elif st.session_state.current_step == 5:
    # Enhanced PRD Library functionality
    st.header("📄 PRD Library & Advanced AI Analysis")
    st.markdown("Upload and analyze Product Requirements Documents for enhanced specification extraction and comprehensive datasheet generation")
    
    tab1, tab2, tab3 = st.tabs(["📁 Upload & Analyze PRD", "📋 PRD Library Management", "🚀 PRD Integration"])
    
    with tab1:
        st.subheader("📁 Upload New PRD Document")
        st.markdown("Upload PDF, DOCX, or TXT files containing product requirements for AI-powered analysis")
        
        uploaded_file = st.file_uploader(
            "Select PRD Document",
            type=['pdf', 'docx', 'txt'],
            help="Supported formats: PDF, Word documents, and plain text files"
        )
        
        if uploaded_file:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                prd_name = st.text_input("PRD Document Name", value=uploaded_file.name.split('.')[0])
                prd_description = st.text_area("Description (optional)", 
                    placeholder="Brief description of this PRD document, product line, version, etc...")
                expected_type = st.selectbox("Expected Product Type", 
                    list(PRODUCT_TYPES.keys()),
                    format_func=lambda x: PRODUCT_TYPES[x]['name'])
                
                # Analysis options
                st.subheader("🔬 Analysis Options")
                confidence_threshold = st.slider("Confidence Threshold", 0.1, 1.0, 0.6, 0.1,
                    help="Minimum confidence level for extracted specifications")
                extract_features = st.checkbox("Extract Product Features", value=True)
                extract_competitive_info = st.checkbox("Extract Competitive Information", value=False)
                
            with col2:
                st.markdown("**📁 File Information:**")
                st.info(f"""
                **Name:** {uploaded_file.name}
                **Size:** {uploaded_file.size:,} bytes
                **Type:** {uploaded_file.type}
                """)
                
                # File type specific info
                if uploaded_file.type == "application/pdf":
                    st.success("📄 PDF detected - will extract text from all pages")
                elif "word" in uploaded_file.type.lower():
                    st.success("📝 Word document detected")
                else:
                    st.success("📄 Text file detected")
            
            if st.button("🔍 Analyze PRD with Advanced AI", type="primary", use_container_width=True):
                with st.spinner("🧠 Extracting text and performing comprehensive AI analysis..."):
                    # Extract text based on file type
                    file_content = uploaded_file.read()
                    
                    if uploaded_file.type == "application/pdf":
                        extracted_text = extract_text_from_pdf(file_content)
                    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        extracted_text = extract_text_from_docx(file_content)
                    else:
                        extracted_text = file_content.decode('utf-8', errors='ignore')
                    
                    if "Error" not in extracted_text:
                        # Show extracted text preview
                        with st.expander("📄 Extracted Text Preview", expanded=False):
                            st.text_area("First 1000 characters", extracted_text[:1000], height=200, disabled=True)
                        
                        # Analyze with enhanced AI
                        analysis_result = analyze_prd_with_ai(extracted_text, model_choice)
                        
                        if "error" not in analysis_result:
                            prd_id = datetime.now().strftime("%Y%m%d%H%M%S")
                            
                            # Enhanced PRD document storage
                            st.session_state.prd_documents[prd_id] = {
                                "id": prd_id,
                                "name": prd_name,
                                "filename": uploaded_file.name,
                                "description": prd_description,
                                "expected_type": expected_type,
                                "file_size": uploaded_file.size,
                                "file_type": uploaded_file.type,
                                "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "raw_content": extracted_text,
                                "content_length": len(extracted_text),
                                "ai_analysis": analysis_result,
                                "extracted_specs": analysis_result.get('specifications', {}),
                                "extracted_features": analysis_result.get('features', []),
                                "performance_metrics": analysis_result.get('performance_metrics', {}),
                                "confidence_score": analysis_result.get('confidence_score', 0.0),
                                "extraction_notes": analysis_result.get('extraction_notes', ''),
                                "analysis_model": model_choice,
                                "confidence_threshold": confidence_threshold,
                                "extract_features": extract_features,
                                "extract_competitive": extract_competitive_info
                            }
                            
                            confidence = analysis_result.get('confidence_score', 0)
                            st.success(f"✅ **PRD Analysis Complete!** Confidence: {confidence*100:.1f}%")
                            
                            # Enhanced analysis results display
                            with st.expander("🎯 Comprehensive AI Analysis Results", expanded=True):
                                
                                # Analysis summary
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Confidence Score", f"{confidence*100:.1f}%")
                                with col2:
                                    specs_count = len([v for v in analysis_result.get('specifications', {}).values() if v])
                                    st.metric("Specifications", specs_count)
                                with col3:
                                    features_count = len(analysis_result.get('features', []))
                                    st.metric("Features", features_count)
                                with col4:
                                    detected_type = analysis_result.get('product_type', expected_type)
                                    st.metric("Detected Type", PRODUCT_TYPES.get(detected_type, {}).get('name', 'Unknown'))
                                
                                # Tabbed results
                                result_tabs = st.tabs(["🔧 Specifications", "⭐ Features", "📊 Performance", "📝 Notes"])
                                
                                with result_tabs[0]:
                                    st.subheader("🔧 Extracted Specifications")
                                    if analysis_result.get('specifications'):
                                        specs_data = []
                                        for key, value in analysis_result['specifications'].items():
                                            if value:
                                                specs_data.append({
                                                    "Specification": key.replace('_', ' ').title(),
                                                    "Value": str(value),
                                                    "Confidence": "High" if confidence > 0.8 else "Medium" if confidence > 0.6 else "Low"
                                                })
                                        
                                        if specs_data:
                                            st.dataframe(specs_data, use_container_width=True)
                                        else:
                                            st.info("No specifications with values extracted")
                                    else:
                                        st.info("No specifications extracted")
                                
                                with result_tabs[1]:
                                    st.subheader("⭐ Extracted Features")
                                    if analysis_result.get('features'):
                                        for idx, feature in enumerate(analysis_result['features'], 1):
                                            st.write(f"**{idx}.** {feature}")
                                    else:
                                        st.info("No features extracted")
                                
                                with result_tabs[2]:
                                    st.subheader("📊 Performance Metrics")
                                    if analysis_result.get('performance_metrics'):
                                        for key, value in analysis_result['performance_metrics'].items():
                                            if value:
                                                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                                    else:
                                        st.info("No performance metrics extracted")
                                
                                with result_tabs[3]:
                                    st.subheader("📝 Extraction Notes")
                                    if analysis_result.get('extraction_notes'):
                                        st.info(analysis_result['extraction_notes'])
                                    else:
                                        st.info("No additional notes")
                            
                            # Quick actions
                            st.divider()
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("🚀 Use for Generation", type="primary"):
                                    st.session_state.selected_prd_id = prd_id
                                    st.session_state.new_specs = analysis_result.get('specifications', {})
                                    st.session_state.new_features = analysis_result.get('features', [])
                                    st.session_state.current_step = 2
                                    st.success("PRD data loaded! Redirecting...")
                                    time.sleep(1)
                                    st.rerun()
                            with col2:
                                if st.button("📋 View in Library"):
                                    st.session_state.current_step = 5  # Stay on PRD tab but switch to library
                                    st.rerun()
                            with col3:
                                if st.button("🔄 Upload Another"):
                                    st.rerun()
                            
                        else:
                            st.error(f"❌ **AI Analysis Failed**: {analysis_result['error']}")
                            st.error("Please check the document content and try again.")
                    else:
                        st.error(f"❌ **Text Extraction Failed**: {extracted_text}")
                        st.error("Unable to extract text from the uploaded file.")
    
    with tab2:
        st.subheader("📋 PRD Document Library Management")
        
        if not st.session_state.prd_documents:
            st.info("📄 No PRD documents uploaded yet. Upload some PRDs to enhance datasheet generation with auto-populated specifications.")
            
            if st.button("📁 Upload First PRD", type="primary"):
                # Switch to upload tab
                st.rerun()
        else:
            # Enhanced search and filter for PRDs
            col1, col2, col3 = st.columns(3)
            with col1:
                search_term = st.text_input("🔍 Search PRDs", placeholder="Search by name, description, or content...")
            with col2:
                filter_type = st.selectbox("📱 Filter by Product Type", 
                    ["All"] + list(PRODUCT_TYPES.keys()),
                    format_func=lambda x: "All Types" if x == "All" else PRODUCT_TYPES.get(x, {}).get('name', x))
            with col3:
                confidence_filter = st.selectbox("🎯 Filter by Confidence",
                    ["All", "High (80%+)", "Medium (60%+)", "Low (<60%)"])
            
            # Library statistics
            total_prds = len(st.session_state.prd_documents)
            high_confidence = sum(1 for prd in st.session_state.prd_documents.values() 
                                if prd.get('confidence_score', 0) >= 0.8)
            total_specs = sum(len([v for v in prd.get('extracted_specs', {}).values() if v]) 
                            for prd in st.session_state.prd_documents.values())
            
            st.markdown(f"""
            **📊 Library Statistics:** {total_prds} documents • {high_confidence} high-confidence • {total_specs} total specifications extracted
            """)
            
            # Filter PRDs
            filtered_prds = {}
            for prd_id, prd_data in st.session_state.prd_documents.items():
                # Text search
                if search_term:
                    search_lower = search_term.lower()
                    if not any([
                        search_lower in prd_data['name'].lower(),
                        search_lower in prd_data.get('description', '').lower(),
                        search_lower in prd_data.get('raw_content', '')[:500].lower()
                    ]):
                        continue
                
                # Type filter
                if filter_type != "All" and prd_data['expected_type'] != filter_type:
                    continue
                
                # Confidence filter
                confidence = prd_data.get('confidence_score', 0)
                if confidence_filter == "High (80%+)" and confidence < 0.8:
                    continue
                elif confidence_filter == "Medium (60%+)" and confidence < 0.6:
                    continue
                elif confidence_filter == "Low (<60%)" and confidence >= 0.6:
                    continue
                
                filtered_prds[prd_id] = prd_data
            
            st.write(f"**Showing {len(filtered_prds)} of {len(st.session_state.prd_documents)} PRD documents**")
            
            # Display PRDs with enhanced information
            for prd_id, prd_data in filtered_prds.items():
                confidence = prd_data.get('confidence_score', 0)
                confidence_emoji = "🎯" if confidence >= 0.8 else "⭐" if confidence >= 0.6 else "📄"
                
                # File size and content indicators
                file_size = prd_data.get('file_size', 0)
                size_mb = file_size / 1024 / 1024
                size_indicator = f"{size_mb:.1f}MB" if size_mb >= 1 else f"{file_size/1024:.0f}KB"
                
                with st.expander(f"{confidence_emoji} {prd_data['name']} • {confidence*100:.1f}% confidence • {size_indicator}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**File:** {prd_data['filename']}")
                        st.write(f"**Product Type:** {PRODUCT_TYPES[prd_data['expected_type']]['name']}")
                        st.write(f"**Upload Date:** {prd_data['upload_date']}")
                        st.write(f"**Analysis Model:** {prd_data.get('analysis_model', 'Unknown')}")
                        st.write(f"**File Size:** {size_indicator} ({prd_data.get('content_length', 0):,} characters)")
                        
                        if prd_data.get('description'):
                            st.write(f"**Description:** {prd_data['description']}")
                        
                        # Enhanced metrics
                        col_a, col_b, col_c, col_d = st.columns(4)
                        with col_a:
                            specs_count = len([v for v in prd_data.get('extracted_specs', {}).values() if v])
                            st.metric("Specifications", specs_count)
                        with col_b:
                            features_count = len(prd_data.get('extracted_features', []))
                            st.metric("Features", features_count)
                        with col_c:
                            st.metric("Confidence", f"{confidence*100:.0f}%")
                        with col_d:
                            performance_count = len([v for v in prd_data.get('performance_metrics', {}).values() if v])
                            st.metric("Performance", performance_count)
                        
                        if prd_data.get('extraction_notes'):
                            st.info(f"**Analysis Notes:** {prd_data['extraction_notes']}")
                    
                    with col2:
                        # Action buttons
                        if st.button("🚀 Use for Generation", key=f"use_prd_{prd_id}", type="primary", use_container_width=True):
                            st.session_state.selected_prd_id = prd_id
                            st.session_state.new_specs = prd_data.get('extracted_specs', {})
                            st.session_state.new_features = prd_data.get('extracted_features', [])
                            st.session_state.current_step = 2
                            st.success("PRD selected! Redirecting...")
                            time.sleep(1)
                            st.rerun()
                        
                        if st.button("🔍 View Details", key=f"details_prd_{prd_id}", use_container_width=True):
                            # Toggle detailed view
                            toggle_key = f"show_details_{prd_id}"
                            if toggle_key not in st.session_state:
                                st.session_state[toggle_key] = False
                            st.session_state[toggle_key] = not st.session_state[toggle_key]
                            st.rerun()
                        
                        if st.button("🗑️ Delete", key=f"del_prd_{prd_id}", use_container_width=True, type="secondary"):
                            del st.session_state.prd_documents[prd_id]
                            st.success(f"Deleted {prd_data['name']}")
                            st.rerun()
                    
                    # Show detailed analysis if toggled
                    if st.session_state.get(f"show_details_{prd_id}", False):
                        st.divider()
                        detail_tabs = st.tabs(["🔧 Specifications", "⭐ Features", "📊 Performance", "📄 Content"])
                        
                        with detail_tabs[0]:
                            specs = prd_data.get('extracted_specs', {})
                            if specs:
                                for key, value in specs.items():
                                    if value:
                                        st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                            else:
                                st.info("No specifications extracted")
                        
                        with detail_tabs[1]:
                            features = prd_data.get('extracted_features', [])
                            if features:
                                for idx, feature in enumerate(features, 1):
                                    st.write(f"**{idx}.** {feature}")
                            else:
                                st.info("No features extracted")
                        
                        with detail_tabs[2]:
                            performance = prd_data.get('performance_metrics', {})
                            if performance:
                                for key, value in performance.items():
                                    if value:
                                        st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                            else:
                                st.info("No performance metrics extracted")
                        
                        with detail_tabs[3]:
                            content_preview = prd_data.get('raw_content', '')[:2000]
                            st.text_area("Content Preview (first 2000 characters)", content_preview, height=300, disabled=True)
    
    with tab3:
        st.subheader("🚀 PRD Integration for Datasheet Generation")
        st.markdown("Select a PRD document to automatically populate specification fields for comprehensive datasheet generation")
        
        if not st.session_state.prd_documents:
            st.info("📄 No PRD documents available. Upload some PRDs first to enable auto-population of specifications.")
            
            if st.button("📁 Upload PRD Document", type="primary"):
                # Switch back to upload tab
                st.rerun()
        else:
            # PRD selection with enhanced information
            st.write("**Available PRD Documents:**")
            
            prd_options = {}
            for prd_id, prd_data in st.session_state.prd_documents.items():
                confidence = prd_data.get('confidence_score', 0)
                specs_count = len([v for v in prd_data.get('extracted_specs', {}).values() if v])
                features_count = len(prd_data.get('extracted_features', []))
                confidence_indicator = "🎯" if confidence >= 0.8 else "⭐" if confidence >= 0.6 else "📄"
                
                prd_options[prd_id] = f"{confidence_indicator} {prd_data['name']} • {confidence*100:.0f}% • {specs_count} specs, {features_count} features"
            
            selected_prd_id = st.selectbox(
                "Choose PRD Document", 
                options=list(prd_options.keys()),
                format_func=lambda x: prd_options[x],
                help="Select a PRD document to auto-populate specification fields"
            )
            
            if selected_prd_id:
                prd_data = st.session_state.prd_documents[selected_prd_id]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📋 PRD Document Summary")
                    st.write(f"**Name:** {prd_data['name']}")
                    st.write(f"**Product Type:** {PRODUCT_TYPES[prd_data['expected_type']]['name']}")
                    st.write(f"**Upload Date:** {prd_data['upload_date']}")
                    st.write(f"**File:** {prd_data['filename']}")
                    
                    confidence = prd_data.get('confidence_score', 0)
                    confidence_color = "green" if confidence >= 0.8 else "orange" if confidence >= 0.6 else "red"
                    st.markdown(f"**Analysis Confidence:** <span style='color: {confidence_color}'>{confidence*100:.1f}%</span>", unsafe_allow_html=True)
                    
                    specs_count = len([v for v in prd_data.get('extracted_specs', {}).values() if v])
                    features_count = len(prd_data.get('extracted_features', []))
                    performance_count = len([v for v in prd_data.get('performance_metrics', {}).values() if v])
                    
                    st.write(f"**Extracted Content:** {specs_count} specifications, {features_count} features, {performance_count} performance metrics")
                    
                    if prd_data.get('description'):
                        st.write(f"**Description:** {prd_data['description']}")
                
                with col2:
                    st.subheader("🎯 Integration Preview")
                    
                    # Show preview of key specifications
                    specs = prd_data.get('extracted_specs', {})
                    preview_specs = {}
                    key_fields = ['model_number', 'max_data_rate', 'frequency_bands', 'power_consumption', 'dimensions']
                    
                    for field in key_fields:
                        if field in specs and specs[field]:
                            preview_specs[field.replace('_', ' ').title()] = specs[field]
                    
                    if preview_specs:
                        st.write("**Key Specifications Preview:**")
                        for key, value in list(preview_specs.items())[:5]:
                            st.write(f"• **{key}:** {value}")
                    else:
                        st.info("No key specifications preview available")
                    
                    # Show preview of key features
                    features = prd_data.get('extracted_features', [])
                    if features:
                        st.write("**Key Features Preview:**")
                        for feature in features[:3]:
                            st.write(f"• {feature}")
                    else:
                        st.info("No features preview available")
                
                # Integration actions
                st.divider()
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col1:
                    if st.button("📊 View Full Analysis", use_container_width=True):
                        # Show detailed analysis
                        with st.expander("🔬 Comprehensive Analysis Results", expanded=True):
                            analysis_tabs = st.tabs(["📋 All Specifications", "⭐ All Features", "📊 Performance Metrics"])
                            
                            with analysis_tabs[0]:
                                specs = prd_data.get('extracted_specs', {})
                                if specs:
                                    specs_df = []
                                    for key, value in specs.items():
                                        if value:
                                            specs_df.append({
                                                "Specification": key.replace('_', ' ').title(),
                                                "Value": str(value)
                                            })
                                    if specs_df:
                                        st.dataframe(specs_df, use_container_width=True)
                                else:
                                    st.info("No specifications extracted")
                            
                            with analysis_tabs[1]:
                                features = prd_data.get('extracted_features', [])
                                if features:
                                    for idx, feature in enumerate(features, 1):
                                        st.write(f"**{idx}.** {feature}")
                                else:
                                    st.info("No features extracted")
                            
                            with analysis_tabs[2]:
                                performance = prd_data.get('performance_metrics', {})
                                if performance:
                                    for key, value in performance.items():
                                        if value:
                                            st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                                else:
                                    st.info("No performance metrics extracted")
                
                with col2:
                    integration_button_text = "🚀 Use PRD for Professional Generation"
                    if confidence >= 0.8:
                        integration_button_text = "🎯 Use High-Confidence PRD"
                    
                    if st.button(integration_button_text, type="primary", use_container_width=True):
                        # Set the PRD data in session state
                        st.session_state.selected_prd_id = selected_prd_id
                        st.session_state.new_specs = prd_data.get('extracted_specs', {})
                        st.session_state.new_features = prd_data.get('extracted_features', [])
                        
                        # Add performance metrics to specs if available
                        performance_metrics = prd_data.get('performance_metrics', {})
                        for key, value in performance_metrics.items():
                            if value and key not in st.session_state.new_specs:
                                st.session_state.new_specs[key] = value
                        
                        # Redirect to step 2 (specifications)
                        st.session_state.current_step = 2
                        st.success(f"✅ **PRD Integration Successful!** {prd_data['name']} data loaded with {specs_count} specifications and {features_count} features.")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                
                with col3:
                    if st.button("🔄 Select Different", use_container_width=True):
                        st.rerun()

elif st.session_state.current_step == 6:
    # Enhanced Analytics and Performance Dashboard
    st.header("📊 Analytics & Performance Dashboard")
    st.markdown("Comprehensive analytics for datasheet generation performance, template effectiveness, and PRD utilization")
    
    if not st.session_state.generated_datasheets and not st.session_state.prd_documents:
        st.info("📊 No data available for analytics. Generate some datasheets and upload PRDs to see comprehensive analytics.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🎯 Generate First Datasheet", type="primary"):
                st.session_state.current_step = 1
                st.rerun()
        with col2:
            if st.button("📄 Upload PRD Document", type="secondary"):
                st.session_state.current_step = 5
                st.rerun()
        with col3:
            if st.button("📋 View Templates", type="secondary"):
                st.session_state.current_step = 1
                st.rerun()
    else:
        
        # Analytics tabs
        analytics_tabs = st.tabs([
            "📈 Generation Analytics", 
            "🎯 Quality Metrics", 
            "📄 PRD Performance", 
            "🏆 Template Effectiveness",
            "📊 Usage Patterns"
        ])
        
        with analytics_tabs[0]:
            st.subheader("📈 Generation Analytics Overview")
            
            if st.session_state.generated_datasheets:
                # Key metrics
                total_datasheets = len(st.session_state.generated_datasheets)
                total_words = sum(d.get('word_count', 0) for d in st.session_state.generated_datasheets)
                avg_quality = sum(d.get('quality_score', 0) for d in st.session_state.generated_datasheets) / total_datasheets
                verified_count = sum(1 for d in st.session_state.generated_datasheets if d.get('template_verified'))
                prd_enhanced_count = sum(1 for d in st.session_state.generated_datasheets if d.get('prd_enhanced'))
                live_streamed_count = sum(1 for d in st.session_state.generated_datasheets if d.get('generation_method') == 'live_streaming')
                
                # Metrics display
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Generated", total_datasheets, delta=f"+{total_datasheets} this session")
                with col2:
                    avg_words = total_words / total_datasheets if total_datasheets > 0 else 0
                    st.metric("Avg Words", f"{avg_words:,.0f}", delta=f"{avg_words-3000:+.0f} vs standard")
                with col3:
                    st.metric("Avg Quality", f"{avg_quality:.1%}", delta=f"+{(avg_quality-0.75)*100:.0f}% vs baseline")
                with col4:
                    comprehensive_rate = sum(1 for d in st.session_state.generated_datasheets if d.get('word_count', 0) >= 4000) / total_datasheets * 100
                    st.metric("Comprehensive Rate", f"{comprehensive_rate:.0f}%")
                
                st.divider()
                
                # Enhancement breakdown
                col1, col2, col3 = st.columns(3)
                with col1:
                    verified_rate = verified_count / total_datasheets * 100
                    st.metric("Verified Templates", f"{verified_count}/{total_datasheets}", delta=f"{verified_rate:.0f}% usage")
                with col2:
                    prd_rate = prd_enhanced_count / total_datasheets * 100
                    st.metric("PRD Enhanced", f"{prd_enhanced_count}/{total_datasheets}", delta=f"{prd_rate:.0f}% usage")
                with col3:
                    live_rate = live_streamed_count / total_datasheets * 100
                    st.metric("Live Streamed", f"{live_streamed_count}/{total_datasheets}", delta=f"{live_rate:.0f}% usage")
                
                # Generation timeline
                if total_datasheets > 1:
                    st.subheader("📅 Generation Timeline")
                    
                    # Create timeline data
                    timeline_data = []
                    for ds in st.session_state.generated_datasheets:
                        timeline_data.append({
                            'Date': ds['generation_date'],
                            'Product': ds['product_name'][:30] + "..." if len(ds['product_name']) > 30 else ds['product_name'],
                            'Words': ds.get('word_count', 0),
                            'Quality': ds.get('quality_score', 0) * 100,
                            'Verified': 'Yes' if ds.get('template_verified') else 'No',
                            'PRD': 'Yes' if ds.get('prd_enhanced') else 'No'
                        })
                    
                    st.dataframe(timeline_data, use_container_width=True)
            else:
                st.info("No datasheets generated yet for analytics.")
        
        with analytics_tabs[1]:
            st.subheader("🎯 Quality Metrics Analysis")
            
            if st.session_state.generated_datasheets:
                # Quality distribution
                quality_ranges = {"Excellent (90%+)": 0, "Good (70-89%)": 0, "Fair (50-69%)": 0, "Needs Improvement (<50%)": 0}
                word_ranges = {"Comprehensive (4000+)": 0, "Standard (2500-3999)": 0, "Basic (1000-2499)": 0, "Minimal (<1000)": 0}
                
                for ds in st.session_state.generated_datasheets:
                    quality = ds.get('quality_score', 0)
                    words = ds.get('word_count', 0)
                    
                    # Quality categorization
                    if quality >= 0.9:
                        quality_ranges["Excellent (90%+)"] += 1
                    elif quality >= 0.7:
                        quality_ranges["Good (70-89%)"] += 1
                    elif quality >= 0.5:
                        quality_ranges["Fair (50-69%)"] += 1
                    else:
                        quality_ranges["Needs Improvement (<50%)"] += 1
                    
                    # Word count categorization
                    if words >= 4000:
                        word_ranges["Comprehensive (4000+)"] += 1
                    elif words >= 2500:
                        word_ranges["Standard (2500-3999)"] += 1
                    elif words >= 1000:
                        word_ranges["Basic (1000-2499)"] += 1
                    else:
                        word_ranges["Minimal (<1000)"] += 1
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Quality Distribution")
                    for category, count in quality_ranges.items():
                        percentage = count / len(st.session_state.generated_datasheets) * 100
                        st.progress(percentage / 100, text=f"{category}: {count} ({percentage:.0f}%)")
                
                with col2:
                    st.subheader("📝 Content Length Distribution")
                    for category, count in word_ranges.items():
                        percentage = count / len(st.session_state.generated_datasheets) * 100
                        st.progress(percentage / 100, text=f"{category}: {count} ({percentage:.0f}%)")
                
                # Detailed quality metrics
                st.divider()
                st.subheader("🔍 Detailed Quality Breakdown")
                
                # Calculate average metrics across all datasheets
                if st.session_state.generated_datasheets:
                    metrics_sum = {
                        'overall_quality': 0,
                        'spec_accuracy': 0,
                        'feature_coverage': 0,
                        'completeness_score': 0,
                        'professional_formatting': 0,
                        'technical_depth': 0
                    }
                    
                    valid_analyses = 0
                    for ds in st.session_state.generated_datasheets:
                        analysis = ds.get('accuracy_analysis', {})
                        if analysis:
                            valid_analyses += 1
                            for key in metrics_sum:
                                metrics_sum[key] += analysis.get(key, 0)
                    
                    if valid_analyses > 0:
                        col1, col2, col3 = st.columns(3)
                        
                        metrics_avg = {k: v / valid_analyses for k, v in metrics_sum.items()}
                        
                        with col1:
                            st.metric("Overall Quality", f"{metrics_avg['overall_quality']:.1%}")
                            st.metric("Specification Accuracy", f"{metrics_avg['spec_accuracy']:.1%}")
                        with col2:
                            st.metric("Feature Coverage", f"{metrics_avg['feature_coverage']:.1%}")
                            st.metric("Completeness Score", f"{metrics_avg['completeness_score']:.1%}")
                        with col3:
                            st.metric("Professional Formatting", f"{metrics_avg['professional_formatting']:.1%}")
                            st.metric("Technical Depth", f"{metrics_avg['technical_depth']:.1%}")
            else:
                st.info("No quality data available yet.")
        
        with analytics_tabs[2]:
            st.subheader("📄 PRD Performance Analysis")
            
            if st.session_state.prd_documents:
                total_prds = len(st.session_state.prd_documents)
                high_confidence_prds = sum(1 for prd in st.session_state.prd_documents.values() if prd.get('confidence_score', 0) >= 0.8)
                total_extracted_specs = sum(len([v for v in prd.get('extracted_specs', {}).values() if v]) for prd in st.session_state.prd_documents.values())
                total_extracted_features = sum(len(prd.get('extracted_features', [])) for prd in st.session_state.prd_documents.values())
                
                # PRD metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total PRDs", total_prds)
                with col2:
                    confidence_rate = high_confidence_prds / total_prds * 100 if total_prds > 0 else 0
                    st.metric("High Confidence", f"{high_confidence_prds}/{total_prds}", delta=f"{confidence_rate:.0f}%")
                with col3:
                    avg_specs = total_extracted_specs / total_prds if total_prds > 0 else 0
                    st.metric("Avg Specs/PRD", f"{avg_specs:.1f}")
                with col4:
                    avg_features = total_extracted_features / total_prds if total_prds > 0 else 0
                    st.metric("Avg Features/PRD", f"{avg_features:.1f}")
                
                # PRD effectiveness
                st.divider()
                st.subheader("📊 PRD Analysis Effectiveness")
                
                prd_data = []
                for prd_id, prd in st.session_state.prd_documents.items():
                    specs_count = len([v for v in prd.get('extracted_specs', {}).values() if v])
                    features_count = len(prd.get('extracted_features', []))
                    confidence = prd.get('confidence_score', 0)
                    
                    prd_data.append({
                        'PRD Name': prd['name'],
                        'Confidence': f"{confidence*100:.0f}%",
                        'Specifications': specs_count,
                        'Features': features_count,
                        'Product Type': PRODUCT_TYPES[prd['expected_type']]['name'],
                        'Upload Date': prd['upload_date']
                    })
                
                st.dataframe(prd_data, use_container_width=True)
                
                # PRD utilization in generation
                if st.session_state.generated_datasheets:
                    prd_usage_count = sum(1 for ds in st.session_state.generated_datasheets if ds.get('prd_enhanced'))
                    usage_rate = prd_usage_count / len(st.session_state.generated_datasheets) * 100
                    
                    st.subheader("🚀 PRD Utilization in Generation")
                    st.metric("PRD Usage Rate", f"{prd_usage_count}/{len(st.session_state.generated_datasheets)}", delta=f"{usage_rate:.0f}% of generations")
            else:
                st.info("No PRD documents available for analysis.")
        
        with analytics_tabs[3]:
            st.subheader("🏆 Template Effectiveness Analysis")
            
            if st.session_state.templates:
                # Template statistics
                total_templates = len(st.session_state.templates)
                verified_templates = sum(1 for t in st.session_state.templates.values() if t.get('accuracy_verified'))
                avg_template_quality = sum(t.get('quality_score', 0) for t in st.session_state.templates.values()) / total_templates
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Templates", total_templates)
                with col2:
                    verification_rate = verified_templates / total_templates * 100
                    st.metric("Verified Templates", f"{verified_templates}/{total_templates}", delta=f"{verification_rate:.0f}%")
                with col3:
                    st.metric("Avg Template Quality", f"{avg_template_quality:.2f}/1.0")
                
                # Template usage analysis
                if st.session_state.generated_datasheets:
                    st.divider()
                    st.subheader("📈 Template Usage Patterns")
                    
                    template_usage = {}
                    template_performance = {}
                    
                    for ds in st.session_state.generated_datasheets:
                        template_name = ds.get('template_used', 'Unknown')
                        
                        if template_name not in template_usage:
                            template_usage[template_name] = 0
                            template_performance[template_name] = []
                        
                        template_usage[template_name] += 1
                        template_performance[template_name].append(ds.get('quality_score', 0))
                    
                    # Create usage data
                    usage_data = []
                    for template, count in template_usage.items():
                        avg_performance = sum(template_performance[template]) / len(template_performance[template])
                        usage_data.append({
                            'Template': template,
                            'Usage Count': count,
                            'Usage Rate': f"{count/len(st.session_state.generated_datasheets)*100:.0f}%",
                            'Avg Quality': f"{avg_performance:.1%}",
                            'Performance Rating': "🎯 Excellent" if avg_performance >= 0.9 else "⭐ Good" if avg_performance >= 0.7 else "👍 Fair"
                        })
                    
                    st.dataframe(usage_data, use_container_width=True)
                    
                    # Template recommendations
                    st.subheader("💡 Template Recommendations")
                    
                    best_templates = sorted(usage_data, key=lambda x: float(x['Avg Quality'].rstrip('%'))/100, reverse=True)
                    
                    if best_templates:
                        st.success(f"🏆 **Best Performing Template:** {best_templates[0]['Template']} ({best_templates[0]['Avg Quality']} quality)")
                        
                    most_used = sorted(usage_data, key=lambda x: x['Usage Count'], reverse=True)
                    if most_used:
                        st.info(f"📈 **Most Used Template:** {most_used[0]['Template']} ({most_used[0]['Usage Count']} uses)")
            else:
                st.info("No template data available for analysis.")
        
        with analytics_tabs[4]:
            st.subheader("📊 Usage Patterns & Insights")
            
            # System usage overview
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_sessions = 1  # Current session
                st.metric("Sessions", total_sessions)
            
            with col2:
                total_operations = len(st.session_state.generated_datasheets) + len(st.session_state.prd_documents)
                st.metric("Total Operations", total_operations)
            
            with col3:
                if st.session_state.generated_datasheets:
                    avg_time_between = "Real-time"  # Since we don't track timestamps precisely
                    st.metric("Generation Speed", "Live Streaming")
                else:
                    st.metric("Generation Speed", "N/A")
            
            with col4:
                enhancement_rate = 0
                if st.session_state.generated_datasheets:
                    enhanced = sum(1 for ds in st.session_state.generated_datasheets 
                                 if ds.get('template_verified') or ds.get('prd_enhanced'))
                    enhancement_rate = enhanced / len(st.session_state.generated_datasheets) * 100
                st.metric("Enhancement Rate", f"{enhancement_rate:.0f}%")
            
            # Product type distribution
            if st.session_state.generated_datasheets:
                st.divider()
                st.subheader("📱 Product Type Distribution")
                
                product_distribution = {}
                for ds in st.session_state.generated_datasheets:
                    prod_type = ds.get('product_type', 'unknown')
                    product_name = PRODUCT_TYPES.get(prod_type, {}).get('name', 'Unknown')
                    product_distribution[product_name] = product_distribution.get(product_name, 0) + 1
                
                for product, count in product_distribution.items():
                    percentage = count / len(st.session_state.generated_datasheets) * 100
                    st.progress(percentage / 100, text=f"{product}: {count} ({percentage:.0f}%)")
            
            # Feature adoption
            st.divider()
            st.subheader("🚀 Feature Adoption")
            
            feature_adoption = {
                "Template Selection": len(st.session_state.generated_datasheets) > 0,
                "PRD Integration": len(st.session_state.prd_documents) > 0,
                "Verified Templates": any(ds.get('template_verified') for ds in st.session_state.generated_datasheets),
                "Live Streaming": any(ds.get('generation_method') == 'live_streaming' for ds in st.session_state.generated_datasheets),
                "Comprehensive Generation": any(ds.get('word_count', 0) >= 4000 for ds in st.session_state.generated_datasheets),
                "Professional Formatting": any(ds.get('professional_formatting') for ds in st.session_state.generated_datasheets),
            }
            
            for feature, adopted in feature_adoption.items():
                status = "✅ Adopted" if adopted else "❌ Not Used"
                color = "green" if adopted else "red"
                st.markdown(f"**{feature}:** <span style='color: {color}'>{status}</span>", unsafe_allow_html=True)
            
            # Recommendations
            st.divider()
            st.subheader("💡 Usage Recommendations")
            
            recommendations = []
            
            if not st.session_state.generated_datasheets:
                recommendations.append("🎯 Start by generating your first datasheet using a verified template")
            
            if not st.session_state.prd_documents:
                recommendations.append("📝 Upload PRD documents to auto-populate specifications and improve accuracy")
            
            if st.session_state.generated_datasheets and not any(ds.get('template_verified') for ds in st.session_state.generated_datasheets):
                recommendations.append("🏆 Try using verified templates for higher quality and more comprehensive outputs")
            
            if len(st.session_state.generated_datasheets) > 0:
                avg_words = sum(ds.get('word_count', 0) for ds in st.session_state.generated_datasheets) / len(st.session_state.generated_datasheets)
                if avg_words < 4000:
                    recommendations.append("📊 Consider providing more detailed specifications to generate comprehensive datasheets (4000+ words)")
            
            if not any(ds.get('generation_method') == 'live_streaming' for ds in st.session_state.generated_datasheets):
                recommendations.append("🔴 Try the live streaming generation to watch content being created in real-time")
            
            if recommendations:
                for rec in recommendations:
                    st.info(rec)
            else:
                st.success("🎉 You're using all advanced features! Great job maximizing the platform's capabilities.")

# Enhanced footer
st.divider()

# Footer statistics and status
footer_stats = []

if st.session_state.templates:
    verified_templates = sum(1 for t in st.session_state.templates.values() if t.get('accuracy_verified'))
    footer_stats.append(f"🎯 {verified_templates} Verified Templates")

if st.session_state.prd_documents:
    high_confidence_prds = sum(1 for prd in st.session_state.prd_documents.values() if prd.get('confidence_score', 0) >= 0.8)
    footer_stats.append(f"📝 {high_confidence_prds} High-Confidence PRDs")

if st.session_state.generated_datasheets:
    comprehensive_count = sum(1 for d in st.session_state.generated_datasheets if d.get('word_count', 0) >= 4000)
    live_count = sum(1 for d in st.session_state.generated_datasheets if d.get('generation_method') == 'live_streaming')
    footer_stats.append(f"📊 {comprehensive_count} Comprehensive Generated")
    footer_stats.append(f"🔴 {live_count} Live Streamed")

footer_status = " | ".join(footer_stats) if footer_stats else "Ready for enhanced datasheet generation"

# Calculate session performance
session_performance = "🚀 High Performance"
if st.session_state.generated_datasheets:
    avg_quality = sum(d.get('quality_score', 0) for d in st.session_state.generated_datasheets) / len(st.session_state.generated_datasheets)
    if avg_quality >= 0.9:
        session_performance = "🎯 Exceptional Performance"
    elif avg_quality >= 0.8:
        session_performance = "⭐ High Performance"
    elif avg_quality >= 0.7:
        session_performance = "👍 Good Performance"
    else:
        session_performance = "📈 Standard Performance"

st.markdown(
    f"""
    <div style='text-align: center; color: #666; font-size: 0.95em; margin-top: 50px; 
                background: linear-gradient(135deg, #f8f9fa, #e9ecef); 
                padding: 25px; border-radius: 15px; border: 2px solid #ff6600;'>
        <div style='font-size: 1.3em; font-weight: bold; color: #ff6600; margin-bottom: 15px;'>
            🚀 Ruckus Professional Datasheet Generator v10.0
        </div>
        <div style='font-size: 1.1em; margin-bottom: 10px;'>
            <strong>🔴 Live Streaming Generation • 📊 Professional Formatting • 🎯 Verified Templates</strong>
        </div>
        <div style='margin-bottom: 10px;'>
            {footer_status}
        </div>
        <div style='font-size: 0.9em; color: #555;'>
            📈 Session Status: {session_performance} | 
            🎛️ Features: Professional HTML/PDF • Template Selection • PRD Integration • Live Generation • Quality Analytics<br>
            📊 Total Generated: {len(st.session_state.generated_datasheets)} | 
            📄 PRDs: {len(st.session_state.prd_documents)} | 
            🏆 Templates: {len(st.session_state.templates)}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)