#include "RangeTable.h"

#include <QCoreApplication>
#include <QDir>
#include <QTextStream>
#include <algorithm>
#include <cmath>

namespace {
QString rangeTableRoot() {
    const auto appDir = QCoreApplication::applicationDirPath();
    return appDir + "/rangeTables";
}

QHash<QString, QString> prefixMap() {
    return {
        {QStringLiteral("M109A6"), QStringLiteral("M109A6")},
        {QStringLiteral("M1129"), QStringLiteral("M1129")},
        {QStringLiteral("M119"), QStringLiteral("M119")},
        {QStringLiteral("RM-70"), QStringLiteral("RM70")},
        {QStringLiteral("siala"), QStringLiteral("siala")},
    };
}
}

RangeTable::RangeTable(QString system, QString trajectory, int charge)
    : m_system(std::move(system)), m_trajectory(std::move(trajectory)), m_charge(charge) {
    const auto prefix = filePrefixForSystem(m_system);
    m_path = QStringLiteral("%1/%2_rangeTable_%3_%4.csv").arg(rangeTableRoot(), prefix, m_trajectory).arg(m_charge);
    m_rows = loadRows();
}

bool RangeTable::isValid() const {
    return !m_rows.isEmpty();
}

bool RangeTable::supportsRange(double distance) const {
    if (m_rows.isEmpty()) {
        return false;
    }
    const auto minIt = std::min_element(m_rows.begin(), m_rows.end(), [](const auto &a, const auto &b) {
        return a.range < b.range;
    });
    const auto maxIt = std::max_element(m_rows.begin(), m_rows.end(), [](const auto &a, const auto &b) {
        return a.range < b.range;
    });
    return distance >= minIt->range && distance <= maxIt->range;
}

std::optional<RangeSolution> RangeTable::calculate(double distance, double altitudeDelta) const {
    if (!supportsRange(distance)) {
        return std::nullopt;
    }

    const auto neighbors = neighborRows(distance);
    if (neighbors.isEmpty()) {
        return std::nullopt;
    }

    const auto baseMill = interpolate(neighbors, distance, &RangeRow::mill);
    const auto diff100m = interpolate(neighbors, distance, &RangeRow::diff100m);
    const auto eta = interpolate(neighbors, distance, &RangeRow::eta);

    RangeSolution result;
    result.charge = m_charge;
    result.baseMill = baseMill;
    result.diff100m = diff100m;
    result.mill = baseMill + (altitudeDelta / 100.0) * diff100m;
    result.eta = eta;
    return result;
}

QString RangeTable::filePrefixForSystem(const QString &system) {
    const auto map = prefixMap();
    return map.value(system, system);
}

QVector<RangeRow> RangeTable::loadRows() const {
    QFile file(m_path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }

    QTextStream in(&file);
    const auto headerLine = in.readLine();
    const auto headers = headerLine.split(',');

    auto indexFor = [&](const QString &key) -> int {
        for (int i = 0; i < headers.size(); ++i) {
            if (headers[i].trimmed().compare(key, Qt::CaseInsensitive) == 0) {
                return i;
            }
        }
        return -1;
    };

    const int rangeIdx = indexFor("range");
    const int millIdx = indexFor("mill");
    const int diffIdx = indexFor("diff100m");
    const int etaIdx = indexFor("eta");

    QVector<RangeRow> rows;
    while (!in.atEnd()) {
        const auto line = in.readLine();
        if (line.trimmed().isEmpty()) {
            continue;
        }
        const auto columns = line.split(',');
        auto valueAt = [&](int idx) -> std::optional<double> {
            if (idx < 0 || idx >= columns.size()) {
                return std::nullopt;
            }
            bool ok = false;
            const auto number = columns[idx].trimmed().toDouble(&ok);
            if (!ok) {
                return std::nullopt;
            }
            return number;
        };

        auto range = valueAt(rangeIdx);
        auto mill = valueAt(millIdx);
        auto diff = valueAt(diffIdx);
        auto eta = valueAt(etaIdx);
        if (range && mill && diff && eta) {
            rows.push_back(RangeRow{*range, *mill, *diff, *eta});
        }
    }

    std::sort(rows.begin(), rows.end(), [](const auto &a, const auto &b) { return a.range < b.range; });
    return rows;
}

