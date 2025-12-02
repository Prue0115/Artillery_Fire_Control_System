#include "MainWindow.h"
#include "ui_MainWindow.h"

#include <QMessageBox>
#include <QScopedPointer>
#include <algorithm>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent), ui(new Ui::MainWindow) {
    ui->setupUi(this);
    setupTables();

    ui->systemCombo->addItems({"M109A6", "M1129", "M119", "RM-70", "siala"});
    ui->systemCombo->setCurrentText("M109A6");

    connect(ui->calculateButton, &QPushButton::clicked, this, &MainWindow::calculate);
    connect(ui->logFilterCombo, &QComboBox::currentTextChanged, this, &MainWindow::refreshLog);
}

MainWindow::~MainWindow() {
    delete ui;
}

void MainWindow::setupTables() {
    auto configureTable = [](QTableWidget *table) {
        table->setColumnCount(3);
        table->setHorizontalHeaderLabels({"CH", "MILL", "ETA"});
        table->horizontalHeader()->setStretchLastSection(true);
        table->verticalHeader()->setVisible(false);
        table->setEditTriggers(QAbstractItemView::NoEditTriggers);
        table->setSelectionMode(QAbstractItemView::NoSelection);
        table->setRowCount(3);
        for (int row = 0; row < 3; ++row) {
            for (int col = 0; col < 3; ++col) {
                table->setItem(row, col, new QTableWidgetItem("—"));
            }
        }
    };

    configureTable(ui->lowTable);
    configureTable(ui->highTable);

    ui->logTable->setColumnCount(6);
    ui->logTable->setHorizontalHeaderLabels({"시간", "장비", "My ALT", "Target ALT", "Distance", "결과"});
    ui->logTable->horizontalHeader()->setStretchLastSection(true);
    ui->logTable->verticalHeader()->setVisible(false);
    ui->logTable->setEditTriggers(QAbstractItemView::NoEditTriggers);
    ui->logTable->setSelectionBehavior(QAbstractItemView::SelectRows);
    ui->logTable->setSelectionMode(QAbstractItemView::SingleSelection);
}

void MainWindow::calculate() {
    bool myOk = false, targetOk = false, distanceOk = false;
    const double myAlt = ui->myAltEdit->text().toDouble(&myOk);
    const double targetAlt = ui->targetAltEdit->text().toDouble(&targetOk);
    const double distance = ui->distanceEdit->text().toDouble(&distanceOk);

    if (!myOk || !targetOk || !distanceOk) {
        QMessageBox::warning(this, tr("입력 오류"), tr("모든 필드에 숫자를 입력하세요."));
        return;
    }

    const double altitudeDelta = myAlt - targetAlt;
    const auto system = ui->systemCombo->currentText();

    const auto overrides = trajectoryOverrides().value(system);
    const auto lowCharges = overrides.low.isEmpty() ? availableCharges(system, "low") : overrides.low;
    const auto highCharges = overrides.high.isEmpty() ? availableCharges(system, "high") : overrides.high;

    const auto lowSolutions = findSolutions("low", lowCharges, distance, altitudeDelta);
    const auto highSolutions = findSolutions("high", highCharges, distance, altitudeDelta);

    const auto lowMessage = lowCharges.isEmpty() ? tr("저각 데이터가 없습니다.") : QString();
    const auto highMessage = highCharges.isEmpty() ? tr("고각 데이터가 없습니다.") : QString();

    updateTable(ui->lowTable, ui->lowStatusLabel, lowSolutions, lowMessage);
    updateTable(ui->highTable, ui->highStatusLabel, highSolutions, highMessage);

    appendLog(system, myAlt, targetAlt, distance, lowSolutions, highSolutions);
}

void MainWindow::refreshLog() {
    const auto filter = ui->logFilterCombo->currentText();
    ui->logTable->setRowCount(0);

    QVector<LogEntry> filtered = m_logs;
    if (filter != "전체") {
        filtered.erase(std::remove_if(filtered.begin(), filtered.end(), [&](const LogEntry &entry) {
            return entry.system != filter;
        }), filtered.end());
    }

    std::sort(filtered.begin(), filtered.end(), [](const auto &a, const auto &b) {
        return a.timestamp > b.timestamp;
    });

    ui->logTable->setRowCount(filtered.size());
    for (int row = 0; row < filtered.size(); ++row) {
        const auto &entry = filtered[row];
        const auto timestamp = entry.timestamp.toString("hh:mm:ss");
        ui->logTable->setItem(row, 0, new QTableWidgetItem(timestamp));
        ui->logTable->setItem(row, 1, new QTableWidgetItem(entry.system));
        ui->logTable->setItem(row, 2, new QTableWidgetItem(QString::number(entry.myAlt)));
        ui->logTable->setItem(row, 3, new QTableWidgetItem(QString::number(entry.targetAlt)));
        ui->logTable->setItem(row, 4, new QTableWidgetItem(QString::number(entry.distance)));

        QStringList summaries;
        if (!entry.low.isEmpty()) {
            summaries << tr("LOW %1").arg(formatSolution(entry.low.first()));
        }
        if (!entry.high.isEmpty()) {
            summaries << tr("HIGH %1").arg(formatSolution(entry.high.first()));
        }
        ui->logTable->setItem(row, 5, new QTableWidgetItem(summaries.join(" | ")));
    }

    ui->logTable->resizeColumnsToContents();
}

void MainWindow::updateTable(QTableWidget *table, QLabel *statusLabel, const QVector<RangeSolution> &solutions, const QString &message) {
    for (int row = 0; row < table->rowCount(); ++row) {
        for (int col = 0; col < table->columnCount(); ++col) {
            table->item(row, col)->setText("—");
        }
    }

    if (!message.isEmpty()) {
        statusLabel->setText(message);
    } else if (solutions.isEmpty()) {
        statusLabel->setText(tr("지원 범위 밖입니다."));
    } else {
        statusLabel->clear();
    }

    const int limit = std::min(static_cast<int>(solutions.size()), table->rowCount());
    for (int i = 0; i < limit; ++i) {
        const auto &solution = solutions[i];
        table->item(i, 0)->setText(QString::number(solution.charge));
        table->item(i, 1)->setText(QString::number(solution.mill, 'f', 2));
        table->item(i, 2)->setText(QString::number(solution.eta, 'f', 1));
    }
}

QVector<RangeSolution> MainWindow::findSolutions(const QString &trajectory, const QVector<int> &charges, double distance, double altitudeDelta) const {
    QVector<RangeSolution> solutions;
    const auto system = ui->systemCombo->currentText();

    for (int charge : charges) {
        RangeTable table(system, trajectory, charge);
        if (!table.isValid()) {
            continue;
        }
        const auto result = table.calculate(distance, altitudeDelta);
        if (result) {
            solutions.push_back(*result);
        }
        if (solutions.size() >= 3) {
            break;
        }
    }
    return solutions;
}

void MainWindow::appendLog(const QString &system, double myAlt, double targetAlt, double distance, const QVector<RangeSolution> &low, const QVector<RangeSolution> &high) {
    m_logs.push_back({QDateTime::currentDateTime(), system, myAlt, targetAlt, distance, low, high});
    refreshLog();
}

QString MainWindow::formatSolution(const RangeSolution &solution) const {
    return tr("CH %1 / %2 mil / ETA %3s").arg(solution.charge).arg(QString::number(solution.mill, 'f', 2)).arg(QString::number(solution.eta, 'f', 1));
}
