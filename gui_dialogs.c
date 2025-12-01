#include "gui_dialogs.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef __APPLE__
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#endif

// Simple dynamic string duplicator
static char *str_dup(const char *src) {
    if (!src) return NULL;
    size_t len = strlen(src);
    char *out = (char *)malloc(len + 1);
    if (out) strcpy(out, src);
    return out;
}

// Escape double quotes for osascript strings
static char *escape_quotes(const char *text) {
    size_t len = strlen(text);
    size_t extra = 0;
    for (size_t i = 0; i < len; ++i) {
        if (text[i] == '"') extra++;
    }
    char *out = (char *)malloc(len + extra + 1);
    if (!out) return NULL;
    size_t j = 0;
    for (size_t i = 0; i < len; ++i) {
        if (text[i] == '"') out[j++] = '\\';
        out[j++] = text[i];
    }
    out[j] = '\0';
    return out;
}

static char *read_line(void) {
    size_t cap = 256;
    size_t len = 0;
    char *buf = (char *)malloc(cap);
    if (!buf) return NULL;
    int ch;
    while ((ch = getchar()) != EOF && ch != '\n') {
        if (len + 1 >= cap) {
            cap *= 2;
            char *tmp = (char *)realloc(buf, cap);
            if (!tmp) {
                free(buf);
                return NULL;
            }
            buf = tmp;
        }
        buf[len++] = (char)ch;
    }
    buf[len] = '\0';
    return buf;
}

#ifdef __APPLE__
static char *run_command_capture(const char *cmd) {
    FILE *fp = popen(cmd, "r");
    if (!fp) return NULL;
    size_t cap = 512;
    size_t len = 0;
    char *buf = (char *)malloc(cap);
    if (!buf) {
        pclose(fp);
        return NULL;
    }
    int ch;
    while ((ch = fgetc(fp)) != EOF) {
        if (len + 1 >= cap) {
            cap *= 2;
            char *tmp = (char *)realloc(buf, cap);
            if (!tmp) {
                free(buf);
                pclose(fp);
                return NULL;
            }
            buf = tmp;
        }
        buf[len++] = (char)ch;
    }
    buf[len] = '\0';
    pclose(fp);
    return buf;
}
#endif

int gui_confirm(const char *title, const char *message, int default_yes) {
#ifdef __APPLE__
    char *safe_msg = escape_quotes(message ? message : "");
    if (!safe_msg) return default_yes;
    const char *default_button = default_yes ? "Yes" : "No";
    char command[2048];
    snprintf(command, sizeof(command),
             "osascript -e 'display dialog \"%s\" with title \"%s\" buttons {\"No\",\"Yes\"} default button \"%s\"'",
             safe_msg, title ? title : "", default_button);
    free(safe_msg);
    char *out = run_command_capture(command);
    if (out) {
        int yes = strstr(out, "button returned:Yes") != NULL;
        free(out);
        return yes;
    }
#endif
    printf("%s\n%s [y/N]: ", title ? title : "", message ? message : "");
    fflush(stdout);
    char *line = read_line();
    if (!line) return default_yes;
    int yes = (line[0] == 'y' || line[0] == 'Y');
    free(line);
    return yes;
}

char *gui_prompt_text(const char *title, const char *message, const char *default_value) {
#ifdef __APPLE__
    char *safe_msg = escape_quotes(message ? message : "");
    char *safe_def = escape_quotes(default_value ? default_value : "");
    if (!safe_msg || !safe_def) {
        free(safe_msg);
        free(safe_def);
        return default_value ? str_dup(default_value) : NULL;
    }
    char command[4096];
    snprintf(command, sizeof(command),
             "osascript -e 'display dialog \"%s\" with title \"%s\" default answer \"%s\"'",
             safe_msg, title ? title : "", safe_def);
    free(safe_msg);
    free(safe_def);
    char *out = run_command_capture(command);
    if (out) {
        char *pos = strstr(out, "text returned:");
        if (pos) {
            pos += strlen("text returned:");
            while (*pos == ' ' || *pos == '\t') pos++;
            char *trim = str_dup(pos);
            free(out);
            if (trim) {
                size_t len = strlen(trim);
                while (len > 0 && (trim[len - 1] == '\n' || trim[len - 1] == '\r')) {
                    trim[len - 1] = '\0';
                    len--;
                }
            }
            return trim;
        }
        free(out);
    }
#endif
    printf("%s\n%s\n(default: %s) > ", title ? title : "", message ? message : "", default_value ? default_value : "");
    fflush(stdout);
    char *line = read_line();
    if (!line || strlen(line) == 0) {
        free(line);
        return default_value ? str_dup(default_value) : NULL;
    }
    return line;
}

char *gui_select_folder(const char *title, const char *default_path) {
#ifdef __APPLE__
    char *safe_title = escape_quotes(title ? title : "");
    char *safe_default = escape_quotes(default_path ? default_path : "");
    if (!safe_title || !safe_default) {
        free(safe_title);
        free(safe_default);
        return default_path ? str_dup(default_path) : NULL;
    }
    char command[4096];
    snprintf(command, sizeof(command),
             "osascript -e 'set theFolder to POSIX path of (choose folder with prompt \"%s\" default location POSIX file \"%s\")'",
             safe_title, safe_default);
    free(safe_title);
    free(safe_default);
    char *out = run_command_capture(command);
    if (out && strlen(out) > 0) {
        // Trim trailing newlines
        size_t len = strlen(out);
        while (len > 0 && (out[len - 1] == '\n' || out[len - 1] == '\r')) {
            out[len - 1] = '\0';
            len--;
        }
        return out;
    }
    free(out);
#endif
    printf("%s\n기본 폴더: %s\n원하는 설치 경로를 입력하세요: ", title ? title : "", default_path ? default_path : "");
    fflush(stdout);
    char *line = read_line();
    if (!line || strlen(line) == 0) {
        free(line);
        return default_path ? str_dup(default_path) : NULL;
    }
    return line;
}
