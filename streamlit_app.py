import os
import base64
import requests
import streamlit as st
from github import Github, GithubException
from wardley_map import create_wardley_map_plot, create_svg_map

API_ENDPOINT = "https://maps.wardleymaps.ai/v2/maps/fetch?id="
GITHUB = st.secrets["GITHUB"]
GITHUBREPO = "swardley/MAP-REPOSITORY"
DEBUG = True  # True to overwrite files that already exist
MAP_ID = None

# Dictionary of map IDs with user-friendly names
map_dict = {
    "Tea Shop": "b74c93cc19cfb8879b",
    "Agriculture 2023 Research": "163ed036fe13308f13",
    "AI & Entertainment": "aa08b8996aff3bca85",
    "Prompt Engineering": "38dfbb3dfc0f891d28",
}

# Reset the map on page reload
def reset_map():
    st.session_state["messages"] = []
    st.session_state["total_tokens_used"] = 0
    st.session_state["tokens_used"] = 0
    st.session_state["past"] = []
    st.session_state["generated"] = []
    st.session_state["disabled_buttons"] = []

def get_owm_map(map_id):
    try:
        response = requests.get(f"{API_ENDPOINT}{map_id}")
        response.raise_for_status()
        map_data = response.json()
        if 'text' in map_data:
            return map_data['text']
        else:
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching map data: {e}")
        return None

st.set_page_config(page_title="Chat with your Map", layout="wide")

if "map_text" not in st.session_state:
    st.session_state["map_text"] = ""

if "current_map_id" not in st.session_state:
    st.session_state["current_map_id"] = ""

try:
    g = Github(GITHUB)
    REPO = g.get_repo(GITHUBREPO)
except GithubException as e:
    st.error(f"An error occurred contacting GitHub: {e}")
    REPO = None

map_selection = st.sidebar.radio(
    "Map Selection",
    ("Select from List", "Enter Map ID", "Select from GitHub"),
    help="Select GitHub to get a list of Simon's latest research.\n\nSelect from list to get predefined maps.\n\nSelect Enter Map ID to provide your own Onlinewardleymaps id",
    key="map_selection",
)

if map_selection == "Select from List":
    selected_name = st.sidebar.selectbox("Select Map", list(map_dict.keys()))
    MAP_ID = map_dict[selected_name]
elif map_selection == "Select from GitHub":
    with st.spinner("Fetching latest maps from GitHub"):
        if "file_list" not in st.session_state:
            st.session_state.file_list = []
            contents = REPO.get_contents("")
            while contents:
                file_item = contents.pop(0)
                if file_item.type == "dir":
                    contents.extend(REPO.get_contents(file_item.path))
                else:
                    file_name = file_item.name
                    if (
                        not file_name.startswith(".")
                        and os.path.splitext(file_name)[1] == ""
                        and file_name.lower() != "license"
                    ):
                        st.session_state.file_list.append(file_item.path)

    if "file_list" in st.session_state:
        selected_file = st.sidebar.selectbox("Select a Map", st.session_state.file_list)
        file_item = REPO.get_contents(selected_file)
        file_content = base64.b64decode(file_item.content).decode("utf-8")
        MAP_ID = selected_file
        st.session_state["file_content"] = file_content
else:
    MAP_ID = st.sidebar.text_input("Enter Map ID:", key="map_id_input")
    selected_name = MAP_ID

if MAP_ID:
    if map_selection != "Select from GitHub":
        if st.session_state.get("current_map_id") != MAP_ID:
            reset_map()
            st.session_state["current_map_id"] = MAP_ID
            st.session_state["map_text"] = get_owm_map(MAP_ID)
            if not st.session_state["map_text"]:
                st.error("Failed to retrieve map text. Please check the Map ID and try again.")
    else:
        if st.session_state.get("current_map_id") != MAP_ID:
            reset_map()
            st.session_state["current_map_id"] = MAP_ID
            st.session_state["map_text"] = st.session_state["file_content"]

# Display the map in the sidebar
if st.session_state.get("map_text"):
    try:
        # Get the Wardley Map
        map, map_plot = create_wardley_map_plot(st.session_state["map_text"])
        svg_map = create_svg_map(map_plot)

        # Encode as base 64
        svg_b64 = base64.b64encode(svg_map.encode("utf-8")).decode("utf-8")

        # Create CSS wrapper
        css = '<p style="text-align:center; display: flex; justify-content: center;">'

        # Create HTML
        html_map = r'{}<img src="data:image/svg+xml;base64,{}"/>'.format(css, svg_b64)

        # Write the HTML
        st.write(html_map, unsafe_allow_html=True)

        with st.sidebar:
            TITLE = "No Title"
            map_text = st.session_state["map_text"]
            for line in map_text.split("\n"):
                if line.startswith("title"):
                    TITLE = line.split("title ")[1]
            if TITLE:
                st.markdown(f"### {TITLE}")

            # Display any warnings drawing the map
            if map.warnings:
                st.write("Warnings parsing and drawing the map")
                for map_message in map.warnings:
                    st.warning(map_message)
    except Exception as e:
        st.error(f"An error occurred while creating the map: {e}")
else:
    st.info("Please select a map to display.")
