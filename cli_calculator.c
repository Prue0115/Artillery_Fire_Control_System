#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "version.h"
#include <dirent.h>

#define MAX_ROWS 4000
#define MAX_TABLES 64
#define MAX_PATH 512
#define MAX_NAME 64

typedef struct {
    double range;
    double mill;
    double diff100m;
    double eta;
} RangeRow;

typedef struct {
    RangeRow rows[MAX_ROWS];
    size_t count;
    double min_range;
    double max_range;
} RangeTable;

static int cmp_range(const void *a, const void *b) {
    double ra = ((const RangeRow *)a)->range;
    double rb = ((const RangeRow *)b)->range;
    if (ra < rb) return -1;
    if (ra > rb) return 1;
    return 0;
}

typedef struct {
    char system[MAX_NAME];
    char trajectory[MAX_NAME];
    int charge;
    RangeTable table;
} TableInfo;

static void usage(void) {
    fprintf(stderr, "사용법: cli_calculator --system M109A6 --distance 5000 [--trajectory low|high] [--charge 3] [--altitude-delta 50] [--list]\n");
    fprintf(stderr, "- system, distance는 필수입니다.\n");
    fprintf(stderr, "- trajectory/charge를 생략하면 해당 시스템의 모든 표에서 범위 안에 들어오는 결과를 모두 출력합니다.\n");
    fprintf(stderr, "- --list로 로드 가능한 시스템/궤적/장약 조합을 확인할 수 있습니다.\n");
    fprintf(stderr, "- --version으로 현재 빌드 버전을 확인할 수 있습니다.\n");
}

static int parse_filename(const char *name, char *system, char *trajectory, int *charge) {
    char sys_buf[MAX_NAME];
    char traj_buf[MAX_NAME];
    int parsed_charge = -1;

    if (sscanf(name, "%63[^_]_rangeTable_%63[^_]_%d.csv", sys_buf, traj_buf, &parsed_charge) == 3) {
        strncpy(system, sys_buf, MAX_NAME);
        strncpy(trajectory, traj_buf, MAX_NAME);
        system[MAX_NAME - 1] = '\0';
        trajectory[MAX_NAME - 1] = '\0';
        *charge = parsed_charge;
        return 1;
    }
    return 0;
}

static int load_csv(const char *path, RangeTable *table) {
    FILE *fp = fopen(path, "r");
    if (!fp) {
        fprintf(stderr, "파일을 열 수 없습니다: %s\n", path);
        return -1;
    }

    char line[256];
    size_t idx = 0;

    // Skip header
    if (!fgets(line, sizeof(line), fp)) {
        fclose(fp);
        return -1;
    }

    while (fgets(line, sizeof(line), fp) && idx < MAX_ROWS) {
        char *token;
        double values[4];
        int col = 0;

        token = strtok(line, ",\n\r");
        while (token && col < 4) {
            values[col] = atof(token);
            token = strtok(NULL, ",\n\r");
            col++;
        }

        if (col >= 4) {
            table->rows[idx].range = values[0];
            table->rows[idx].mill = values[1];
            table->rows[idx].diff100m = values[2];
            table->rows[idx].eta = values[3];
            idx++;
        }
    }

    table->count = idx;
    if (table->count > 0) {
        // 데이터가 항상 정렬되어 있다는 보장은 없으므로 범위를 기준으로 정렬한다.
        qsort(table->rows, table->count, sizeof(RangeRow), cmp_range);
        table->min_range = table->rows[0].range;
        table->max_range = table->rows[table->count - 1].range;
    }
    fclose(fp);
    return 0;
}

static int supports_range(const RangeTable *table, double distance) {
    if (table->count == 0) return 0;
    double min = table->min_range;
    double max = table->max_range;
    return distance >= min && distance <= max;
}

static RangeRow interpolate(const RangeTable *table, double distance) {
    if (table->count == 0) {
        RangeRow empty = {0};
        return empty;
    }

    RangeRow prev = table->rows[0];
    for (size_t i = 1; i < table->count; i++) {
        RangeRow curr = table->rows[i];
        if (curr.range >= distance) {
            double span = curr.range - prev.range;
            double ratio = span == 0 ? 0.0 : (distance - prev.range) / span;

            RangeRow result;
            result.range = distance;
            result.mill = prev.mill + ratio * (curr.mill - prev.mill);
            result.diff100m = prev.diff100m + ratio * (curr.diff100m - prev.diff100m);
            result.eta = prev.eta + ratio * (curr.eta - prev.eta);
            return result;
        }
        prev = curr;
    }
    return table->rows[table->count - 1];
}

static int load_tables(const char *system_filter, const char *trajectory_filter, TableInfo *tables, size_t *count) {
    DIR *dir = opendir("rangeTables");
    if (!dir) {
        perror("rangeTables 디렉토리를 열 수 없습니다");
        return -1;
    }

    struct dirent *entry;
    size_t idx = 0;

    while ((entry = readdir(dir)) != NULL) {
        if (idx >= MAX_TABLES) break;
#ifdef DT_DIR
        if (entry->d_type == DT_DIR) continue;
#endif
        if (entry->d_name[0] == '.') continue;

        char system[MAX_NAME];
        char trajectory[MAX_NAME];
        int charge = -1;

        if (!parse_filename(entry->d_name, system, trajectory, &charge)) continue;
        if (system_filter && strcmp(system_filter, system) != 0) continue;
        if (trajectory_filter && strcmp(trajectory_filter, trajectory) != 0) continue;

        char path[MAX_PATH];
        snprintf(path, sizeof(path), "rangeTables/%s", entry->d_name);

        TableInfo info;
        memset(&info, 0, sizeof(info));
        strncpy(info.system, system, MAX_NAME - 1);
        strncpy(info.trajectory, trajectory, MAX_NAME - 1);
        info.charge = charge;

        if (load_csv(path, &info.table) == 0) {
            tables[idx++] = info;
        }
    }

    closedir(dir);
    *count = idx;
    if (idx == 0) {
        fprintf(stderr, "로드할 CSV가 없습니다. rangeTables 폴더에 사용자가 준비한 CSV를 넣어야 하며 프로그램이 생성하지 않습니다.\n");
        return -1;
    }
    return 0;
}

