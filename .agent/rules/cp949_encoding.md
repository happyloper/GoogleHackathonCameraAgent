---
description: Always enforce UTF-8 and avoid cp949 encoding errors on Windows
---

# Windows Encode/Decode (cp949) Rule

When writing Python scripts or any other code that interacts with standard output or file reading/writing on Windows, be aware that the default system encoding is often `cp949`. This can cause `UnicodeEncodeError` or `UnicodeDecodeError` when processing or printing characters like Emojis, Korean text, or special symbols.

**Always apply the following practices:**

1. **Standard Output**: Explicitly set the console output to UTF-8 at the top of Python scripts if there's a chance of printing special characters.
   ```python
   import sys
   import io
   
   if sys.stdout.encoding.lower() != 'utf-8':
       sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
   ```
2. **File I/O**: ALWAYS explicitly use `encoding="utf-8"` when using `open()`.
   ```python
   with open("file.txt", "w", encoding="utf-8") as f:
       f.write(text)
   ```
3. **Avoid Emojis in raw `print` on weak terminals**: While UTF-8 stdout reconfiguration usually fixes it, if a barebones Windows `cmd.exe` process is known to be running the script, consider avoiding complex multi-byte Emojis (`🎙️`, `✨` etc.) in basic `print()` statements unless strictly requested, to guarantee cross-compatibility without crashing. 
