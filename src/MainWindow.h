#pragma once

#include <QDateTime>
#include <QMainWindow>
#include <QLabel>
#include <QTableWidget>
#include <QVector>

#include "RangeTable.h"

QT_BEGIN_NAMESPACE
namespace Ui { class MainWindow; }
QT_END_NAMESPACE

struct LogEntry {
    QDateTime timestamp;
    QString system;
    double myAlt{0.0};
    double targetAlt{0.0};
    double distance{0.0};
    QVector<RangeSolution> low;
    QVector<RangeSolution> high;
};

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow() override;

private slots:
    void calculate();
    void refreshLog();

private:
    void setupTables();
    void updateTable(QTableWidget *table, QLabel *statusLabel, const QVector<RangeSolution> &solutions, const QString &message);
    QVector<RangeSolution> findSolutions(const QString &trajectory, const QVector<int> &charges, double distance, double altitudeDelta) const;
    void appendLog(const QString &system, double myAlt, double targetAlt, double distance, const QVector<RangeSolution> &low, const QVector<RangeSolution> &high);
    QString formatSolution(const RangeSolution &solution) const;

    Ui::MainWindow *ui;
    QVector<LogEntry> m_logs;
};
