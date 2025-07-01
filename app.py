from flask import Flask, request, render_template_string, send_file
from youtube_transcript_api._api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
import re
import io

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Transcript App</title>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {
            min-height: 100vh;
            margin: 0;
            font-family: 'Montserrat', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            flex-direction: column;
        }
        .container {
            max-width: 500px;
            margin: 60px auto 20px auto;
            background: #fff;
            border-radius: 18px;
            box-shadow: 0 8px 32px rgba(44, 62, 80, 0.15);
            padding: 36px 32px 28px 32px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 {
            color: #5f2c82;
            font-weight: 700;
            margin-bottom: 18px;
            letter-spacing: 1px;
        }
        form {
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        label {
            font-weight: 600;
            color: #333;
        }
        input[type="text"] {
            padding: 10px 12px;
            border: 1.5px solid #764ba2;
            border-radius: 8px;
            font-size: 1rem;
            outline: none;
            transition: border 0.2s;
        }
        input[type="text"]:focus {
            border: 2px solid #667eea;
        }
        button {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            border: none;
            border-radius: 8px;
            padding: 12px 0;
            font-size: 1.1rem;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(44, 62, 80, 0.10);
            transition: background 0.2s, transform 0.1s;
        }
        button:hover {
            background: linear-gradient(90deg, #764ba2 0%, #667eea 100%);
            transform: translateY(-2px) scale(1.03);
        }
        .error {
            color: #e74c3c;
            margin-top: 10px;
            font-weight: 600;
        }
        .transcript-section {
            width: 100%;
            margin-top: 28px;
        }
        .transcript-section h2 {
            color: #764ba2;
            margin-bottom: 10px;
        }
        textarea {
            width: 100%;
            height: 320px;
            border-radius: 10px;
            border: 1.5px solid #764ba2;
            padding: 14px;
            font-size: 1rem;
            background: #f7f7fb;
            color: #222;
            resize: vertical;
            box-shadow: 0 2px 8px rgba(44, 62, 80, 0.07);
        }
        footer {
            margin-top: auto;
            text-align: center;
            color: #fff;
            padding: 18px 0 10px 0;
            font-size: 1rem;
            letter-spacing: 0.5px;
            opacity: 0.85;
        }
        @media (max-width: 600px) {
            .container {
                max-width: 98vw;
                padding: 18px 6vw 18px 6vw;
            }
            textarea {
                height: 180px;
            }
        }
        .download-btn {
            margin-top: 12px;
            background: linear-gradient(90deg, #43cea2 0%, #185a9d 100%);
            color: #fff;
            border: none;
            border-radius: 8px;
            padding: 10px 0;
            font-size: 1rem;
            font-weight: 700;
            cursor: pointer;
            width: 100%;
            box-shadow: 0 2px 8px rgba(44, 62, 80, 0.10);
            transition: background 0.2s, transform 0.1s;
        }
        .download-btn:hover {
            background: linear-gradient(90deg, #185a9d 0%, #43cea2 100%);
            transform: translateY(-2px) scale(1.03);
        }
        .copy-btn {
            margin-top: 12px;
            background: linear-gradient(90deg, #ffb347 0%, #ffcc33 100%);
            color: #222;
            border: none;
            border-radius: 8px;
            padding: 10px 0;
            font-size: 1rem;
            font-weight: 700;
            cursor: pointer;
            width: 100%;
            box-shadow: 0 2px 8px rgba(44, 62, 80, 0.10);
            transition: background 0.2s, transform 0.1s;
        }
        .copy-btn:hover {
            background: linear-gradient(90deg, #ffcc33 0%, #ffb347 100%);
            transform: translateY(-2px) scale(1.03);
        }
        .copied-msg {
            color: #27ae60;
            font-weight: 600;
            margin-top: 8px;
            text-align: center;
            display: none;
        }
        .copied-msg.show {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>YouTube Transcript App</h1>
        <form method="post">
            <label for="url">YouTube Video URL or ID:</label>
            <input type="text" id="url" name="url" required value="{{ url|default('') }}">
            {% if languages and languages|length > 1 %}
                <label for="language">Transcript Language:</label>
                <select id="language" name="language">
                    {% for code, name in languages %}
                        <option value="{{ code }}" {% if code == selected_language %}selected{% endif %}>{{ name }} ({{ code }})</option>
                    {% endfor %}
                </select>
            {% endif %}
            <button type="submit">Get Transcript</button>
        </form>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
        {% if transcript %}
            <div class="transcript-section">
                <h2>Transcript</h2>
                <textarea id="transcript-text" readonly>{{ transcript }}</textarea>
                <button type="button" class="copy-btn" onclick="copyTranscript()">Copy Transcript</button>
                <div id="copied-msg" class="copied-msg">Copied!</div>
                <form method="post" action="/download">
                    <input type="hidden" name="transcript" value="{{ transcript|e }}">
                    <button type="submit" class="download-btn">Download as .txt</button>
                </form>
            </div>
        {% endif %}
    </div>
    <footer>
        &copy; {{ 2024 }} YouTube Transcript App &mdash; Made by DEVAIR
    </footer>
    <script>
        function copyTranscript() {
            var textarea = document.getElementById('transcript-text');
            textarea.select();
            textarea.setSelectionRange(0, 99999); // For mobile devices
            document.execCommand('copy');
            var msg = document.getElementById('copied-msg');
            msg.classList.add('show');
            setTimeout(function() {
                msg.classList.remove('show');
            }, 1200);
        }
    </script>
</body>
</html>
'''

def extract_video_id(url_or_id):
    # Try to extract video ID from URL or accept as is
    regex = r"(?:v=|youtu\.be/|youtube\.com/embed/)([\w-]{11})"
    match = re.search(regex, url_or_id)
    if match:
        return match.group(1)
    if re.match(r"^[\w-]{11}$", url_or_id):
        return url_or_id
    return None

def format_timestamp(seconds):
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

@app.route('/', methods=['GET', 'POST'])
def index():
    transcript = None
    error = None
    url = ''
    languages = []
    selected_language = None
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        selected_language = request.form.get('language')
        video_id = extract_video_id(url)
        if not video_id:
            error = 'Invalid YouTube URL or ID.'
        else:
            try:
                transcript_list = None
                transcript_info = YouTubeTranscriptApi.list_transcripts(video_id)
                languages = [(t.language_code, t.language) for t in transcript_info]
                if selected_language:
                    transcript_obj = transcript_info.find_transcript([selected_language])
                    transcript_list = transcript_obj.fetch()
                else:
                    transcript_obj = next(iter(transcript_info))
                    transcript_list = transcript_obj.fetch()
                    selected_language = transcript_obj.language_code
                transcript = '\n'.join([
                    f"{format_timestamp(snippet.start)} {snippet.text}" for snippet in transcript_list
                ])
            except TranscriptsDisabled:
                error = 'Transcripts are disabled for this video.\nPossible reasons: The video owner has disabled captions or the video is a live stream.\nSolution: Try another video.'
            except NoTranscriptFound:
                error = 'No transcript found for this video.\nPossible reasons: The video is too new, private, or has no captions.\nSolution: Try another video or check back later.'
            except VideoUnavailable:
                error = 'Video unavailable.\nPossible reasons: The video is private, deleted, or restricted in your region.\nSolution: Check the video URL or try a different video.'
            except Exception as e:
                error = f'An unexpected error occurred: {str(e)}\nPossible reasons: Network issues, invalid video ID, or YouTube API changes.\nSolution: Check your internet connection or try again later.'
    return render_template_string(HTML_TEMPLATE, transcript=transcript, error=error, url=url, languages=languages, selected_language=selected_language)

@app.route('/download', methods=['POST'])
def download():
    transcript = request.form.get('transcript', '')
    if not transcript:
        return 'No transcript to download.', 400
    buf = io.BytesIO()
    buf.write(transcript.encode('utf-8'))
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name='transcript.txt',
        mimetype='text/plain'
    )

if __name__ == '__main__':
    app.run(debug=True) 