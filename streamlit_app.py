"""
Wardley Map Visualization and Interaction Application

This Streamlit application enables users to view and interact with Wardley Maps from various sources
including a predefined list, direct map ID input, or a GitHub repository. It supports visualization
of maps using SVG rendering and provides an interactive interface for map selection and display.

The application fetches maps from:
1. Online Wardley Maps API (https://maps.wardleymaps.ai)
2. Simon Wardley's GitHub repository
3. User-provided map IDs

Features:
- Multiple map selection methods
- SVG-based map rendering
- Map warnings and error handling
- Responsive layout for different screen sizes
"""

import os
import base64
import requests
import streamlit as st
from github import Github, GithubException
from wardley_map import create_wardley_map_plot, create_svg_map
from typing import Optional, Tuple, Dict, List, Any

# Configuration constants
API_ENDPOINT = "https://maps.wardleymaps.ai/v2/maps/fetch?id="  # Online Wardley Maps API endpoint
GITHUB = st.secrets["GITHUB"]  # GitHub access token from Streamlit secrets
GITHUBREPO = "swardley/MAP-REPOSITORY"  # Simon Wardley's map repository
DEBUG = True  # Enable debug mode for additional logging and error information

# Dictionary of predefined maps with their corresponding IDs
map_dict: Dict[str, str] = {
    "Tea Shop": "b74c93cc19cfb8879b",
    "Agriculture 2023 Research": "163ed036fe13308f13",
    "AI & Entertainment": "aa08b8996aff3bca85",
    "Prompt Engineering": "38dfbb3dfc0f891d28",
}

def reset_map() -> None:
    """
    Resets all map-related session state variables to their default values.

    This function is called when switching between different maps to ensure
    a clean state for the new map visualization.
    """
    st.session_state["messages"] = []
    st.session_state["total_tokens_used"] = 0
    st.session_state["tokens_used"] = 0
    st.session_state["past"] = []
    st.session_state["generated"] = []
    st.session_state["disabled_buttons"] = []

def get_owm_map(map_id: str) -> Optional[str]:
    """
    Fetches map data from the Online Wardley Maps API.

    Args:
        map_id (str): The unique identifier of the map to fetch.

    Returns:
        Optional[str]: The map text if successful, None if the request fails.

    Raises:
        requests.exceptions.RequestException: If the API request fails.
    """
    try:
        response = requests.get(f"{API_ENDPOINT}{map_id}", timeout=10)
        response.raise_for_status()
        map_data = response.json()
        return map_data.get('text')
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching map data: {e}")
        return None
    except ValueError as e:
        st.error(f"Error parsing map data: {e}")
        return None

