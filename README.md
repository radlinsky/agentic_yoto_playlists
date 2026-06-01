# Yoto Playlist Builder
An agentic-driven project that allows you to easily create, build, and update kids' audio playlists on a Yoto player via the [Yoto HTTP API](https://yoto.dev/api/). 

This repository provides a set of generalized `.md` instruction files and Python scripts designed to be driven by an autonomous AI agent (such as Claude Code, Pi.dev, Cline, Copilot, Antigravity, etc.).
## How It Works
The core philosophy of this project is that an AI Agent is perfectly suited to manage the tedious parts of playlist creation (downloading audio, resizing images, uploading via API, writing metadata). 

You, the user, just provide a starting point like a link to a Creative Commons [Internet Archive](https://archive.org) list of audio files, a Creative Commons YouTube playlist, OR a local folder of MP3s on your computer.

The agent then automatically takes care of the rest.
## Getting Started. 
1. **Clone this repository** to a local directory.
2. **Set up your environment**: Ensure you have Python 3.13 (with `Pillow` installed) and `ffmpeg` available on your system `PATH`.
3. **Get your Yoto Token**:
   * Open [my.yotoplay.com](https://my.yotoplay.com) in your browser and log in.
   * Open Developer Tools (`F12`) and select the **Console** tab.
   * Run the following command:
     ```javascript
     copy(localStorage.access_token)
     ```
   * Paste the token into a file named `.yoto_token.txt` in the root of this project, or set it as an environment variable named `YOTO_TOKEN`. *(Note: The token usually lasts about 24 hours).*
4. **Point your Agent**: Start your favorite agent harness in this folder and point it at the `AGENT_INSTRUCTIONS.md` file. 
### Example Prompts

*"Hey agent, read AGENT_INSTRUCTIONS.md and help me create a Yoto playlist from this YouTube link: [link]"*

*"Please follow AGENT_INSTRUCTIONS.md to upload the MP3s in my `C:\Music\Audiobook` folder to a new Yoto card."*

The agent will read the instructions, figure out which reference guides to follow, and use the included Python scripts to get the job done!

## Example Run

Prompted the agent with: 

> *"Read AGENT_INSTRUCTIONS.md and create a yoto card playlist from https://archive.org/metadata/aesop_fables_volume_one_librivox/files"*

See this [hosted execution log](https://htmlpreview.github.io/?https://github.com/radlinsky/agentic_yoto_playlists/blob/main/example.html&leafId=eab39ea5&targetId=e4cc691e) to see how a locally hosted model running via `pi.dev` reasons through the request.

### What the Agent Does Automatically
1. **Downloads audio**: Pulls down all songs/chapters into an `/audio` subfolder (e.g., takes ~10-15 minutes for a full album).
2. **Uploads audio files to Yoto**: Pushes all audio tracks to your Yoto library via the Yoto API.
3. **Fetches icons**: Reads track titles and pulls matching icons from the Yoto Icons library.
4. **Creates album artwork**: Generates a composite album cover using a mosaic tile layout of the track icons.
5. **Uploads image files to Yoto**: Uploads the icons and the new album artwork to the playlist.
6. **Writes card description**: Automatically generates a description for the album.
7. **Generates printables**: Creates a ready-to-print PDF of the album cover to cut and tape onto a physical Yoto card.

## License
This project is open-source software licensed under the [MIT License](LICENSE).
