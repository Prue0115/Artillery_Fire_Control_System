#ifndef GUI_DIALOGS_H
#define GUI_DIALOGS_H

// Minimal dialog helpers with macOS-first UX (osascript) and CLI fallback.
// These utilities prefer native dialogs on macOS for an "Apple-like" feel.
// On other platforms, they fall back to console prompts to remain portable.

char *gui_select_folder(const char *title, const char *default_path);
int gui_confirm(const char *title, const char *message, int default_yes);
char *gui_prompt_text(const char *title, const char *message, const char *default_value);

// Caller must free returned strings.

#endif // GUI_DIALOGS_H
