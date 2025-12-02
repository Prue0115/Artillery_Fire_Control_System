#pragma once

#include <QFile>
#include <QHash>
#include <QVector>
#include <QString>
#include <QStringList>
#include <optional>

struct RangeRow {
    double range{0.0};
    double mill{0.0};
    double diff100m{0.0};
    double eta{0.0};
};

struct RangeSolution {
    int charge{0};
    double mill{0.0};
    double eta{0.0};
    double baseMill{0.0};
    double diff100m{0.0};
};

class RangeTable {
public:
    RangeTable(QString system, QString trajectory, int charge);

    bool isValid() const;
    bool supportsRange(double distance) const;
    std::optional<RangeSolution> calculate(double distance, double altitudeDelta) const;
    QString path() const { return m_path; }

    static QString filePrefixForSystem(const QString &system);

private:
    QVector<RangeRow> loadRows() const;
    QVector<RangeRow> neighborRows(double distance) const;
    double interpolate(const QVector<RangeRow> &neighbors, double distance, double (RangeRow::*field)) const;

    QString m_system;
    QString m_trajectory;
    int m_charge{0};
    QString m_path;
    QVector<RangeRow> m_rows;
};

QVector<int> availableCharges(const QString &system, const QString &trajectory);

struct SystemTrajectoryOverride {
    QVector<int> low;
    QVector<int> high;
};

QHash<QString, SystemTrajectoryOverride> trajectoryOverrides();
