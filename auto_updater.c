#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "gui_dialogs.h"
#include "version.h"

#ifndef P_tmpdir
#define P_tmpdir "/tmp"
#endif

static void print_usage(void) {
    fprintf(stderr, "사용법: auto_updater --manifest <URL> [--binary ./cli_calculator] [--download-dir /tmp] [--yes]\n");
    fprintf(stderr, "- manifest: update.json의 경로 혹은 URL\n");
    fprintf(stderr, "- binary: 덮어쓸 실행 파일 경로 (기본: ./cli_calculator)\n");
    fprintf(stderr, "- download-dir: 새 파일을 임시 저장할 경로 (기본: 시스템 임시 폴더)\n");
    fprintf(stderr, "- --yes: 확인 없이 자동 교체\n");
}

static int compare_versions(const char *a, const char *b) {
    int ma = 0, mb = 0, pa = 0, pb = 0, ca = 0, cb = 0;
    sscanf(a, "%d.%d.%d", &ma, &pa, &ca);
    sscanf(b, "%d.%d.%d", &mb, &pb, &cb);
    if (ma != mb) return (ma > mb) ? 1 : -1;
    if (pa != pb) return (pa > pb) ? 1 : -1;
    if (ca != cb) return (ca > cb) ? 1 : -1;
    return 0;
}

static char *read_all(FILE *fp) {
    size_t cap = 4096;
    size_t len = 0;
    char *buf = (char *)malloc(cap);
    if (!buf) return NULL;
    int ch;
    while ((ch = fgetc(fp)) != EOF) {
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

static char *fetch_manifest(const char *url) {
    char command[2048];
    snprintf(command, sizeof(command), "curl -Ls --fail --retry 2 --retry-delay 1 '%s'", url);
    FILE *fp = popen(command, "r");
    if (!fp) return NULL;
    char *json = read_all(fp);
    pclose(fp);
    return json;
}

static int extract_json_string(const char *json, const char *key, char *out, size_t out_size) {
    char pattern[128];
    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    const char *pos = strstr(json, pattern);
    if (!pos) return 0;
    pos = strchr(pos, ':');
    if (!pos) return 0;
    pos++;
    while (*pos == ' ' || *pos == '\t') pos++;
    if (*pos == '"') {
        pos++;
        size_t i = 0;
        while (*pos && *pos != '"' && i + 1 < out_size) {
            out[i++] = *pos++;
        }
        out[i] = '\0';
        return 1;
    }
    return 0;
}

static int download_file(const char *url, const char *dest_path) {
    char command[2048];
    snprintf(command, sizeof(command), "curl -L --fail --retry 2 --retry-delay 1 -o '%s' '%s'", dest_path, url);
    int rc = system(command);
    return rc == 0;
}

static int ensure_dir(const char *path) {
    struct stat st;
    if (stat(path, &st) == 0) {
        return S_ISDIR(st.st_mode) ? 0 : -1;
    }
    return mkdir(path, 0755);
}

static int replace_binary(const char *tmp_path, const char *target_path) {
    char backup[1024];
    snprintf(backup, sizeof(backup), "%s.bak", target_path);
    remove(backup);
    rename(target_path, backup);
    remove(target_path);
    if (rename(tmp_path, target_path) != 0) {
        fprintf(stderr, "새 바이너리로 교체하지 못했습니다: %s -> %s (%s)\n", tmp_path, target_path, strerror(errno));
        rename(backup, target_path);
        return -1;
    }
    chmod(target_path, 0755);
    return 0;
}

int main(int argc, char **argv) {
    const char *manifest_url = NULL;
    const char *binary_path = "./cli_calculator";
    const char *download_dir = P_tmpdir;
    int auto_yes = 0;

    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--manifest") == 0 && i + 1 < argc) {
            manifest_url = argv[++i];
        } else if (strcmp(argv[i], "--binary") == 0 && i + 1 < argc) {
            binary_path = argv[++i];
        } else if (strcmp(argv[i], "--download-dir") == 0 && i + 1 < argc) {
            download_dir = argv[++i];
        } else if (strcmp(argv[i], "--yes") == 0) {
            auto_yes = 1;
        }
    }

    if (!manifest_url) {
        print_usage();
        return 1;
    }

    if (ensure_dir(download_dir) != 0) {
        fprintf(stderr, "임시 경로를 준비하지 못했습니다: %s\n", download_dir);
        return 1;
    }

    printf("현재 버전: %s\n", APP_VERSION);
    printf("메타데이터를 확인하는 중: %s\n", manifest_url);
    char *manifest = fetch_manifest(manifest_url);
    if (!manifest) {
        fprintf(stderr, "메타데이터를 가져오지 못했습니다. curl이 설치되어 있는지 확인하세요.\n");
        return 1;
    }

    char remote_version[64] = {0};
    char remote_url[1024] = {0};
    if (!extract_json_string(manifest, "version", remote_version, sizeof(remote_version)) ||
        !extract_json_string(manifest, "url", remote_url, sizeof(remote_url))) {
        fprintf(stderr, "update.json에서 버전/URL을 읽을 수 없습니다.\n");
        free(manifest);
        return 1;
    }
    free(manifest);

    int cmp = compare_versions(remote_version, APP_VERSION);
    if (cmp <= 0) {
        printf("이미 최신 버전입니다 (remote %s).\n", remote_version);
        return 0;
    }

    printf("새 버전 %s이 감지되었습니다.\n", remote_version);
    if (!auto_yes) {
        int proceed = gui_confirm("업데이트", "업데이트를 다운로드하여 교체할까요?", 1);
        if (!proceed) {
            printf("업데이트를 취소했습니다.\n");
            return 0;
        }
    }

    char tmp_path[1024];
    snprintf(tmp_path, sizeof(tmp_path), "%s/cli_calculator.new", download_dir);
    printf("다운로드: %s -> %s\n", remote_url, tmp_path);
    if (!download_file(remote_url, tmp_path)) {
        fprintf(stderr, "다운로드에 실패했습니다. curl이 인터넷에 접근 가능한지 확인하세요.\n");
        return 1;
    }

    printf("기존 바이너리를 교체합니다: %s\n", binary_path);
    if (replace_binary(tmp_path, binary_path) != 0) {
        remove(tmp_path);
        return 1;
    }

    printf("업데이트 완료! 새 버전: %s\n", remote_version);
    return 0;
}