static void list_tables(const TableInfo *tables, size_t count) {
    printf("사용 가능한 레인지 테이블 목록:\n");
    for (size_t i = 0; i < count; i++) {
        printf("- %s / %s / charge %d\n", tables[i].system, tables[i].trajectory, tables[i].charge);
    }
}

static int print_results(const TableInfo *tables, size_t count, double distance, double altitude_delta) {
    int printed = 0;
    double overall_min = 1e9;
    double overall_max = -1e9;
    for (size_t i = 0; i < count; i++) {
        const TableInfo *info = &tables[i];
        if (info->table.count > 0) {
            if (info->table.min_range < overall_min) overall_min = info->table.min_range;
            if (info->table.max_range > overall_max) overall_max = info->table.max_range;
        }
        if (!supports_range(&info->table, distance)) {
            continue;
        }

        RangeRow row = interpolate(&info->table, distance);
        double mill_adjust = (altitude_delta / 100.0) * row.diff100m;
        double final_mill = row.mill + mill_adjust;

        printf("=== %s / %s / charge %d ===\n", info->system, info->trajectory, info->charge);
        printf("Distance: %.2f m\n", distance);
        printf("Altitude delta: %.2f m (사수-목표)\n", altitude_delta);
        printf("Base mill: %.2f\n", row.mill);
        printf("Diff per 100m: %.2f\n", row.diff100m);
        printf("Adjusted mill: %.2f\n", final_mill);
        printf("ETA: %.2f\n\n", row.eta);
        printed = 1;
    }
    if (!printed && overall_max >= 0) {
        fprintf(stderr, "입력한 거리 %.2f m가 지원 범위를 벗어났습니다. 가능한 범위: %.2f m ~ %.2f m\n", distance, overall_min, overall_max);
    }
    return printed;
}

int main(int argc, char *argv[]) {
    const char *system = NULL;
    const char *trajectory = NULL;
    int charge = -1;
    double distance = -1.0;
    double altitude_delta = 0.0;
    int list_only = 0;
    int show_version = 0;
    TableInfo *tables = NULL;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--system") == 0 && i + 1 < argc) {
            system = argv[++i];
        } else if (strcmp(argv[i], "--trajectory") == 0 && i + 1 < argc) {
            trajectory = argv[++i];
        } else if (strcmp(argv[i], "--charge") == 0 && i + 1 < argc) {
            charge = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--distance") == 0 && i + 1 < argc) {
            distance = atof(argv[++i]);
        } else if (strcmp(argv[i], "--altitude-delta") == 0 && i + 1 < argc) {
            altitude_delta = atof(argv[++i]);
        } else if (strcmp(argv[i], "--list") == 0) {
            list_only = 1;
        } else if (strcmp(argv[i], "--version") == 0) {
            show_version = 1;
        }
    }

    if (show_version) {
        printf("cli_calculator version %s\n", APP_VERSION);
        return 0;
    }

    if (!system) {
        usage();
        return 1;
    }

    tables = calloc(MAX_TABLES, sizeof(TableInfo));
    if (!tables) {
        fprintf(stderr, "메모리를 할당할 수 없습니다.\n");
        return 1;
    }

    size_t table_count = 0;

    if (load_tables(system, trajectory, tables, &table_count) != 0) {
        fprintf(stderr, "레인지 테이블을 찾을 수 없습니다. system/trajectory 값을 확인하세요.\n");
        free(tables);
        return 1;
    }

    if (list_only) {
        list_tables(tables, table_count);
        free(tables);
        return 0;
    }

    if (distance <= 0.0) {
        usage();
        free(tables);
        return 1;
    }

    // 특정 charge가 지정되면 해당 테이블만 필터링한다.
    if (charge >= 0) {
        TableInfo *filtered = calloc(MAX_TABLES, sizeof(TableInfo));
        if (!filtered) {
            fprintf(stderr, "메모리를 할당할 수 없습니다.\n");
            free(tables);
            return 1;
        }
        size_t filtered_count = 0;
        for (size_t i = 0; i < table_count; i++) {
            if (tables[i].charge == charge) {
                filtered[filtered_count++] = tables[i];
            }
        }
        if (filtered_count == 0) {
            fprintf(stderr, "지정한 장약(%d)에 해당하는 테이블이 없습니다.\n", charge);
            free(filtered);
            free(tables);
            return 1;
        }
        memcpy(tables, filtered, filtered_count * sizeof(TableInfo));
        table_count = filtered_count;
        free(filtered);
    }

    if (!print_results(tables, table_count, distance, altitude_delta)) {
        fprintf(stderr, "거리를 지원하는 테이블이 없습니다 (%.2f m).\n", distance);
        free(tables);
        return 1;
    }

    free(tables);
    return 0;
}
