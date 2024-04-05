import os, re, json, toml, base64
import streamlit as st
from github import Github
from wardley_map import (
    create_wardley_map_plot,
    get_owm_map,
    convert_owm2json,
    convert_owm2toml,
    convert_owm2cypher,
    convert_owm2graph,
    convert_owm2yaml,
    parse_wardley_map
)

API_ENDPOINT = "https://api.onlinewardleymaps.com/v1/maps/fetch?id="
GITHUB = st.secrets["GITHUB"]
GITHUBREPO = "swardley/MAP-REPOSITORY"
DEBUG = True  # True to overwrite files that already exist
MAP_ID = None

# Dictionary of map IDs with user-friendly names
map_dict = {
    "Tea Shop": "QRXryFJ8Q1NxhbHKQL",
    "Agriculture 2023 Research": "gQuu7Kby3yYveDngy2",
    "AI & Entertainment": "1LSW3jTlx4u16T06di",
    "Prompt Engineering": "mUJtoSmOfqlfXhNMJP",
    "Microsoft Fabric": "K4DjW1RdsbUWV8JzoP",
    "Fixed Penalty Notices": "gTTfD4r2mORudVFKge",
}


# Reset the map on page reload
def reset_map():
    st.session_state["messages"] = []
    st.session_state["total_tokens_used"] = 0
    st.session_state["tokens_used"] = 0
    st.session_state["past"] = []
    st.session_state["generated"] = []
    st.session_state["disabled_buttons"] = []


st.set_page_config(page_title="Chat with your  Map", layout="wide")

if "map_text" not in st.session_state:
    st.session_state["map_text"] = []

if "current_map_id" not in st.session_state:
    st.session_state["current_map_id"] = []

try:
    g = Github(GITHUB)
    REPO = g.get_repo(GITHUBREPO)
except GithubException as e:
    st.error(f"An error occurred contacting GitHub: {e}")
    REPO = None

map_selection = st.sidebar.radio(
    "Map Selection",
    ("Select from GitHub", "Select from List", "Enter Map ID"),
    help="Select GitHub to get a list of Simon 's latest research.\n\nSelect from list to get predefined maps.\n\nSelect Enter Map ID to provide your own Onlinewardleymaps id",
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
                    # Check if the file name starts with a '.', has no extension, or is named 'LICENSE'
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

if map_selection != "Select from GitHub":
    if st.session_state.get("current_map_id") != MAP_ID:
        reset_map()
        del st.session_state["messages"]
        st.session_state["current_map_id"] = MAP_ID
        st.session_state["map_text"] = get_owm_map(MAP_ID)

if map_selection == "Select from GitHub":
    if st.session_state.get("current_map_id") != MAP_ID:
        reset_map()
        st.session_state["current_map_id"] = MAP_ID
        st.session_state["map_text"] = st.session_state["file_content"]

# Display the map in the sidebar
if "map_text" in st.session_state:
    with st.sidebar:
        TITLE = "No Title"
        map_text = st.session_state["map_text"]
        for line in map_text.split("\n"):
            if line.startswith("title"):
                TITLE = line.split("title ")[1]
        if TITLE:
            st.markdown(f"### {TITLE}")

        # Get the Wardley Map
        map, map_plot = create_wardley_map_plot(map_text)

        # Encode as base 64
        svg_b64 = base64.b64encode(map_plot.encode("utf-8")).decode("utf-8")

        # Create CSS wrapper
        css = '<p style="text-align:center; display: flex; justify-content: {};">'.format("center")

        # Create HTML
        html_map = r'{}<img src="data:image/svg+xml;base64,{}"/>'.format(css, svg_b64)

        # Write the HTML
        st.write(html_map, unsafe_allow_html=True)

        # Display any warnings drawing the map
        if map.warnings:
            st.write("Warnings parsing and the drawing map")
            for map_message in map.warnings:
                st.warning(map_message)
