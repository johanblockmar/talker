# Voices for Chatterbox

Drop reference recordings here (or in `%APPDATA%\Talker\voices`) to use them as voices.

* `myvoice.wav`: a single 5 to 15 second clip of clean speech, no music or noise.
* `myvoice/neutral.wav`, `myvoice/happy.wav`, `myvoice/sad.wav`, ...: one clip per mood.
  Talker picks the clip matching the current mood, which gives the most convincing emotion.
  Missing moods fall back to `neutral.wav`.

Then choose `myvoice` in the Voice box, or pass `--voice myvoice` on the command line.
Recordings in this folder are ignored by git.