def initialize_session_state() -> None:
    """
    Initializes all required session state variables with default values.

    This function ensures all necessary session state variables exist and
    have appropriate default values when the application starts. It is called
    at application startup to set up the initial state.
    
    Session state variables include:
    - messages: List of conversation messages
    - total_tokens_used: Counter for total tokens used in conversations
    - tokens_used: Counter for tokens used in current interaction
    - past/generated: Lists for conversation history
    - map_text: Current map content in text format
    - current_map_id: ID of the currently displayed map
    - file_list: List of available map files from GitHub
    """
    defaults = {
        "messages": [],
        "total_tokens_used": 0,
        "tokens_used": 0,
        "past": [],
        "generated": [],
        "disabled_buttons": [],
        "map_text": "",
        "current_map_id": "",
        "file_list": []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Initialize Streamlit page configuration
st.set_page_config(page_title="Chat with your Map", layout="wide")

# Initialize session state variables for map display
# These are kept separate from initialize_session_state() to allow for 
# direct reference during app startup
if "map_text" not in st.session_state:
    st.session_state["map_text"] = ""  # Stores the text content of the current map

if "current_map_id" not in st.session_state:
    st.session_state["current_map_id"] = ""  # Tracks the ID of the currently displayed map

# Initialize GitHub connection for accessing Simon Wardley's map repository
try:
    g = Github(GITHUB)  # Create GitHub client with access token
    REPO = g.get_repo(GITHUBREPO)  # Access the repository containing maps
except GithubException as e:
    st.error(f"An error occurred contacting GitHub: {e}")
    REPO = None  # Set repo to None to handle the failure case gracefully

# Sidebar map selection interface with three options for map sources
map_selection = st.sidebar.radio(
    "Map Selection",
    ("Select from List", "Enter Map ID", "Select from GitHub"),
    help="Select GitHub to get a list of Simon's latest research.\n\nSelect from list to get predefined maps.\n\nSelect Enter Map ID to provide your own Onlinewardleymaps id",
    key="map_selection",
)

# Handle map selection logic
# MAP_ID will store the identifier for the selected map, regardless of source
MAP_ID = None

if map_selection == "Select from List":
    selected_name = st.sidebar.selectbox("Select Map", list(map_dict.keys()))
    MAP_ID = map_dict[selected_name]
elif map_selection == "Select from GitHub":
    # Recursively fetch all map files from Simon Wardley's GitHub repository
    with st.spinner("Fetching latest maps from GitHub"):
        if "file_list" not in st.session_state:
            # Initialize empty file list if not already in session state
            st.session_state.file_list = []
            contents = REPO.get_contents("")  # Get root contents
            
            # Recursively traverse repository to find all map files
            while contents:
                file_item = contents.pop(0)
                if file_item.type == "dir":
                    # Add directory contents to the processing queue
                    contents.extend(REPO.get_contents(file_item.path))
                else:
                    # Filter for Wardley map files (no extension, not hidden, not license)
                    file_name = file_item.name
                    if (
                        not file_name.startswith(".")  # Not hidden files
                        and os.path.splitext(file_name)[1] == ""  # No file extension
                        and file_name.lower() != "license"  # Not the license file
                    ):
                        st.session_state.file_list.append(file_item.path)

    # Display dropdown menu for map selection from GitHub
    if "file_list" in st.session_state:
        selected_file = st.sidebar.selectbox("Select a Map", st.session_state.file_list)
        file_item = REPO.get_contents(selected_file)  # Get file content from GitHub
        file_content = base64.b64decode(file_item.content).decode("utf-8")  # Decode content
        MAP_ID = selected_file  # Use file path as map ID
        st.session_state["file_content"] = file_content  # Store decoded content
else:
    # Handle direct map ID input from user
    MAP_ID = st.sidebar.text_input("Enter Map ID:", key="map_id_input")
    selected_name = MAP_ID  # Use the ID as the name when directly entered by user

# Handle map loading and display logic
if MAP_ID:
    # For online Wardley Maps API sources (predefined list or direct ID input)
    if map_selection != "Select from GitHub":
        # Only fetch new map if ID has changed
        if st.session_state.get("current_map_id") != MAP_ID:
            reset_map()  # Reset session state for new map
            st.session_state["current_map_id"] = MAP_ID  # Update current map ID
            st.session_state["map_text"] = get_owm_map(MAP_ID)  # Fetch map from API
            
            # Display error if map couldn't be retrieved
            if not st.session_state["map_text"]:
                st.error("Failed to retrieve map text. Please check the Map ID and try again.")
    # For GitHub source
    else:
        # Only update if map has changed
        if st.session_state.get("current_map_id") != MAP_ID:
            reset_map()  # Reset session state for new map
            st.session_state["current_map_id"] = MAP_ID  # Update current map ID
            st.session_state["map_text"] = st.session_state["file_content"]  # Use already fetched content

# Display the map if map text is available
if st.session_state.get("map_text"):
    try:
        # Generate Wardley Map visualization from text using wardley_map library
        map, map_plot = create_wardley_map_plot(st.session_state["map_text"])
        svg_map = create_svg_map(map_plot)  # Convert plot to SVG format

        # Encode SVG as base64 for embedding in HTML
        svg_b64 = base64.b64encode(svg_map.encode("utf-8")).decode("utf-8")

        # Create CSS wrapper for responsive layout
        css = '''
            <style>
                .map-container {
                    display: flex;
                    justify-content: center;
                    max-width: 100%;
                    margin: auto;
                }
                .map-container img {
                    max-width: 100%;
                    height: auto;
                }
            </style>
        '''

        # Create HTML with embedded SVG image
        html_map = f'{css}<img src="data:image/svg+xml;base64,{svg_b64}"/></div>'

        # Render the HTML in Streamlit
        st.write(html_map, unsafe_allow_html=True)

        # Display map title and warnings in sidebar for additional context
        with st.sidebar:
            # Extract map title from the map text
            TITLE = "No Title"
            map_text = st.session_state["map_text"]
            for line in map_text.split("\n"):
                if line.startswith("title"):
                    TITLE = line.split("title ")[1]
            
            # Display the title if found
            if TITLE:
                st.markdown(f"### {TITLE}")

            # Display any warnings from map parsing/rendering
            if map.warnings:
                st.write("Warnings parsing and drawing the map")
                for map_message in map.warnings:
                    st.warning(map_message)
    except Exception as e:
        # Handle any errors during map creation or rendering
        st.error(f"An error occurred while creating the map: {e}")
else:
    # Prompt user to select a map if none is selected
    st.info("Please select a map to display.")