import streamlit as st
import json
from openai import OpenAI
from datetime import datetime
import re
from typing import Dict, List, Tuple, Optional
import time

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
        elif any(kw in line_lower for kw in ['features', 'benefits', 'highlights']) and len(line_lower) < 50:
            current_section = 'features'
            is_section_header = True
        elif any(kw in line_lower for kw in ['specifications', 'technical specs', 'specs']) and len(line_lower) < 50:
            current_section = 'specifications'
            is_section_header = True
        elif any(kw in line_lower for kw in ['ordering', 'model', 'part number']) and len(line_lower) < 50:
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

def generate_datasheet_with_llm(template: Dict, specs: Dict, features: List[str], api_key: str, model: str = "gpt-3.5-turbo") -> str:
    """Generate new datasheet using OpenAI API with better error handling"""
    try:
        client = OpenAI(api_key=api_key)
    except Exception as e:
        st.error(f"Invalid API key: {str(e)}")
        return None
    
    # Build the prompt
    prompt = f"""You are a technical writer for Ruckus Networks. Create a professional datasheet for a new product based on the template and specifications provided.

TEMPLATE INFORMATION:
Product Type: {PRODUCT_TYPES[template['product_type']]['name']}
Template Overview: {template['sections']['overview'][:500]}...

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
        st.error(f"Error generating datasheet: {str(e)}")
        return None

def export_library() -> str:
    """Export the entire library as JSON"""
    export_data = {
        "version": "1.0",
        "export_date": datetime.now().isoformat(),
        "templates": st.session_state.templates,
        "generated_datasheets": st.session_state.generated_datasheets
    }
    return json.dumps(export_data, indent=2)

def import_library(file_content: str) -> bool:
    """Import library from JSON"""
    try:
        data = json.loads(file_content)
        st.session_state.templates = data.get("templates", {})
        st.session_state.generated_datasheets = data.get("generated_datasheets", [])
        return True
    except Exception as e:
        st.error(f"Error importing library: {str(e)}")
        return False

# Main UI
st.title("📊 Ruckus Datasheet Generator")
st.markdown("Generate professional datasheets for new Ruckus products using AI")

# Top navigation bar
col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
with col2:
    if st.button("📋 Library", type="secondary" if st.session_state.current_step != 4 else "primary"):
        st.session_state.current_step = 4
        st.rerun()
with col3:
    if st.button("🏠 Home", type="secondary" if st.session_state.current_step == 4 else "primary"):
        st.session_state.current_step = 1
        st.rerun()

# Sidebar
with st.sidebar:
    st.title("⚙️ Configuration")
    
    api_key = st.text_input("OpenAI API Key", type="password", help="Enter your OpenAI API key")
    
    if api_key:
        st.success("API key configured ✓")
        
        # Model selection
        model_choice = st.selectbox(
            "AI Model",
            ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
            index=0,
            help="GPT-3.5 is faster and cheaper, GPT-4 is more capable"
        )
    else:
        st.warning("Please enter your OpenAI API key to generate datasheets")
        model_choice = "gpt-3.5-turbo"
    
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
        for template in st.session_state.templates.values():
            ptype = template['product_type']
            type_counts[ptype] = type_counts.get(ptype, 0) + 1
        
        for ptype, count in type_counts.items():
            st.write(f"• {PRODUCT_TYPES.get(ptype, {}).get('name', ptype)}: {count}")
    
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
if st.session_state.current_step != 4:
    # Step indicator
    steps = ["Upload Template", "Enter Specifications", "Generate Datasheet"]
    cols = st.columns(len(steps))
    for idx, (col, step) in enumerate(zip(cols, steps)):
        with col:
            if idx + 1 <= st.session_state.current_step:
                st.info(f"**Step {idx + 1}: {step}**")
            else:
                st.text(f"Step {idx + 1}: {step}")
    
    st.divider()

# Step 1: Upload Template
if st.session_state.current_step == 1:
    st.header("Step 1: Select Template Datasheet")
    
    # Create tabs for upload and selection
    tab1, tab2 = st.tabs(["📤 Upload New Templates", "📚 Select from Library"])
    
    with tab1:
        st.write("Upload existing Ruckus datasheets to add them to your template library.")
        
        # Allow multiple file uploads
        uploaded_files = st.file_uploader(
            "Choose datasheet files",
            type=['txt', 'md', 'pdf'],
            accept_multiple_files=True,
            help="Upload text, markdown, or PDF files containing template datasheets"
        )
        
        if uploaded_files:
            upload_count = 0
            for uploaded_file in uploaded_files:
                # Check if already processed
                file_already_exists = any(
                    t.get('original_filename') == uploaded_file.name 
                    for t in st.session_state.templates.values()
                )
                
                if not file_already_exists:
                    try:
                        if uploaded_file.type == "application/pdf":
                            st.warning(f"PDF support coming soon. Skipping {uploaded_file.name}")
                            continue
                        else:
                            content = str(uploaded_file.read(), "utf-8")
                        
                        # Detect product type
                        product_type = detect_product_type(content)
                        
                        # Extract sections
                        sections = extract_key_sections(content)
                        
                        # Create unique template name
                        template_name = uploaded_file.name.replace('.txt', '').replace('.md', '').replace('.pdf', '')
                        existing_names = [t['name'] for t in st.session_state.templates.values()]
                        if template_name in existing_names:
                            template_name = f"{template_name}_{datetime.now().strftime('%H%M%S')}"
                        
                        # Auto-save the template
                        template_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{upload_count}"
                        
                        st.session_state.templates[template_id] = {
                            "name": template_name,
                            "original_filename": uploaded_file.name,
                            "product_type": product_type,
                            "content": content,
                            "sections": sections,
                            "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        upload_count += 1
                    except Exception as e:
                        st.error(f"Error processing {uploaded_file.name}: {str(e)}")
            
            if upload_count > 0:
                st.success(f"✅ Successfully uploaded {upload_count} template(s)")
                time.sleep(1)
                st.rerun()
            else:
                st.info("All uploaded files are already in the library or could not be processed.")
    
    with tab2:
        if not st.session_state.templates:
            st.info("No templates uploaded yet. Please upload datasheets in the 'Upload New Templates' tab.")
        else:
            st.write("Select a template from your library to use for generating a new datasheet.")
            
            # Filter by product type
            product_types_in_library = list(set(t['product_type'] for t in st.session_state.templates.values()))
            product_types_in_library.insert(0, "All")
            
            selected_filter = st.selectbox(
                "Filter by Product Type",
                product_types_in_library,
                format_func=lambda x: "All Product Types" if x == "All" else PRODUCT_TYPES.get(x, {}).get('name', x)
            )
            
            # Display templates
            templates_to_show = {
                tid: tdata for tid, tdata in st.session_state.templates.items()
                if selected_filter == "All" or tdata['product_type'] == selected_filter
            }
            
            if templates_to_show:
                st.write(f"**{len(templates_to_show)} template(s) available**")
                
                for tid, tdata in templates_to_show.items():
                    with st.expander(f"📄 {tdata['name']}", expanded=False):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**Product Type:** {PRODUCT_TYPES[tdata['product_type']]['name']}")
                            st.write(f"**Uploaded:** {tdata['upload_date']}")
                            
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
        st.info(f"Using template: **{template['name']}** ({PRODUCT_TYPES[template['product_type']]['name']})")
        
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
        
        with col2:
            st.subheader("New Specifications")
            st.write(f"**Specifications Provided:** {len([k for k, v in st.session_state.new_specs.items() if k != 'marketing_message'])}")
            st.write(f"**New Features:** {len(st.session_state.new_features)}")
        
        st.divider()
        
        # Generate button
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("← Back"):
                st.session_state.current_step = 2
                st.rerun()
        
        with col2:
            if st.button("🚀 Generate Datasheet", type="primary", disabled=not api_key, use_container_width=True):
                if api_key:
                    with st.spinner("Generating datasheet... This may take a moment."):
                        generated_content = generate_datasheet_with_llm(
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
                                "model_used": model_choice
                            }
                            st.session_state.generated_datasheets.append(datasheet)
                            st.success("✅ Datasheet generated successfully!")
                            
                            # Display the generated datasheet
                            st.divider()
                            st.subheader("Generated Datasheet")
                            
                            # Action buttons
                            col1, col2, col3 = st.columns(3)
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
                                html_content = f"""
                                <html>
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
                                    {generated_content.replace('```', '')}
                                </body>
                                </html>
                                """
                                st.download_button(
                                    label="📥 Download HTML",
                                    data=html_content,
                                    file_name=f"{datasheet['product_name']}_datasheet.html",
                                    mime="text/html",
                                    use_container_width=True
                                )
                            with col3:
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
                    st.error("Please enter your OpenAI API key in the sidebar.")
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
        
        # Filter datasheets
        filtered_datasheets = []
        for ds in reversed(st.session_state.generated_datasheets):
            if search_term and search_term.lower() not in ds['product_name'].lower():
                continue
            if filter_type != "All" and ds['product_type'] != filter_type:
                continue
            filtered_datasheets.append(ds)
        
        st.write(f"Showing {len(filtered_datasheets)} of {len(st.session_state.generated_datasheets)} datasheets")
        
        # Display filtered datasheets
        for ds in filtered_datasheets:
            with st.expander(f"📄 {ds['product_name']} - Generated {ds['generation_date']}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Template Used:** {ds['template_used']}")
                    st.write(f"**Product Type:** {PRODUCT_TYPES[ds['product_type']]['name']}")
                    st.write(f"**Model Used:** {ds.get('model_used', 'Unknown')}")
                    
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
                    st.download_button(
                        label="📥 Download MD",
                        data=ds['content'],
                        file_name=f"{ds['product_name']}_datasheet.md",
                        mime="text/markdown",
                        key=f"download_{ds['id']}"
                    )
                    
                    # Delete button
                    if st.button("🗑️ Delete", key=f"delete_ds_{ds['id']}"):
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

# Footer
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
        Ruckus Datasheet Generator v1.0 | Powered by OpenAI
    </div>
    """,
    unsafe_allow_html=True
)