using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using AFCS.Wpf.Services;

namespace AFCS.Wpf;

public partial class MainWindow : Window
{
    private readonly string _baseDirectory;
    private readonly List<string> _systems = new() { "M109A6", "M1129", "M119", "RM-70", "siala" };

    public MainWindow()
    {
        InitializeComponent();
        _baseDirectory = ResolveBaseDirectory();
        EquipmentCombo.ItemsSource = _systems;
        EquipmentCombo.SelectedIndex = 0;
        DistanceBox.Text = "1000";
        MyAltitudeBox.Text = "0";
        TargetAltitudeBox.Text = "0";
        RefreshChargeLists();
    }

    private void OnEquipmentChanged(object sender, SelectionChangedEventArgs e)
    {
        RefreshChargeLists();
    }

    private void RefreshChargeLists()
    {
        var system = EquipmentCombo.SelectedItem as string ?? _systems.First();
        var (low, high) = RangeTableService.ResolveCharges(system, _baseDirectory);
        LowChargeCombo.ItemsSource = low;
        HighChargeCombo.ItemsSource = high;
        LowChargeCombo.SelectedIndex = low.Any() ? 0 : -1;
        HighChargeCombo.SelectedIndex = high.Any() ? 0 : -1;
    }

    private void OnCalculateClicked(object sender, RoutedEventArgs e)
    {
        if (!TryParseInputs(out var distance, out var myAlt, out var targetAlt))
        {
            MessageBox.Show(this, "숫자만 입력하세요.", "입력 오류", MessageBoxButton.OK, MessageBoxImage.Error);
            return;
        }

        var altitudeDelta = myAlt - targetAlt;
        AltitudeDelta.Text = $"고도 차이(사수-목표): {altitudeDelta:+0.0} m";
        var system = EquipmentCombo.SelectedItem as string ?? _systems.First();

        UpdateSolutions(distance, altitudeDelta, system, "low", LowChargeCombo, LowResults, LowStatus);
        UpdateSolutions(distance, altitudeDelta, system, "high", HighChargeCombo, HighResults, HighStatus);
    }

    private void UpdateSolutions(
        double distance,
        double altitudeDelta,
        string system,
        string trajectory,
        ComboBox chargeSelector,
        ItemsControl resultsControl,
        TextBlock statusBlock)
    {
        int? manualCharge = chargeSelector.SelectedItem is int value ? value : null;
        IReadOnlyList<int>? charges = manualCharge.HasValue ? new List<int> { manualCharge.Value } : null;
        var results = RangeTableService.FindSolutions(distance, altitudeDelta, trajectory, system, _baseDirectory, charges: charges);

        resultsControl.ItemsSource = results.Select(r => new
        {
            r.Charge,
            Mill = r.Mill.ToString("F2"),
            Eta = r.Eta.ToString("F1"),
            r.BaseMill,
            r.Diff100m
        }).ToList();

        statusBlock.Text = results.Any()
            ? string.Empty
            : charges == null
                ? "선택한 사거리 데이터가 없습니다. rangeTables를 확인하세요."
                : "선택된 장약에 대한 사거리 데이터가 없습니다.";
    }

    private bool TryParseInputs(out double distance, out double myAlt, out double targetAlt)
    {
        distance = myAlt = targetAlt = 0;
        var styles = System.Globalization.NumberStyles.Any;
        var culture = System.Globalization.CultureInfo.InvariantCulture;
        return double.TryParse(DistanceBox.Text, styles, culture, out distance)
            && double.TryParse(MyAltitudeBox.Text, styles, culture, out myAlt)
            && double.TryParse(TargetAltitudeBox.Text, styles, culture, out targetAlt);
    }

    private static string ResolveBaseDirectory()
    {
        var dir = AppContext.BaseDirectory;
        while (!string.IsNullOrWhiteSpace(dir))
        {
            if (Directory.Exists(Path.Combine(dir, "rangeTables")))
            {
                return dir;
            }

            var parent = Directory.GetParent(dir);
            if (parent == null || parent.FullName == dir)
            {
                break;
            }

            dir = parent.FullName;
        }

        return AppContext.BaseDirectory;
    }
}
