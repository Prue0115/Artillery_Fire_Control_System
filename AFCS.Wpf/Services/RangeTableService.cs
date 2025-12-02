using System.Globalization;
using System.IO;
using System.Linq;

namespace AFCS.Wpf.Services;

public record RangeTableRow(double Range, double Mill, double Diff100m, double Eta);

public record CalculationResult(int Charge, double Mill, double Eta, double BaseMill, double Diff100m);

public static class RangeTableService
{
    private static readonly Dictionary<string, string> SystemFilePrefix = new()
    {
        ["M109A6"] = "M109A6",
        ["M1129"] = "M1129",
        ["M119"] = "M119",
        ["RM-70"] = "RM70",
        ["siala"] = "siala"
    };

    private static readonly Dictionary<string, Dictionary<string, IReadOnlyList<int>>> SystemTrajectoryCharges = new()
    {
        ["M1129"] = new Dictionary<string, IReadOnlyList<int>>
        {
            ["low"] = Array.Empty<int>(),
            ["high"] = new List<int> { 0, 1, 2 }
        }
    };

    public static IReadOnlyList<int> AvailableCharges(string system, string trajectory, string baseDirectory)
    {
        var prefix = SystemFilePrefix.GetValueOrDefault(system, system);
        var pattern = $"{prefix}_rangeTable_{trajectory}_";
        var directory = Path.Combine(baseDirectory, "rangeTables");
        if (!Directory.Exists(directory))
        {
            return Array.Empty<int>();
        }

        return Directory.EnumerateFiles(directory, $"{pattern}*.csv")
            .Select(Path.GetFileNameWithoutExtension)
            .Where(name => name != null && name.StartsWith(pattern, StringComparison.OrdinalIgnoreCase))
            .Select(name => name![pattern.Length..])
            .Where(suffix => int.TryParse(suffix, out _))
            .Select(int.Parse)
            .Distinct()
            .OrderBy(v => v)
            .ToList();
    }

    public static IReadOnlyList<CalculationResult> FindSolutions(
        double distance,
        double altitudeDelta,
        string trajectory,
        string system,
        string baseDirectory,
        int limit = 3,
        IReadOnlyList<int>? charges = null)
    {
        var rows = new List<CalculationResult>();
        var resolvedCharges = charges ?? AvailableCharges(system, trajectory, baseDirectory);
        if (!resolvedCharges.Any())
        {
            return rows;
        }

        foreach (var charge in resolvedCharges)
        {
            var table = LoadRangeTable(system, trajectory, charge, baseDirectory);
            if (table.Count == 0 || !SupportsRange(table, distance))
            {
                continue;
            }

            var calculation = Calculate(table, distance, altitudeDelta, charge);
            if (calculation != null)
            {
                rows.Add(calculation.Value);
            }

            if (rows.Count >= limit)
            {
                break;
            }
        }

        return rows;
    }

    private static CalculationResult? Calculate(
        IReadOnlyList<RangeTableRow> rows,
        double distance,
        double altitudeDelta,
        int charge)
    {
        try
        {
            var baseMill = Interpolate(rows, distance, r => r.Mill);
            var diff100m = Interpolate(rows, distance, r => r.Diff100m);
            var eta = Interpolate(rows, distance, r => r.Eta);
            var millAdjust = (altitudeDelta / 100.0) * diff100m;
            var finalMill = baseMill + millAdjust;
            return new CalculationResult(charge, finalMill, eta, baseMill, diff100m);
        }
        catch (InvalidOperationException)
        {
            return null;
        }
    }

    private static IReadOnlyList<RangeTableRow> LoadRangeTable(string system, string trajectory, int charge, string baseDirectory)
    {
        var prefix = SystemFilePrefix.GetValueOrDefault(system, system);
        var filename = $"{prefix}_rangeTable_{trajectory}_{charge}.csv";
        var path = Path.Combine(baseDirectory, "rangeTables", filename);
        if (!File.Exists(path))
        {
            return Array.Empty<RangeTableRow>();
        }

        var rows = new List<RangeTableRow>();
        using var reader = new StreamReader(path);
        string? headerLine = reader.ReadLine();
        if (headerLine == null)
        {
            return rows;
        }

        var headers = headerLine.Split(',').Select(h => h.Trim()).ToArray();
        int rangeIdx = Array.FindIndex(headers, h => string.Equals(h, "range", StringComparison.OrdinalIgnoreCase));
        int millIdx = Array.FindIndex(headers, h => string.Equals(h, "mill", StringComparison.OrdinalIgnoreCase));
        int diffIdx = Array.FindIndex(headers, h => string.Equals(h, "diff100m", StringComparison.OrdinalIgnoreCase));
        int etaIdx = Array.FindIndex(headers, h => string.Equals(h, "eta", StringComparison.OrdinalIgnoreCase));

        string? line;
        while ((line = reader.ReadLine()) != null)
        {
            var parts = line.Split(',');
            if (!TryParse(parts, rangeIdx, out double range) ||
                !TryParse(parts, millIdx, out double mill) ||
                !TryParse(parts, diffIdx, out double diff) ||
                !TryParse(parts, etaIdx, out double eta))
            {
                continue;
            }

            rows.Add(new RangeTableRow(range, mill, diff, eta));
        }

        return rows.OrderBy(r => r.Range).ToList();
    }