QVector<RangeRow> RangeTable::neighborRows(double distance) const {
    if (m_rows.isEmpty()) {
        return {};
    }

    QVector<RangeRow> neighbors;
    const auto ranges = [&]() {
        QVector<double> vals;
        vals.reserve(m_rows.size());
        for (const auto &row : m_rows) {
            vals.push_back(row.range);
        }
        return vals;
    }();

    auto it = std::lower_bound(ranges.begin(), ranges.end(), distance);
    int idx = static_cast<int>(it - ranges.begin());

    if (idx > 0) {
        neighbors.push_back(m_rows[idx - 1]);
    }
    if (idx < m_rows.size()) {
        neighbors.push_back(m_rows[idx]);
    }

    QVector<RangeRow> remaining;
    if (idx - 2 >= 0) {
        remaining.push_back(m_rows[idx - 2]);
    }
    if (idx + 1 < m_rows.size()) {
        remaining.push_back(m_rows[idx + 1]);
    }

    std::sort(remaining.begin(), remaining.end(), [distance](const auto &a, const auto &b) {
        return std::abs(a.range - distance) < std::abs(b.range - distance);
    });

    for (const auto &row : remaining) {
        if (std::none_of(neighbors.begin(), neighbors.end(), [&](const RangeRow &r) { return r.range == row.range; })) {
            neighbors.push_back(row);
        }
        if (neighbors.size() >= 3) {
            break;
        }
    }

    std::sort(neighbors.begin(), neighbors.end(), [](const auto &a, const auto &b) { return a.range < b.range; });
    return neighbors;
}

double RangeTable::interpolate(const QVector<RangeRow> &neighbors, double distance, double (RangeRow::*field)) const {
    if (neighbors.isEmpty()) {
        return 0.0;
    }
    if (neighbors.size() == 1) {
        return neighbors.front().*field;
    }
    if (neighbors.size() == 2 || neighbors[0].range == neighbors[1].range) {
        const auto &lower = neighbors[0];
        const auto &upper = neighbors[1];
        if (upper.range == lower.range) {
            return lower.*field;
        }
        const auto ratio = (distance - lower.range) / (upper.range - lower.range);
        return lower.*field + ratio * (upper.*field - lower.*field);
    }

    const auto &x0 = neighbors[0].range;
    const auto &x1 = neighbors[1].range;
    const auto &x2 = neighbors[2].range;

    const double y0 = neighbors[0].*field;
    const double y1 = neighbors[1].*field;
    const double y2 = neighbors[2].*field;

    auto basis = [](double x, double a, double b) {
        return (x - a) / (b - a);
    };

    const auto t0 = basis(distance, x1, x0) * basis(distance, x2, x0);
    const auto t1 = basis(distance, x0, x1) * basis(distance, x2, x1);
    const auto t2 = basis(distance, x0, x2) * basis(distance, x1, x2);
    return y0 * t0 + y1 * t1 + y2 * t2;
}

QVector<int> availableCharges(const QString &system, const QString &trajectory) {
    const auto prefix = RangeTable::filePrefixForSystem(system);
    const QDir dir(rangeTableRoot());
    const QString pattern = QStringLiteral("%1_rangeTable_%2_").arg(prefix, trajectory);
    QVector<int> charges;

    const auto entries = dir.entryList(QStringList() << QStringLiteral("%1*.csv").arg(pattern), QDir::Files);
    for (const auto &entry : entries) {
        auto suffix = entry;
        suffix.chop(4); // remove .csv
        suffix.remove(0, pattern.size());
        bool ok = false;
        const int charge = suffix.toInt(&ok);
        if (ok) {
            charges.push_back(charge);
        }
    }
    std::sort(charges.begin(), charges.end());
    charges.erase(std::unique(charges.begin(), charges.end()), charges.end());
    return charges;
}

QHash<QString, SystemTrajectoryOverride> trajectoryOverrides() {
    return {
        {QStringLiteral("M1129"), {{}, {0, 1, 2}}},
    };
}
