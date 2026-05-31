# Yoto Playlist Builder

An agentic-driven project that allows you to easily create, build, and update kids' audio playlists on a Yoto player via the Yoto HTTP API (api.yotoplay.com). 

This repository provides a set of generalized `.md` instruction files and Python scripts designed to be driven by an autonomous AI agent (such as Claude Code, Pi.dev, Cline, Copilot, Antigravity, etc.).

## How it works

The core philosophy of this project is that an AI Agent is perfectly suited to manage the tedious parts of playlist creation (downloading audio, resizing images, uploading via API, writing metadata). You, the user, just provide a starting point—like a YouTube playlist or a folder of MP3s—and the agent takes care of the rest.

## Getting Started

1. **Clone this repository** to a local directory.
2. **Set up your environment**: Ensure you have Python 3.13 (with `Pillow` installed) and `ffmpeg` available on your PATH.
3. **Get your Yoto Token**:
   - Open [my.yotoplay.com](https://my.yotoplay.com) in your browser and log in.
   - Open Developer Tools (F12) -> Console.
   - Run `copy(localStorage.access_token)`.
   - Paste the token into a file named `.yoto_token.txt` in the root of this project (or set it as an environment variable `YOTO_TOKEN`). The token usually lasts about 24 hours.
4. **Point your Agent**:
   Start your favorite agent harness in this folder and point it at the `AGENT_INSTRUCTIONS.md` file. For example:
   - *"Hey agent, read AGENT_INSTRUCTIONS.md and help me create a Yoto playlist from this YouTube link: [link]"*
   - *"Please follow AGENT_INSTRUCTIONS.md to upload the MP3s in my `C:\Music\Audiobook` folder to a new Yoto card."*

The agent will read the instructions, figure out which reference guides to follow, and use the included Python scripts to get the job done!

## License
Open Source (MIT).