    private static bool TryParse(string[] parts, int index, out double value)
    {
        value = default;
        if (index < 0 || index >= parts.Length)
        {
            return false;
        }

        return double.TryParse(parts[index], NumberStyles.Any, CultureInfo.InvariantCulture, out value);
    }

    private static bool SupportsRange(IReadOnlyList<RangeTableRow> rows, double distance)
    {
        if (rows.Count == 0)
        {
            return false;
        }

        var min = rows.Min(r => r.Range);
        var max = rows.Max(r => r.Range);
        return distance >= min && distance <= max;
    }

    private static double Interpolate(
        IReadOnlyList<RangeTableRow> rows,
        double distance,
        Func<RangeTableRow, double> selector)
    {
        var neighbors = NeighborRows(rows, distance).ToList();
        if (neighbors.Count == 0)
        {
            throw new InvalidOperationException("No rows available for interpolation.");
        }

        if (neighbors.Count == 1)
        {
            return selector(neighbors[0]);
        }

        if (neighbors.Count == 2 || Math.Abs(neighbors[0].Range - neighbors[1].Range) < double.Epsilon)
        {
            var lower = neighbors[0];
            var upper = neighbors[1];
            if (Math.Abs(upper.Range - lower.Range) < double.Epsilon)
            {
                return selector(lower);
            }

            var ratio = (distance - lower.Range) / (upper.Range - lower.Range);
            return selector(lower) + ratio * (selector(upper) - selector(lower));
        }

        var x0 = neighbors[0].Range;
        var x1 = neighbors[1].Range;
        var x2 = neighbors[2].Range;
        var y0 = selector(neighbors[0]);
        var y1 = selector(neighbors[1]);
        var y2 = selector(neighbors[2]);

        double Basis(double x, double a, double b) => Math.Abs(b - a) < double.Epsilon ? 0.0 : (x - a) / (b - a);

        var t0 = Basis(distance, x1, x0) * Basis(distance, x2, x0);
        var t1 = Basis(distance, x0, x1) * Basis(distance, x2, x1);
        var t2 = Basis(distance, x0, x2) * Basis(distance, x1, x2);

        return y0 * t0 + y1 * t1 + y2 * t2;
    }

    private static IEnumerable<RangeTableRow> NeighborRows(IReadOnlyList<RangeTableRow> rows, double distance)
    {
        var ordered = rows.OrderBy(r => r.Range).ToList();
        var idx = ordered.FindIndex(r => r.Range >= distance);
        idx = idx < 0 ? ordered.Count : idx;

        var neighbors = new List<RangeTableRow>();
        if (idx > 0)
        {
            neighbors.Add(ordered[idx - 1]);
        }
        if (idx < ordered.Count)
        {
            neighbors.Add(ordered[idx]);
        }

        var remaining = new List<RangeTableRow>();
        if (idx - 2 >= 0)
        {
            remaining.Add(ordered[idx - 2]);
        }
        if (idx + 1 < ordered.Count)
        {
            remaining.Add(ordered[idx + 1]);
        }

        remaining = remaining.OrderBy(r => Math.Abs(r.Range - distance)).ToList();
        foreach (var row in remaining)
        {
            if (neighbors.Any(n => Math.Abs(n.Range - row.Range) < double.Epsilon))
            {
                continue;
            }

            neighbors.Add(row);
            if (neighbors.Count >= 3)
            {
                break;
            }
        }

        return neighbors.OrderBy(r => r.Range);
    }

    public static (IReadOnlyList<int> lowCharges, IReadOnlyList<int> highCharges) ResolveCharges(string system, string baseDirectory)
    {
        var overrides = SystemTrajectoryCharges.GetValueOrDefault(system);
        IReadOnlyList<int>? low = overrides != null && overrides.TryGetValue("low", out var l) && l.Any() ? l : null;
        IReadOnlyList<int>? high = overrides != null && overrides.TryGetValue("high", out var h) && h.Any() ? h : null;

        low ??= AvailableCharges(system, "low", baseDirectory);
        high ??= AvailableCharges(system, "high", baseDirectory);
        return (low, high);
    }
}
