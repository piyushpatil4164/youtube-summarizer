# 🎓 AI YouTube Lecture Digest

A Streamlit application that turns educational lecture transcripts into structured study notes, summaries, quizzes, flashcards, searchable subtitles, mind maps, and downloadable PDFs.

## Important YouTube Cloud Deployment Note

YouTube currently blocks many transcript requests originating from cloud-provider IP ranges. The `youtube-transcript-api` project documents this as a `RequestBlocked` / `IpBlocked` problem and recommends a proxy, especially a rotating residential proxy, for cloud deployments.

This project therefore supports:

1. Normal direct caption retrieval.
2. An optional HTTP/HTTPS proxy through `YOUTUBE_PROXY_URL`.
3. Direct transcript/lecture-text input when a video has no accessible captions.
4. Built-in demo transcript fallback for the three sample buttons when YouTube blocks the Streamlit server. Demo fallback is clearly marked in the UI and is not presented as live YouTube data.

## Features

- YouTube URL parsing for watch, youtu.be, shorts, live, embed, and raw video IDs.
- Caption retrieval with timestamped segments.
- Current `youtube-transcript-api` API with compatibility handling for older releases.
- Long-transcript map/reduce processing that processes every transcript chunk.
- Groq AI generation with current GPT-OSS models and fallback handling.
- Detailed notes, executive summaries, bullet points, quizzes/flashcards, and cheat sheets.
- Chat with the transcript.
- Mermaid concept mind map.
- Searchable subtitle list.
- Markdown and PDF download.

## Streamlit Secrets

At minimum:

```toml
GROQ_API_KEY = "your_groq_api_key"
```

For live YouTube transcript retrieval on Streamlit Cloud, add a working HTTP/HTTPS proxy as well:

```toml
YOUTUBE_PROXY_URL = "http://username:password@proxy-host:proxy-port"
```

The proxy must be a service that permits HTTPS traffic and is suitable for YouTube requests. A residential rotating proxy is generally more appropriate than a static datacenter proxy for this use case.

Do **not** put cookies.txt into Streamlit Secrets or GitHub. This application does not require the previously uploaded cookie file.

## Local setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Security

If a real browser cookie export was ever committed to GitHub or uploaded publicly, treat those sessions as compromised. Remove the file from the repository/history where applicable and sign out/revoke affected sessions. Never commit browser cookies, API keys, or Streamlit secrets.
