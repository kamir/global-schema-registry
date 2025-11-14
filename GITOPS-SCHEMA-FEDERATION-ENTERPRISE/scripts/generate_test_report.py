#!/usr/bin/env python3
"""
Generate comprehensive HTML test reports for compatibility testing.

This script generates beautiful, interactive HTML reports from test results,
including compatibility matrices, test results, and visualizations.
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Try to import from project
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from tests.test_compatibility_transitions import (
        COMPATIBILITY_TRANSITIONS,
        TestSchemas
    )
except ImportError:
    print("Warning: Could not import test data. Using fallback.")
    COMPATIBILITY_TRANSITIONS = []


class TestReportGenerator:
    """Generate comprehensive test reports in HTML format."""

    def __init__(self, output_dir: str = "test-reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_html_report(
        self,
        test_results: Optional[Dict] = None,
        compatibility_data: Optional[List] = None
    ) -> str:
        """Generate comprehensive HTML report."""

        if compatibility_data is None:
            compatibility_data = COMPATIBILITY_TRANSITIONS

        html = self._build_html_template(test_results, compatibility_data)

        output_file = self.output_dir / "compatibility-report.html"
        with open(output_file, 'w') as f:
            f.write(html)

        return str(output_file)

    def _build_html_template(
        self,
        test_results: Optional[Dict],
        compatibility_data: List
    ) -> str:
        """Build complete HTML report template."""

        # Build transition matrix
        modes = [
            "NONE",
            "BACKWARD",
            "BACKWARD_TRANSITIVE",
            "FORWARD",
            "FORWARD_TRANSITIVE",
            "FULL",
            "FULL_TRANSITIVE"
        ]

        # Create matrix lookup
        matrix = {}
        for from_mode in modes:
            matrix[from_mode] = {}
            for to_mode in modes:
                if from_mode == to_mode:
                    matrix[from_mode][to_mode] = "N/A"
                else:
                    # Find in compatibility data
                    transition = next(
                        (t for t in compatibility_data
                         if t[0] == from_mode and t[1] == to_mode),
                        None
                    )
                    if transition:
                        matrix[from_mode][to_mode] = transition[2]  # risk_level
                    else:
                        matrix[from_mode][to_mode] = "UNKNOWN"

        # Count statistics
        stats = {
            "SAFE": 0,
            "RISKY": 0,
            "DANGEROUS": 0,
            "N/A": 0
        }

        for from_mode in modes:
            for to_mode in modes:
                risk = matrix[from_mode][to_mode]
                stats[risk] = stats.get(risk, 0) + 1

        # Build HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Schema Compatibility Test Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
        }}

        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }}

        .stat-card .number {{
            font-size: 3em;
            font-weight: bold;
            margin-bottom: 10px;
        }}

        .stat-card .label {{
            font-size: 1.1em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .stat-card.safe .number {{ color: #28a745; }}
        .stat-card.risky .number {{ color: #ffc107; }}
        .stat-card.dangerous .number {{ color: #dc3545; }}
        .stat-card.na .number {{ color: #6c757d; }}

        .content {{
            padding: 40px;
        }}

        h2 {{
            color: #667eea;
            margin: 30px 0 20px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}

        .matrix-container {{
            overflow-x: auto;
            margin: 20px 0;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.9em;
        }}

        th, td {{
            padding: 12px;
            text-align: center;
            border: 1px solid #ddd;
        }}

        th {{
            background: #667eea;
            color: white;
            font-weight: bold;
            position: sticky;
            top: 0;
        }}

        th.row-header {{
            background: #764ba2;
            text-align: left;
        }}

        td.safe {{
            background: #d4edda;
            color: #155724;
            font-weight: bold;
        }}

        td.risky {{
            background: #fff3cd;
            color: #856404;
            font-weight: bold;
        }}

        td.dangerous {{
            background: #f8d7da;
            color: #721c24;
            font-weight: bold;
        }}

        td.na {{
            background: #e9ecef;
            color: #495057;
        }}

        .legend {{
            display: flex;
            gap: 20px;
            justify-content: center;
            margin: 30px 0;
            flex-wrap: wrap;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 20px;
            background: white;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}

        .legend-box {{
            width: 20px;
            height: 20px;
            border-radius: 3px;
        }}

        .legend-box.safe {{ background: #d4edda; }}
        .legend-box.risky {{ background: #fff3cd; }}
        .legend-box.dangerous {{ background: #f8d7da; }}
        .legend-box.na {{ background: #e9ecef; }}

        .transitions-list {{
            margin: 20px 0;
        }}

        .transition-item {{
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #667eea;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}

        .transition-item.safe {{ border-left-color: #28a745; }}
        .transition-item.risky {{ border-left-color: #ffc107; }}
        .transition-item.dangerous {{ border-left-color: #dc3545; }}

        .transition-header {{
            font-weight: bold;
            margin-bottom: 5px;
        }}

        .transition-description {{
            color: #666;
            font-size: 0.95em;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: bold;
            margin-left: 10px;
        }}

        .badge.safe {{ background: #28a745; color: white; }}
        .badge.risky {{ background: #ffc107; color: #333; }}
        .badge.dangerous {{ background: #dc3545; color: white; }}

        footer {{
            background: #f8f9fa;
            padding: 30px;
            text-align: center;
            color: #666;
            border-top: 1px solid #ddd;
        }}

        @media print {{
            body {{ background: white; padding: 0; }}
            .container {{ box-shadow: none; }}
            header {{ background: #667eea; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Schema Compatibility Test Report</h1>
            <div class="subtitle">Complete Analysis of Compatibility Mode Transitions</div>
            <div style="margin-top: 20px; opacity: 0.8;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </header>

        <div class="stats">
            <div class="stat-card safe">
                <div class="number">{stats.get('SAFE', 0)}</div>
                <div class="label">Safe Transitions</div>
            </div>
            <div class="stat-card risky">
                <div class="number">{stats.get('RISKY', 0)}</div>
                <div class="label">Risky Transitions</div>
            </div>
            <div class="stat-card dangerous">
                <div class="number">{stats.get('DANGEROUS', 0)}</div>
                <div class="label">Dangerous Transitions</div>
            </div>
            <div class="stat-card na">
                <div class="number">{len(modes)}</div>
                <div class="label">Compatibility Modes</div>
            </div>
        </div>

        <div class="content">
            <h2>🔄 Complete Transition Matrix</h2>

            <div class="legend">
                <div class="legend-item">
                    <div class="legend-box safe"></div>
                    <span>✅ SAFE - Always safe transition</span>
                </div>
                <div class="legend-item">
                    <div class="legend-box risky"></div>
                    <span>⚠️ RISKY - Requires validation</span>
                </div>
                <div class="legend-item">
                    <div class="legend-box dangerous"></div>
                    <span>🔴 DANGEROUS - High risk, validate carefully</span>
                </div>
                <div class="legend-item">
                    <div class="legend-box na"></div>
                    <span>⏺️ N/A - Same mode (no transition)</span>
                </div>
            </div>

            <div class="matrix-container">
                <table>
                    <thead>
                        <tr>
                            <th class="row-header">From \\ To</th>
                            {''.join(f'<th>{mode}</th>' for mode in modes)}
                        </tr>
                    </thead>
                    <tbody>
"""

        # Add matrix rows
        for from_mode in modes:
            html += f"                        <tr>\n"
            html += f"                            <th class=\"row-header\">{from_mode}</th>\n"
            for to_mode in modes:
                risk = matrix[from_mode][to_mode]
                css_class = risk.lower()
                symbol = {
                    "SAFE": "✅",
                    "RISKY": "⚠️",
                    "DANGEROUS": "🔴",
                    "N/A": "⏺️",
                    "UNKNOWN": "❓"
                }.get(risk, "?")
                html += f"                            <td class=\"{css_class}\">{symbol} {risk}</td>\n"
            html += f"                        </tr>\n"

        html += """                    </tbody>
                </table>
            </div>

            <h2>📋 All Transition Details</h2>
            <div class="transitions-list">
"""

        # Add transition details
        for from_mode, to_mode, risk_level, requires_validation, description in compatibility_data:
            validation_text = "✓ Validation required" if requires_validation else "○ No validation needed"
            html += f"""
                <div class="transition-item {risk_level.lower()}">
                    <div class="transition-header">
                        {from_mode} → {to_mode}
                        <span class="badge {risk_level.lower()}">{risk_level}</span>
                    </div>
                    <div class="transition-description">
                        {description}<br>
                        <small><em>{validation_text}</em></small>
                    </div>
                </div>
"""

        html += """
            </div>
        </div>

        <footer>
            <p><strong>Schema Registry Compatibility Testing Framework</strong></p>
            <p>For more information, see the complete compatibility guide</p>
            <p style="margin-top: 10px; font-size: 0.9em;">
                Report generated by Multi-Backend Schema Registry Test Suite
            </p>
        </footer>
    </div>
</body>
</html>
"""

        return html

    def generate_json_report(self, compatibility_data: Optional[List] = None) -> str:
        """Generate JSON report."""

        if compatibility_data is None:
            compatibility_data = COMPATIBILITY_TRANSITIONS

        report = {
            "generated_at": datetime.now().isoformat(),
            "total_transitions": len(compatibility_data),
            "transitions": [
                {
                    "from_mode": t[0],
                    "to_mode": t[1],
                    "risk_level": t[2],
                    "requires_validation": t[3],
                    "description": t[4]
                }
                for t in compatibility_data
            ],
            "statistics": self._calculate_statistics(compatibility_data)
        }

        output_file = self.output_dir / "compatibility-report.json"
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        return str(output_file)

    def _calculate_statistics(self, compatibility_data: List) -> Dict:
        """Calculate statistics from compatibility data."""

        stats = {
            "total": len(compatibility_data),
            "by_risk_level": {
                "SAFE": 0,
                "RISKY": 0,
                "DANGEROUS": 0
            },
            "requiring_validation": 0
        }

        for _, _, risk_level, requires_validation, _ in compatibility_data:
            stats["by_risk_level"][risk_level] = stats["by_risk_level"].get(risk_level, 0) + 1
            if requires_validation:
                stats["requiring_validation"] += 1

        return stats


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate compatibility test reports"
    )
    parser.add_argument(
        "--output-dir",
        default="test-reports",
        help="Output directory for reports"
    )
    parser.add_argument(
        "--format",
        choices=["html", "json", "both"],
        default="both",
        help="Report format"
    )

    args = parser.parse_args()

    generator = TestReportGenerator(args.output_dir)

    print(f"Generating compatibility test reports...")
    print(f"Output directory: {args.output_dir}")
    print()

    files_generated = []

    if args.format in ["html", "both"]:
        html_file = generator.generate_html_report()
        files_generated.append(html_file)
        print(f"✓ HTML report:  {html_file}")

    if args.format in ["json", "both"]:
        json_file = generator.generate_json_report()
        files_generated.append(json_file)
        print(f"✓ JSON report:  {json_file}")

    print()
    print(f"✅ Generated {len(files_generated)} report(s)")
    print()
    print("View reports:")
    for file in files_generated:
        if file.endswith('.html'):
            print(f"  open {file}")
        else:
            print(f"  cat {file}")


if __name__ == "__main__":
    main()
