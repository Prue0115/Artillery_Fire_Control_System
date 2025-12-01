#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include "gui_dialogs.h"

#ifndef _WIN32
#include <libgen.h>
#endif

static int mkdir_p(const char *path) {
    char tmp[1024];
    snprintf(tmp, sizeof(tmp), "%s", path);
    size_t len = strlen(tmp);
    if (len == 0) return -1;
    if (tmp[len - 1] == '/') tmp[len - 1] = '\0';
    for (char *p = tmp + 1; *p; p++) {
        if (*p == '/') {
            *p = '\0';
            mkdir(tmp, 0755);
            *p = '/';
        }
    }
    return mkdir(tmp, 0755) == 0 || errno == EEXIST ? 0 : -1;
}

static int copy_file(const char *src, const char *dst) {
    FILE *in = fopen(src, "rb");
    if (!in) return -1;
    FILE *out = fopen(dst, "wb");
    if (!out) {
        fclose(in);
        return -1;
    }
    char buf[4096];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), in)) > 0) {
        if (fwrite(buf, 1, n, out) != n) {
            fclose(in);
            fclose(out);
            return -1;
        }
    }
    fclose(in);
    fclose(out);
    return 0;
}

static int copy_range_tables(const char *dest_root) {
    DIR *dir = opendir("rangeTables");
    if (!dir) return -1;
    mkdir_p(dest_root);
    char dest_path[1024];
    struct dirent *entry;
    int copied = 0;
    int seen = 0;
    while ((entry = readdir(dir)) != NULL) {
        if (entry->d_name[0] == '.') continue;
        seen++;
        snprintf(dest_path, sizeof(dest_path), "%s/%s", dest_root, entry->d_name);
        char src_path[1024];
        snprintf(src_path, sizeof(src_path), "rangeTables/%s", entry->d_name);
        if (access(dest_path, F_OK) == 0) {
            printf("이미 존재하는 레인지 테이블을 건너뜁니다: %s\n", dest_path);
            continue;
        }
        if (copy_file(src_path, dest_path) != 0) {
            closedir(dir);
            return -1;
        }
        copied++;
    }
    closedir(dir);
    if (seen == 0) {
        fprintf(stderr, "rangeTables 폴더에 복사할 CSV가 없습니다. 프로그램이 데이터를 생성하지 않으므로 먼저 CSV를 넣으세요.\n");
        return -1;
    }
    return 0;
}

static int compile_cli(void) {
    int result = system("cc -o cli_calculator cli_calculator.c");
    return result == 0;
}

static int create_launcher(const char *install_dir, int create_shortcut) {
    char launcher_path[1024];
    snprintf(launcher_path, sizeof(launcher_path), "%s/ArtilleryCalculator.command", install_dir);
    FILE *f = fopen(launcher_path, "w");
    if (!f) return -1;
    fprintf(f, "#!/bin/bash\ncd \"%s\"\n./cli_calculator \"$@\"\n", install_dir);
    fclose(f);
    chmod(launcher_path, 0755);

    if (create_shortcut) {
#ifdef __APPLE__
        // Create desktop alias using osascript for an Apple-like shortcut
        char command[2048];
        snprintf(command, sizeof(command),
                 "osascript -e 'tell application \"Finder\" to make alias file to POSIX file \"%s\" at POSIX file (path to desktop as text)'",
                 launcher_path);
        system(command);
#else
        // Fallback: symlink on Desktop
        const char *home = getenv("HOME");
        if (home) {
            char desktop[1024];
            snprintf(desktop, sizeof(desktop), "%s/Desktop/ArtilleryCalculator", home);
            symlink(launcher_path, desktop);
        }
#endif
    }
    return 0;
}

static void show_summary(const char *install_dir, int shortcut) {
    printf("\n설치가 완료되었습니다!\n");
    printf("설치 경로: %s\n", install_dir);
    printf("런처: %s/ArtilleryCalculator.command\n", install_dir);
    if (shortcut) {
        printf("바탕화면에 바로가기(또는 alias)가 생성되었습니다.\n");
    }
    printf("\n터미널에서 \"%s/ArtilleryCalculator.command --help\" 를 실행해보세요.\n", install_dir);
}

static char *default_install_dir(void) {
#ifdef __APPLE__
    const char *home = getenv("HOME");
    if (!home) home = "/Users/Shared";
    char *path = (char *)malloc(1024);
    snprintf(path, 1024, "%s/Applications/ArtilleryCalculator", home);
    return path;
#elif defined(_WIN32)
    const char *home = getenv("USERPROFILE");
    if (!home) home = "C:/Users/Public";
    char *path = (char *)malloc(1024);
    snprintf(path, 1024, "%s/ArtilleryCalculator", home);
    return path;
#else
    const char *home = getenv("HOME");
    if (!home) home = "/opt";
    char *path = (char *)malloc(1024);
    snprintf(path, 1024, "%s/artillery_calculator", home);
    return path;
#endif
}

int main(void) {
    printf("============================\n");
    printf("  Artillery Calculator GUI Installer (mac-first)\n");
    printf("============================\n\n");

    char *install_dir = default_install_dir();
    char *chosen = gui_select_folder("깔끔한 설치 위치를 선택하세요", install_dir);
    free(install_dir);
    if (!chosen) {
        fprintf(stderr, "설치 경로를 선택하지 못했습니다.\n");
        return 1;
    }

    int want_shortcut = gui_confirm("시작화면 바로가기", "바탕화면에 바로가기를 만들까요?", 1);

    printf("\n• 설치 경로: %s\n", chosen);
    printf("• 바로가기: %s\n", want_shortcut ? "예" : "아니오");

    if (!gui_confirm("설치 진행", "위 설정으로 설치를 진행할까요?", 1)) {
        printf("설치를 취소했습니다.\n");
        free(chosen);
        return 0;
    }

    if (mkdir_p(chosen) != 0) {
        fprintf(stderr, "설치 폴더를 만들 수 없습니다: %s\n", chosen);
        free(chosen);
        return 1;
    }

    if (access("cli_calculator", X_OK) != 0) {
        printf("cli_calculator 바이너리를 찾을 수 없습니다. 소스를 컴파일합니다...\n");
        if (!compile_cli()) {
            fprintf(stderr, "컴파일에 실패했습니다.\n");
            free(chosen);
            return 1;
        }
    }

    char dest_bin[1024];
    snprintf(dest_bin, sizeof(dest_bin), "%s/cli_calculator", chosen);
    if (copy_file("cli_calculator", dest_bin) != 0) {
        fprintf(stderr, "바이너리 복사에 실패했습니다.\n");
        free(chosen);
        return 1;
    }
    chmod(dest_bin, 0755);

    char dest_tables[1024];
    snprintf(dest_tables, sizeof(dest_tables), "%s/rangeTables", chosen);
    if (copy_range_tables(dest_tables) != 0) {
        fprintf(stderr, "레인지 테이블을 복사하지 못했습니다.\n");
        free(chosen);
        return 1;
    }

    if (create_launcher(chosen, want_shortcut) != 0) {
        fprintf(stderr, "런처 생성에 실패했습니다.\n");
        free(chosen);
        return 1;
    }

    show_summary(chosen, want_shortcut);
    free(chosen);
    return 0;
}
